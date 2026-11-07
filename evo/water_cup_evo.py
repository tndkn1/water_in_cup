"""Water Cup EVO
A paper cup full of water sits in your cup holder. Drive smooth enough not to spill it.

External overlay for Assetto Corsa EVO. Reads the game's shared memory and draws the
cup in a small always-on-top window, so run the game in borderless or windowed mode.

Physics: the water surface is modelled as the first sloshing mode of a cylindrical
container, i.e. a damped 2D oscillator whose equilibrium slope equals horizontal
acceleration / g. Jerky inputs excite overshoot, so smoothness matters, not just G.

Usage: python water_cup_evo.py [--demo]
  Drag the window to move it, right-click for settings, double-click to refill.
"""

import ctypes
import json
import math
import os
import random
import sys
import time
import tkinter as tk
from ctypes import wintypes

VERSION = '0.1.0'

G = 9.81
CUP_H = 0.080    # cup height, m
R_TOP = 0.036    # rim radius, m
R_BOT = 0.026    # bottom radius, m
R_PHYS = 0.031   # mean radius used for slosh frequency, m
SLOSH_K = 1.841  # first root of J1', first slosh mode of a cylinder
SPILL_RATE = 6   # 1/s, how fast water above the rim drains away
MAX_SLOPE = 1.5
SUBSTEP = 0.002

VIEW_ELEV = math.radians(35)  # 3D view: camera pitch, looking forward and down like the driver
RING = 48
BASE_W, BASE_H = 260, 380
FRAME_MS = 16

# --- AC EVO shared memory ------------------------------------------------------------
# Layout from Kunos' shared memory documentation (#pragma pack(4)).

PHYSICS_TAG = 'Local\\acevo_pmf_physics'
GRAPHICS_TAG = 'Local\\acevo_pmf_graphics'
PHYSICS_SIZE = 800
GRAPHICS_SIZE = 4096

PHY_PACKET_ID = 0         # int
PHY_SPEED_KMH = 28        # float
GFX_STATUS = 4            # int: 0 off, 1 replay, 2 live, 3 pause
GFX_G_LATERAL = 132       # float, positive = rightward
GFX_G_LONGITUDINAL = 136  # float, positive = under acceleration
GFX_IS_IN_PIT_BOX = 3119  # bool

AC_LIVE = 2
STALE_AFTER = 2.0  # s without a new physics packet: the game has stopped writing

FILE_MAP_READ = 0x0004

_kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
_kernel32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
_kernel32.OpenFileMappingW.restype = wintypes.HANDLE
_kernel32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
_kernel32.MapViewOfFile.restype = ctypes.c_void_p
_kernel32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


class SharedPage:
    """Read-only view of an existing named mapping. Never creates one, so the game
    always gets to size its own segments."""

    def __init__(self, tag, size):
        self.handle = _kernel32.OpenFileMappingW(FILE_MAP_READ, False, tag)
        if not self.handle:
            raise OSError(tag)
        self.base = _kernel32.MapViewOfFile(self.handle, FILE_MAP_READ, 0, 0, size)
        if not self.base:
            _kernel32.CloseHandle(self.handle)
            raise OSError(tag)

    def int(self, off): return ctypes.c_int32.from_address(self.base + off).value
    def float(self, off): return ctypes.c_float.from_address(self.base + off).value
    def bool(self, off): return ctypes.c_uint8.from_address(self.base + off).value != 0

    def close(self):
        _kernel32.UnmapViewOfFile(self.base)
        _kernel32.CloseHandle(self.handle)


class Telemetry:
    def __init__(self):
        self.physics = self.graphics = None
        self.last_packet = None
        self.last_change = 0
        self.next_try = 0

    def close(self):
        for page in (self.physics, self.graphics):
            if page: page.close()
        self.physics = self.graphics = None

    def read(self):
        """Returns None while the game is not running, otherwise a dict of what we use."""
        now = time.monotonic()
        if not self.physics:
            if now < self.next_try: return None
            self.next_try = now + 1
            try:
                self.physics = SharedPage(PHYSICS_TAG, PHYSICS_SIZE)
                self.graphics = SharedPage(GRAPHICS_TAG, GRAPHICS_SIZE)
            except OSError:
                self.close()
                return None
            self.last_packet, self.last_change = None, now

        packet = self.physics.int(PHY_PACKET_ID)
        if packet != self.last_packet:
            self.last_packet, self.last_change = packet, now
        elif now - self.last_change > STALE_AFTER:
            # Our handle keeps the mapping alive after the game exits; let it go and reopen.
            self.close()
            return None

        g = self.graphics
        return {
            'live': g.int(GFX_STATUS) == AC_LIVE and now - self.last_change < 0.5,
            'ax': g.float(GFX_G_LATERAL),
            'az': g.float(GFX_G_LONGITUDINAL),
            'speed': self.physics.float(PHY_SPEED_KMH),
            'in_pit': g.bool(GFX_IS_IN_PIT_BOX),
        }


class DemoTelemetry:
    """Fake laps for trying the app without the game: corners, braking, and a pit stop."""

    def __init__(self):
        self.t0 = time.monotonic()

    def read(self):
        t = (time.monotonic() - self.t0) % 40
        if t > 36:
            return {'live': True, 'ax': 0, 'az': 0, 'speed': 0, 'in_pit': True}
        ax = 0.15 * math.sin(t * 0.6) + (0.25 if 12 < t < 13 else 0)
        az = 0.08 * math.cos(t * 0.4) - (0.5 if 20 < t < 21.5 else 0)
        return {'live': True, 'ax': ax, 'az': az, 'speed': 90, 'in_pit': False}


# --- Settings ------------------------------------------------------------------------

SETTINGS_PATH = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'WaterCupEVO', 'settings.json')

DEFAULTS = {
    'freeboardMm': 8,    # gap between water and rim at rest
    'damping': 0.06,     # damping ratio of the slosh mode
    'invertX': False,
    'invertZ': False,
    'buntaMode': False,  # a single spill ends the run
    'view3D': True,
    'autoRefill': True,  # refill the cup when the car arrives in its pit box
    'scale': 1.0,
    'opacity': 0.9,
    'x': 60, 'y': 60,
}


def load_settings():
    s = dict(DEFAULTS)
    try:
        with open(SETTINGS_PATH, encoding='utf-8') as f:
            s.update({k: v for k, v in json.load(f).items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    return s


def save_settings(s):
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(s, f, indent=2)
    except OSError:
        pass


# --- Water simulation ----------------------------------------------------------------

def clamp(x, a, b): return a if x < a else (b if x > b else x)


def level_to_ml(h): return h * math.pi * R_PHYS * R_PHYS * 1e6


class Cup:
    def __init__(self, settings):
        self.settings = settings
        self.reset()

    def reset(self):
        self.level = CUP_H - self.settings['freeboardMm'] / 1000
        self.sx = self.sz = 0.0    # surface slope
        self.vx = self.vz = 0.0    # slope velocity
        self.spilled_ml, self.spill_events, self.distance = 0.0, 0, 0.0
        self.spilling, self.flash, self.game_over = False, 0.0, False
        self.particles = []

    # phi: direction (in the cup's horizontal plane) where the water goes over the rim.
    def spawn_droplets(self, phi, amount):
        for _ in range(min(6, math.ceil(amount * 3))):
            speed = 40 + random.random() * 80
            self.particles.append({
                'phi': phi, 'x': 0.0, 'y': 0.0,
                'vx': math.cos(phi) * speed,
                'vy': -(30 + random.random() * 90),
                'life': 0.8,
            })

    def physics_step(self, dt, ax, az):
        k = SLOSH_K / R_PHYS
        omega = math.sqrt(G * k * math.tanh(k * max(self.level, 0.005)))
        zeta = self.settings['damping']

        # Equilibrium: the surface tilts so that water climbs away from the acceleration.
        acc_x = omega * omega * (-ax - self.sx) - 2 * zeta * omega * self.vx
        acc_z = omega * omega * (-az - self.sz) - 2 * zeta * omega * self.vz
        self.vx += acc_x * dt
        self.vz += acc_z * dt
        self.sx += self.vx * dt
        self.sz += self.vz * dt

        mag = math.hypot(self.sx, self.sz)
        if mag > MAX_SLOPE:
            self.sx *= MAX_SLOPE / mag
            self.sz *= MAX_SLOPE / mag
            mag = MAX_SLOPE

        excess = mag * R_TOP - (CUP_H - self.level)
        if excess > 0:
            loss = excess * SPILL_RATE * dt
            self.level -= loss
            self.spilled_ml += level_to_ml(loss)
            damp = 1 - min(1, 3 * dt)  # spilling water carries energy away
            self.vx *= damp
            self.vz *= damp
            if not self.spilling:
                self.spilling = True
                self.spill_events += 1
                self.flash = 1
                self.spawn_droplets(math.atan2(self.sz, self.sx), excess * 1000)
                if self.settings['buntaMode']: self.game_over = True
        elif excess < -0.0005:
            self.spilling = False

    def update(self, dt, ax, az, speed_kmh):
        steps = max(1, math.ceil(dt / SUBSTEP))
        for _ in range(steps): self.physics_step(dt / steps, ax, az)
        self.distance += speed_kmh / 3.6 * dt

    def update_particles(self, dt):
        for p in self.particles:
            p['vy'] += 900 * dt
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['life'] -= dt
        self.particles = [p for p in self.particles if p['life'] > 0]


# --- Drawing -------------------------------------------------------------------------
# Tk has no alpha blending, so the translucent colours of the CSP app are pre-blended
# over the window background.

COL_BG = '#16191e'
COL_CUP_FILL = '#272a2f'
COL_CUP_LINE = '#f2f2eb'
COL_WATER = '#4a82cc'
COL_WATER_SIDE = '#2f63b0'
COL_SURFACE = '#cce8ff'
COL_DANGER = '#ff4d40'
COL_OK = '#66e680'
COL_TEXT = '#e6e6e6'
COL_DIM = '#8a8f98'


# Clips a convex polygon to the half-plane f(p) >= 0. Points created on the
# boundary are flagged so the water surface line can be drawn through them.
def clip_poly(poly, f):
    out = []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        fa, fb = f(a), f(b)
        if fa >= 0: out.append((a[0], a[1], False))
        if (fa >= 0) != (fb >= 0):
            t = fa / (fa - fb)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, True))
    return out


def convex_hull(pts):
    pts = sorted(pts)

    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0: lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0: upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def flat(pts): return [c for p in pts for c in p]


def blend(a, b, t):
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(x + (y - x) * t):02x}' for x, y in zip(ca, cb))


def wall_radius(h): return R_BOT + (R_TOP - R_BOT) * h / CUP_H


class Renderer:
    def __init__(self, canvas, cup, settings):
        self.c, self.cup, self.settings = canvas, cup, settings

    def draw_droplets(self, rim_point):
        for p in self.cup.particles:
            bx, by = rim_point(p['phi'])
            x, y = bx + p['x'], by + p['y']
            self.c.create_oval(x - 3, y - 3, x + 3, y + 3, fill=COL_WATER, outline='')

    def draw_cup_2d(self, ox, oy, scale):
        c, cup = self.c, self.cup

        def P(x, h): return (ox + x * scale, oy - h * scale)

        shape = [(-R_BOT, 0), (R_BOT, 0), (R_TOP, CUP_H), (-R_TOP, CUP_H)]
        c.create_polygon(flat(P(*p) for p in shape), fill=COL_CUP_FILL, outline='')

        sx, level = cup.sx, cup.level
        water = clip_poly(shape, lambda p: level + sx * p[0] - p[1])
        if len(water) >= 3:
            c.create_polygon(flat(P(p[0], p[1]) for p in water), fill=COL_WATER, outline='')
            surface = [p for p in water if p[2]]
            if len(surface) >= 2:
                c.create_line(*P(*surface[0][:2]), *P(*surface[1][:2]), fill=COL_SURFACE, width=2)

        c.create_line(*P(-R_BOT, 0), *P(R_BOT, 0), fill=COL_CUP_LINE, width=3)
        c.create_line(*P(-R_BOT, 0), *P(-R_TOP, CUP_H), fill=COL_CUP_LINE, width=3)
        c.create_line(*P(R_BOT, 0), *P(R_TOP, CUP_H), fill=COL_CUP_LINE, width=3)
        c.create_line(*P(-R_TOP - 0.002, CUP_H), *P(R_TOP + 0.002, CUP_H), fill=COL_CUP_LINE, width=5)

        self.draw_droplets(lambda phi: P((1 if math.cos(phi) >= 0 else -1) * R_TOP, CUP_H))

    # Orthographic view from behind and above the cup. x = car right, z = car forward,
    # (ox, oy) = screen position of the cup's bottom centre.
    def draw_cup_3d(self, ox, oy, scale):
        c, cup = self.c, self.cup
        cos_e, sin_e = math.cos(VIEW_ELEV), math.sin(VIEW_ELEV)

        def P(x, h, z): return (ox + x * scale, oy - (h * cos_e + z * sin_e) * scale)

        # Water/wall contact line: solve h = level + m * wall_radius(h) at each angle.
        taper = (R_TOP - R_BOT) / CUP_H
        bottom, rim, contact, front = [], [], [], []
        for i in range(RING):
            t = i / RING * 2 * math.pi
            ct, st = math.cos(t), math.sin(t)
            m = cup.sx * ct + cup.sz * st
            h = clamp((cup.level + m * R_BOT) / max(1 - m * taper, 0.05), 0, CUP_H)
            r = wall_radius(h)
            bottom.append(P(R_BOT * ct, 0, R_BOT * st))
            rim.append(P(R_TOP * ct, CUP_H, R_TOP * st))
            contact.append(P(r * ct, h, r * st))
            front.append(math.sin(t + math.pi / RING) < 0)

        hull = convex_hull(bottom + rim)
        c.create_polygon(flat(hull), fill=COL_CUP_FILL, outline='')

        for i in range(RING):
            if front[i]:
                j = (i + 1) % RING
                c.create_polygon(flat([bottom[i], bottom[j], contact[j], contact[i]]),
                                 fill=COL_WATER_SIDE, outline=COL_WATER_SIDE)
        c.create_polygon(flat(contact), fill=COL_WATER, outline=COL_SURFACE, width=1.5)

        c.create_polygon(flat(hull), fill='', outline=COL_CUP_LINE, width=2)
        c.create_polygon(flat(rim), fill='', outline=COL_CUP_LINE, width=3)

        self.draw_droplets(lambda phi: P(R_TOP * math.cos(phi), CUP_H, R_TOP * math.sin(phi)))

    # Top view: the dot is where the water climbs; the ring is where it goes over the rim.
    def draw_gauge(self, cx, cy, radius):
        cup = self.cup
        limit = max((CUP_H - cup.level) / R_TOP, 1e-4)
        dx, dy = cup.sx / limit, -cup.sz / limit
        length = math.hypot(dx, dy)
        if length > 1.15:
            dx, dy = dx * 1.15 / length, dy * 1.15 / length
        danger = length >= 1
        self.c.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                           fill='#0e1013', outline=COL_DANGER if danger else COL_CUP_LINE, width=2)
        r2 = radius * 0.5
        self.c.create_oval(cx - r2, cy - r2, cx + r2, cy + r2, outline='#454950', width=1)
        px, py = cx + dx * radius, cy + dy * radius
        self.c.create_oval(px - 5, py - 5, px + 5, py + 5, fill=COL_DANGER if danger else COL_WATER, outline='')

    def draw(self, dt, status):
        c, cup, s = self.c, self.cup, self.settings
        k = s['scale']
        w, h = BASE_W * k, BASE_H * k
        c.delete('all')
        cup.flash = max(0, cup.flash - dt * 2)
        c.create_rectangle(0, 0, w, h, fill=blend(COL_BG, COL_DANGER, 0.3 * cup.flash), outline='')

        area = max(h - 170 * k, 40)
        if s['view3D']:
            sin_e, cos_e = math.sin(VIEW_ELEV), math.cos(VIEW_ELEV)
            above = CUP_H * cos_e + R_TOP * sin_e
            scale = min((w - 40 * k) / (2 * R_TOP), area / (above + R_BOT * sin_e))
            self.draw_cup_3d(w / 2, 30 * k + above * scale, scale)
        else:
            scale = min((w - 40 * k) / (2 * R_TOP), area / CUP_H)
            self.draw_cup_2d(w / 2, 30 * k + CUP_H * scale, scale)

        top = 40 * k + area
        self.draw_gauge(w - 50 * k, top + 45 * k, 35 * k)

        title = ('Segoe UI', round(18 * k), 'bold')
        body = ('Segoe UI', round(10 * k))
        x, y = 12 * k, top + 8 * k
        if cup.game_over:
            c.create_text(x, y, text='SPILLED!', fill=COL_DANGER, font=title, anchor='nw')
        elif cup.spill_events == 0:
            c.create_text(x, y, text='CLEAN', fill=COL_OK, font=title, anchor='nw')
        else:
            c.create_text(x, y, text=f'{cup.spilled_ml:.1f} ml', fill=COL_DANGER, font=title, anchor='nw')
        lines = [
            f'Spills: {cup.spill_events}',
            f'Water: {level_to_ml(cup.level):.0f} ml',
            f'Distance: {cup.distance / 1000:.2f} km',
        ]
        for i, line in enumerate(lines):
            c.create_text(x, y + (36 + 18 * i) * k, text=line, fill=COL_TEXT, font=body, anchor='nw')
        if cup.game_over:
            c.create_text(x, y + 90 * k, text='Bunta mode: run over', fill=COL_DANGER, font=body, anchor='nw')
        c.create_text(x, h - 8 * k, text=status, fill=COL_DIM, font=('Segoe UI', round(8 * k)), anchor='sw')


# --- App -----------------------------------------------------------------------------

class App:
    def __init__(self, demo):
        self.settings = load_settings()
        self.cup = Cup(self.settings)
        self.telemetry = DemoTelemetry() if demo else Telemetry()
        self.was_in_pit = None
        self.last_time = time.perf_counter()

        self.root = root = tk.Tk()
        root.title('Water Cup EVO')
        root.overrideredirect(True)  # no title bar, so it sits on top of the game cleanly
        root.attributes('-topmost', True)
        root.configure(bg=COL_BG)
        self.canvas = tk.Canvas(root, highlightthickness=0, bg=COL_BG)
        self.canvas.pack(fill='both', expand=True)
        self.renderer = Renderer(self.canvas, self.cup, self.settings)
        self.apply_window()

        self.canvas.bind('<ButtonPress-1>', self.drag_start)
        self.canvas.bind('<B1-Motion>', self.drag_move)
        self.canvas.bind('<ButtonRelease-1>', lambda e: save_settings(self.settings))
        self.canvas.bind('<Double-Button-1>', lambda e: self.cup.reset())
        self.canvas.bind('<Button-3>', self.show_menu)
        root.bind('<Escape>', lambda e: self.quit())
        self.build_menu()

        root.after(FRAME_MS, self.tick)

    def apply_window(self):
        s = self.settings
        w, h = round(BASE_W * s['scale']), round(BASE_H * s['scale'])
        self.root.geometry(f'{w}x{h}+{s["x"]}+{s["y"]}')
        self.root.attributes('-alpha', s['opacity'])

    def drag_start(self, e):
        self.drag_offset = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def drag_move(self, e):
        self.settings['x'] = e.x_root - self.drag_offset[0]
        self.settings['y'] = e.y_root - self.drag_offset[1]
        self.root.geometry(f'+{self.settings["x"]}+{self.settings["y"]}')

    def build_menu(self):
        s = self.settings
        self.vars = {}
        menu = tk.Menu(self.root, tearoff=False)
        menu.add_command(label='Refill cup / reset', command=self.cup.reset)
        menu.add_separator()

        def toggle(label, key):
            var = self.vars[key] = tk.BooleanVar(value=s[key])

            def changed():
                s[key] = var.get()
                save_settings(s)
            menu.add_checkbutton(label=label, variable=var, command=changed)

        def choice(label, key, values, fmt, then=None):
            sub = tk.Menu(menu, tearoff=False)
            var = self.vars[key] = tk.DoubleVar(value=s[key])

            def changed():
                s[key] = var.get()
                save_settings(s)
                if then: then()
            for v in values:
                sub.add_radiobutton(label=fmt.format(v), variable=var, value=v, command=changed)
            menu.add_cascade(label=label, menu=sub)

        toggle('3D view', 'view3D')
        toggle('Bunta mode (one spill ends the run)', 'buntaMode')
        toggle('Auto refill in pits', 'autoRefill')
        toggle('Invert lateral axis', 'invertX')
        toggle('Invert longitudinal axis', 'invertZ')
        menu.add_separator()
        choice('Gap to rim', 'freeboardMm', [2, 4, 6, 8, 10, 12, 15, 20, 30], '{:.0f} mm')
        choice('Slosh damping', 'damping', [0.02, 0.04, 0.06, 0.1, 0.15, 0.2, 0.3], '{:.2f}')
        choice('Window size', 'scale', [0.75, 1.0, 1.25, 1.5, 2.0], '{:.0%}', self.apply_window)
        choice('Opacity', 'opacity', [0.5, 0.7, 0.8, 0.9, 1.0], '{:.0%}', self.apply_window)
        menu.add_separator()
        menu.add_command(label='Quit', command=self.quit)
        self.menu = menu

    def show_menu(self, e):
        self.menu.tk_popup(e.x_root, e.y_root)

    def quit(self):
        save_settings(self.settings)
        self.root.destroy()

    def tick(self):
        now = time.perf_counter()
        dt = min(now - self.last_time, 0.1)
        self.last_time = now

        data = self.telemetry.read()
        if data is None:
            status = 'Waiting for Assetto Corsa EVO...'
            self.was_in_pit = None
        else:
            s = self.settings
            if s['autoRefill'] and data['in_pit'] and self.was_in_pit is False:
                self.cup.reset()
            self.was_in_pit = data['in_pit']
            if data['live'] and not self.cup.game_over:
                ax = data['ax'] * (-1 if s['invertX'] else 1)
                az = data['az'] * (-1 if s['invertZ'] else 1)
                self.cup.update(dt, ax, az, data['speed'])
            status = 'Demo' if isinstance(self.telemetry, DemoTelemetry) else \
                ('Connected' if data['live'] else 'Connected (paused)')
            if data['in_pit']: status += ' - in pit box'

        self.cup.update_particles(dt)
        self.renderer.draw(dt, status)
        self.root.after(FRAME_MS, self.tick)

    def run(self):
        self.root.mainloop()


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    App(demo='--demo' in sys.argv).run()


if __name__ == '__main__':
    main()
