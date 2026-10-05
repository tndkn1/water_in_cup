# Water Cup — Assetto Corsa app

カップホルダーに水を入れた紙コップを置いて、こぼさずに走れるか。
あの峠の豆腐屋の修行を Assetto Corsa で再現する CSP Lua アプリです。

A paper cup full of water sits in your cup holder — can you drive without spilling it?
A CSP Lua app for Assetto Corsa that recreates the famous mountain-pass tofu-delivery training.

## ダウンロード / Download

**[⬇ WaterCup.zip（最新版 / latest）](https://github.com/tndkn1/water_in_cup/releases/latest/download/WaterCup.zip)**

ダウンロードした zip を Content Manager にドラッグ＆ドロップするだけでインストールできます。過去のバージョンは [Releases](https://github.com/tndkn1/water_in_cup/releases) から。

Just drag and drop the downloaded zip onto Content Manager to install. Older versions are on the [Releases](https://github.com/tndkn1/water_in_cup/releases) page.

## 特徴 / Features

**日本語**

- 車の前後・横 G から水面の揺れ（スロッシング）を物理的にシミュレート
  - 円筒容器の一次スロッシングモード（約 3.6 Hz）を減衰振動として計算
  - G の大きさだけでなく、**操作の急さ**で水面がオーバーシュートしてこぼれる
- 紙コップ表示は **3D**（運転席から見下ろした視点、前後・左右の傾きを表示／デフォルト）と **2D**（側面図）を設定で切り替え
- 上面ゲージ（円の外に点が出るとこぼれる）
- こぼれた量 (ml)、こぼした回数、走行距離を表示
- 設定: 3D/2D 表示、水面とフチの余裕 (mm)、揺れの減衰、**Bunta モード**（1 回こぼしたら終了）、軸反転

**English**

- Physically simulates water sloshing from the car's longitudinal and lateral G
  - The first sloshing mode of a cylindrical container (about 3.6 Hz) is modelled as a damped oscillator
  - Not just how much G you pull, but **how abruptly** you apply inputs makes the water overshoot and spill
- Cup view can be switched in settings between **3D** (looking down from the driver's seat, shows both longitudinal and lateral tilt; default) and **2D** (side view)
- Top-view gauge (water spills when the dot leaves the circle)
- Shows spilled amount (ml), number of spills, and distance driven
- Settings: 3D/2D view, gap between water and rim (mm), slosh damping, **Bunta mode** (one spill ends the run), axis inversion

## 参考動画 / Reference video

- https://www.youtube.com/live/rH3_DwHWyYc

## 動作環境 / Requirements

- Assetto Corsa
- [Custom Shaders Patch (CSP)](https://acstuff.club/patch/)（最新版推奨 / latest version recommended）

## インストール / Install

**日本語**

Content Manager を使う場合（おすすめ）:

1. 上の「ダウンロード」から `WaterCup.zip` をダウンロード
2. zip を Content Manager のウィンドウにドラッグ＆ドロップし、「Install」を押す
3. ゲーム内で右側のアプリバーから **Water Cup** を開く

手動の場合: zip の中の `apps` フォルダを Assetto Corsa のインストールフォルダ
（例: `C:\Program Files (x86)\Steam\steamapps\common\assettocorsa`）にコピーし、
`assettocorsa\apps\lua\WaterCup\` ができれば OK です。

**English**

With Content Manager (recommended):

1. Download `WaterCup.zip` from the Download section above
2. Drag and drop the zip onto the Content Manager window and press "Install"
3. In game, open **Water Cup** from the app bar on the right

Manual install: copy the `apps` folder from the zip into your Assetto Corsa install folder
(e.g. `C:\Program Files (x86)\Steam\steamapps\common\assettocorsa`)
so that you end up with `assettocorsa\apps\lua\WaterCup\`.

## 開発者向け / For developers

`apps/` 以下を変更して `main` に push すると、GitHub Actions が zip を作って Releases に公開します（バージョンは `manifest.ini` の `VERSION`）。
手元で zip を作るときは `pwsh ./build.ps1` を実行すると `dist/` に出力されます。

Pushing changes under `apps/` to `main` makes GitHub Actions build the zip and publish it to Releases (versioned by `VERSION` in `manifest.ini`).
To build locally, run `pwsh ./build.ps1`; the zip is written to `dist/`.

## 使い方 / Usage

**日本語**

- 走るだけ。上面ゲージの点が外側の円に触れるとこぼれます。
- ウィンドウの歯車アイコンから設定、`Refill cup / reset` で水を入れ直し。
- 左コーナーで水が左に寄るなど向きが逆に見える場合は `Invert lateral axis` を ON に。

**English**

- Just drive. Water spills when the dot on the top-view gauge touches the outer circle.
- Open settings with the gear icon on the window; use `Refill cup / reset` to refill the cup.
- If the water moves the wrong way (e.g. it shifts left in a left-hand corner), turn on `Invert lateral axis`.

## 免責 / Disclaimer

非公式のファンメイド作品です。原作・出版社・Kunos Simulazioni とは一切関係ありません。

This is an unofficial fan-made app, not affiliated with the original manga, its publishers, or Kunos Simulazioni.

## ライセンス / License

[MIT License](LICENSE) © 2026 tndkn1

ライセンスの対象は本リポジトリのコードのみです。原作に関する権利は各権利者に帰属します。

The license covers the code in this repository only. All rights to the original work belong to their respective owners.
