-- Water Cup
-- A paper cup full of water sits in your cup holder. Drive smooth enough not to spill it.
--
-- Physics: the water surface is modelled as the first sloshing mode of a cylindrical
-- container, i.e. a damped 2D oscillator whose equilibrium slope equals horizontal
-- acceleration / g. Jerky inputs excite overshoot, so smoothness matters, not just G.

local G = 9.81
local CUP_H = 0.080   -- cup height, m
local R_TOP = 0.036   -- rim radius, m
local R_BOT = 0.026   -- bottom radius, m
local R_PHYS = 0.031  -- mean radius used for slosh frequency, m
local SLOSH_K = 1.841 -- first root of J1', first slosh mode of a cylinder
local SPILL_RATE = 6  -- 1/s, how fast water above the rim drains away
local MAX_SLOPE = 1.5
local SUBSTEP = 0.002

local settings = ac.storage({
  freeboardMm = 8,  -- gap between water and rim at rest
  damping = 0.06,   -- damping ratio of the slosh mode
  invertX = false,
  invertZ = false,
  buntaMode = false -- a single spill ends the run
})

local level, slope, slopeVel
local spilledMl, spillEvents, distance
local spilling, flash, gameOver
local particles = {}

local function clamp(x, a, b) return x < a and a or (x > b and b or x) end

local function reset()
  level = CUP_H - settings.freeboardMm / 1000
  slope = vec2(0, 0)
  slopeVel = vec2(0, 0)
  spilledMl, spillEvents, distance = 0, 0, 0
  spilling, flash, gameOver = false, 0, false
  particles = {}
end
reset()

local function levelToMl(h)
  return h * math.pi * R_PHYS * R_PHYS * 1e6
end

local function spawnDroplets(side, amount)
  for _ = 1, math.min(6, math.ceil(amount * 3)) do
    particles[#particles + 1] = {
      side = side,
      x = 0, y = 0,
      vx = side * (40 + math.random() * 80),
      vy = -(30 + math.random() * 90),
      life = 0.8
    }
  end
end

local function physicsStep(dt, ax, az)
  local k = SLOSH_K / R_PHYS
  local omega = math.sqrt(G * k * math.tanh(k * math.max(level, 0.005)))
  local zeta = settings.damping

  -- Equilibrium: the surface tilts so that water climbs away from the acceleration.
  local tx, tz = -ax, -az
  local accX = omega * omega * (tx - slope.x) - 2 * zeta * omega * slopeVel.x
  local accZ = omega * omega * (tz - slope.y) - 2 * zeta * omega * slopeVel.y
  slopeVel.x = slopeVel.x + accX * dt
  slopeVel.y = slopeVel.y + accZ * dt
  slope.x = slope.x + slopeVel.x * dt
  slope.y = slope.y + slopeVel.y * dt

  local mag = slope:length()
  if mag > MAX_SLOPE then
    slope:scale(MAX_SLOPE / mag)
    mag = MAX_SLOPE
  end

  local excess = mag * R_TOP - (CUP_H - level)
  if excess > 0 then
    local loss = excess * SPILL_RATE * dt
    level = level - loss
    spilledMl = spilledMl + levelToMl(loss)
    slopeVel:scale(1 - math.min(1, 3 * dt)) -- spilling water carries energy away
    if not spilling then
      spilling = true
      spillEvents = spillEvents + 1
      flash = 1
      local side = slope.x >= 0 and 1 or -1
      spawnDroplets(side, excess * 1000)
      if settings.buntaMode then gameOver = true end
    end
  elseif excess < -0.0005 then
    spilling = false
  end
end

local function updateParticles(dt)
  for i = #particles, 1, -1 do
    local p = particles[i]
    p.vy = p.vy + 900 * dt
    p.x = p.x + p.vx * dt
    p.y = p.y + p.vy * dt
    p.life = p.life - dt
    if p.life <= 0 then table.remove(particles, i) end
  end
end

-- Clips a convex polygon to the half-plane f(p) >= 0. Points created on the
-- boundary are flagged so the water surface line can be drawn through them.
local function clipPoly(poly, f)
  local out = {}
  for i = 1, #poly do
    local a, b = poly[i], poly[i % #poly + 1]
    local fa, fb = f(a), f(b)
    if fa >= 0 then out[#out + 1] = a end
    if (fa >= 0) ~= (fb >= 0) then
      local t = fa / (fa - fb)
      out[#out + 1] = { a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, surface = true }
    end
  end
  return out
end

local colCupFill = rgbm(1, 1, 1, 0.08)
local colCupLine = rgbm(0.95, 0.95, 0.92, 1)
local colWater = rgbm(0.35, 0.65, 1, 0.75)
local colSurface = rgbm(0.8, 0.92, 1, 1)
local colDanger = rgbm(1, 0.3, 0.25, 1)
local colOk = rgbm(0.4, 0.9, 0.5, 1)

local function drawCup(origin, scale)
  local function P(x, h) return vec2(origin.x + x * scale, origin.y - h * scale) end

  local cup = { { -R_BOT, 0 }, { R_BOT, 0 }, { R_TOP, CUP_H }, { -R_TOP, CUP_H } }
  for _, p in ipairs(cup) do ui.pathLineTo(P(p[1], p[2])) end
  ui.pathFillConvex(colCupFill)

  local sx = slope.x
  local water = clipPoly(cup, function(p) return level + sx * p[1] - p[2] end)
  if #water >= 3 then
    for _, p in ipairs(water) do ui.pathLineTo(P(p[1], p[2])) end
    ui.pathFillConvex(colWater)
    local s1, s2
    for _, p in ipairs(water) do
      if p.surface then if s1 then s2 = p else s1 = p end end
    end
    if s1 and s2 then ui.drawLine(P(s1[1], s1[2]), P(s2[1], s2[2]), colSurface, 2) end
  end

  ui.drawLine(P(-R_BOT, 0), P(R_BOT, 0), colCupLine, 3)
  ui.drawLine(P(-R_BOT, 0), P(-R_TOP, CUP_H), colCupLine, 3)
  ui.drawLine(P(R_BOT, 0), P(R_TOP, CUP_H), colCupLine, 3)
  ui.drawLine(P(-R_TOP - 0.002, CUP_H), P(R_TOP + 0.002, CUP_H), colCupLine, 5)

  for _, p in ipairs(particles) do
    local base = P(p.side * R_TOP, CUP_H)
    ui.drawCircleFilled(vec2(base.x + p.x, base.y + p.y), 3, colWater)
  end
end

-- Top view: the dot is where the water climbs; the ring is where it goes over the rim.
local function drawGauge(center, radius)
  local limit = math.max((CUP_H - level) / R_TOP, 1e-4)
  local d = vec2(slope.x / limit, -slope.y / limit)
  local len = d:length()
  if len > 1.15 then d:scale(1.15 / len) end
  ui.drawCircleFilled(center, radius, rgbm(0, 0, 0, 0.35), 32)
  ui.drawCircle(center, radius, len >= 1 and colDanger or colCupLine, 32, 2)
  ui.drawCircle(center, radius * 0.5, rgbm(1, 1, 1, 0.2), 24, 1)
  ui.drawCircleFilled(center + d * radius, 5, len >= 1 and colDanger or colWater, 16)
end

local function draw(dt)
  local size = ui.windowSize()
  flash = math.max(0, flash - dt * 2)
  if flash > 0 then
    ui.drawRectFilled(vec2(0, 0), size, rgbm(1, 0.1, 0.1, 0.25 * flash))
  end

  local scale = math.min((size.x - 40) / (2 * R_TOP), (size.y - 170) / CUP_H)
  drawCup(vec2(size.x / 2, 30 + CUP_H * scale), scale)

  local top = 40 + CUP_H * scale
  drawGauge(vec2(size.x - 50, top + 45), 35)

  ui.setCursor(vec2(12, top + 8))
  ui.pushFont(ui.Font.Title)
  if gameOver then
    ui.textColored('SPILLED!', colDanger)
  elseif spillEvents == 0 then
    ui.textColored('CLEAN', colOk)
  else
    ui.textColored(string.format('%.1f ml', spilledMl), colDanger)
  end
  ui.popFont()
  ui.setCursorX(12)
  ui.text(string.format('Spills: %d', spillEvents))
  ui.setCursorX(12)
  ui.text(string.format('Water: %.0f ml', levelToMl(level)))
  ui.setCursorX(12)
  ui.text(string.format('Distance: %.2f km', distance / 1000))
  if gameOver then
    ui.setCursorX(12)
    ui.textColored('Bunta mode: run over', colDanger)
  end
end

function script.windowMain(dt)
  dt = math.min(dt, 0.1)
  local sim = ac.getSim()
  local car = ac.getCar(0)
  if car and not sim.isPaused and not gameOver then
    local a = car.acceleration
    local ax = a.x * (settings.invertX and -1 or 1)
    local az = a.z * (settings.invertZ and -1 or 1)
    local steps = math.max(1, math.ceil(dt / SUBSTEP))
    for _ = 1, steps do physicsStep(dt / steps, ax, az) end
    distance = distance + car.speedKmh / 3.6 * dt
  end
  updateParticles(dt)
  draw(dt)
end

function script.windowSettings(dt)
  local v, changed = ui.slider('##freeboard', settings.freeboardMm, 2, 30, 'Gap to rim: %.0f mm')
  if changed then settings.freeboardMm = v end
  v, changed = ui.slider('##damping', settings.damping, 0.01, 0.3, 'Slosh damping: %.2f')
  if changed then settings.damping = v end
  if ui.checkbox('Bunta mode (one spill ends the run)', settings.buntaMode) then
    settings.buntaMode = not settings.buntaMode
  end
  if ui.checkbox('Invert lateral axis', settings.invertX) then settings.invertX = not settings.invertX end
  if ui.checkbox('Invert longitudinal axis', settings.invertZ) then settings.invertZ = not settings.invertZ end
  ui.offsetCursorY(8)
  if ui.button('Refill cup / reset') then reset() end
end
