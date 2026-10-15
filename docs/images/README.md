<!-- SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.0 -->
# READMEの画像と描画条件

このページは原始図形のプリセット一覧と入力比較の2枚を説明します。リダ実モデルのBlender・Unity・UE画像は[実モデルの画像条件](engine-models.md)へ分けています。

Copyright (c) 2026 Lida。出典：[LidaAngelToon](https://github.com/Lida-V/LidaAngelToon)。画像だけが再配布された場合も作者と配布元を確認できるよう、掲載PNGの下部にLida名と出典URLを表示しています。利用条件は[LICENSE](../../LICENSE)と[NOTICE](../../NOTICE.md)に従います。

## 画像の出所

公開版0.1.0のアドオンを、新規作成したUV球へ適用した実レンダーです。AI生成イラストや完成予想図ではありません。外部モデル・制作中のキャラクター・購入素材は読み込んでいません。背景・文字・カード・出典表示を加えた掲載資料で、シェーダーの描画へ加筆はしていません。

- [プリセットの表示例](preset-gallery.png)：1800×1360、代表8種。FaceとMouthを含む全10種の案内は[README](../../README.md#blenderアドオンのプリセット例)を参照。
- [入力値の比較](feature-controls.png)：1800×1710。各行で左右の1入力だけを変えています。別の行同士は比較条件が違います。

使用した公開コード：[mainの元版](https://github.com/Lida-V/LidaAngelToon/tree/87c04f00626a5cd6261aff7ce28cc696f91b9c64)。描画に使うアドオンと手続き画像はこの版から変更していません。PNGの説明用画像は今回の文書更新で追加したもので、既存v0.1.0のRelease資産を置き換えたものではありません。

## 共通条件

Blender 5.2.1 LTS / EEVEE、96 samples。色表示はStandard、Look None、Exposure 0、Gamma 1。白いSun 1灯、energy 1、方向はアドオンの`ensure_sun`の既定値です。正投影カメラを(0, -20, 0)へ置き、+Y方向を見ています。

すべて半径1、128 segments / 64 ringsのUV球で、スムーズシェーディングを使用。AOは未使用（Occlusion=1）、落ち影・輪郭線はOFF。透明背景で描画して、掲載用の白いカードへ配置しました。球の位置を変えても、光・カメラ・形状の条件は共通です。

## プリセット一覧の基本色

基本色は素材の見分けやすさのための表示例で、プリセットが自動で決める色ではありません。以下は線形RGBの入力値です。

| プリセット | Base Color |
|---|---|
| Skin | (0.72, 0.39, 0.30) |
| Hair | (0.19, 0.13, 0.36) |
| Cloth | (0.13, 0.26, 0.50) |
| Feather | (0.84, 0.87, 0.94) |
| Metal | (0.57, 0.64, 0.72) |
| Gem | (0.10, 0.26, 0.52) |
| Eye | (0.09, 0.38, 0.37) |
| Nail | (0.58, 0.23, 0.36) |

`apply_material`による実適用値を使っています。HairのShade Textureには基本色と同じ単色を入力し、HairStreakはOFF。同梱のHairRingを使用し、適用後のMatCap Add Strengthは0.40です。Eyeは材質の表示例であり、虹彩の作成や眼球モデリングのデモではありません。

## 設定比較の条件

| 行 | 元プリセット | 左 → 右で変える入力 | Base Color（線形RGB） |
|---|---|---|---|
| 影のやわらかさ | Cloth | Shade Soft 1：0.015 → 0.35 | (0.19, 0.31, 0.57) |
| 髪のMatCap | Hair | MatCap Add Strength：0 → 0.40 | (0.19, 0.13, 0.36) |
| 白い光沢の圧縮 | Cloth | Highlight Knee：1.0 → 0.55 | (0.76, 0.70, 0.64) |

- 1行目：両側ともMatCap Add Strength=0、Rim Strength=0、Shade Tint 1=(0.44, 0.49, 0.69, 1)、Shade Shift 1=0.15、Shade Shift 2=-1.5。影の境界幅だけを比較します。
- 2行目：両側ともRim Strength=0、Shade Texture=Base Color。HairRingを接続したまま、MatCapを加える強さだけを比較します。
- 3行目：両側ともMatCap Add Strength=0、Rim Strength=0、Spec Strength=0.70、Spec Size=0.70、Spec Soft=0.22。同じ強い光沢を加え、明るさの圧縮を始める値だけを比較します。照明や露出の差ではありません。

MatCapは見る方向に応じた反射模様の表現で、物理的な金属反射・透過・屈折の実装ではありません。モデル・基本色・画像・光・カメラを変えれば見え方も変わります。本資料は任意モデルの完成品質や、別エンジンでの再現を保証しません。
