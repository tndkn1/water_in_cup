# Water Cup — Assetto Corsa app

カップホルダーに水を入れた紙コップを置いて、こぼさずに走れるか。
あの峠の豆腐屋の修行を Assetto Corsa で再現する CSP Lua アプリです。

A paper cup full of water sits in your cup holder. Drive smooth enough not to spill it.

## 特徴 / Features

- 車の前後・横 G から水面の揺れ（スロッシング）を物理的にシミュレート
  - 円筒容器の一次スロッシングモード（約 3.6 Hz）を減衰振動として計算
  - G の大きさだけでなく、**操作の急さ**で水面がオーバーシュートしてこぼれる
- 紙コップ表示は **3D**（運転席から見下ろした視点、前後・左右の傾きを表示／デフォルト）と **2D**（側面図）を設定で切り替え
- 上面ゲージ（円の外に点が出るとこぼれる）
- こぼれた量 (ml)、こぼした回数、走行距離を表示
- 設定: 3D/2D 表示、水面とフチの余裕 (mm)、揺れの減衰、**Bunta モード**（1 回こぼしたら終了）、軸反転

## 動作環境 / Requirements

- Assetto Corsa
- [Custom Shaders Patch (CSP)](https://acstuff.club/patch/)（最新版推奨）

## インストール / Install

1. このリポジトリの `apps` フォルダを Assetto Corsa のインストールフォルダ
   （例: `C:\Program Files (x86)\Steam\steamapps\common\assettocorsa`）にコピー
   → `assettocorsa\apps\lua\WaterCup\` ができれば OK
2. ゲーム内で右側のアプリバーから **Water Cup** を開く

## 使い方 / Usage

- 走るだけ。上面ゲージの点が外側の円に触れるとこぼれます。
- ウィンドウの歯車アイコンから設定、`Refill cup / reset` で水を入れ直し。
- 左コーナーで水が左に寄るなど向きが逆に見える場合は `Invert lateral axis` を ON に。

## 免責 / Disclaimer

非公式のファンメイド作品です。原作・出版社・Kunos Simulazioni とは一切関係ありません。
This is an unofficial fan-made app, not affiliated with the original manga, its publishers, or Kunos Simulazioni.

## ライセンス / License

[MIT License](LICENSE) © 2026 tndkn1

ライセンスの対象は本リポジトリのコードのみです。原作に関する権利は各権利者に帰属します。
The license covers the code in this repository only. All rights to the original work belong to their respective owners.
