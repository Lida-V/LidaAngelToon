# LidaAngelToon 仕様 v1（日本語の原文）

この文書は、LidaAngelToon の仕様 v1 の日本語の原文の写しです。公開用に、特定のキャラクターの材質の名前・材質ごとの値・画像・作業の場所（パス）・作業の記録の番号を消し、ファイルの場所をこのリポジトリのものに直してあります。英語の版は [SPEC.md](SPEC.md)。

Blender で決めたトゥーンの見た目（ノードグループ `LidaSoftToon`）を、Unity と UE の自作シェーダー **LidaAngelToon** で同じに出すための決まり。

- シェーダーの名前：Unity `LidaAngelToon/Toon`・`LidaAngelToon/Toon Transparent`、UE `M_LidaAngelToon`・`M_LidaAngelToon_Outline`・`MPC_LidaAngelToon`。Blender のノードグループは `LidaSoftToon` のまま（名前は変えない。中身はこの仕様の式と同じ）。
- シェーダーの文は自分で書いたものだけ。キャラクターの材質の名前・値・画像・パスはシェーダーの文に入れず、材質（Unity の材質・プリセット、UE のマテリアルインスタンス）の側に置く。
- ライセンス：Lida Attribution License 1.1（各ファイルの頭の SPDX `LicenseRef-Lida-Attribution-1.1`）。Blender アドオン（`blender/`）だけ GPL-3.0-or-later。

---

## 1. ファイル（このリポジトリ）

| ファイル | 中身 |
|---|---|
| `core/LidaAngelToonCore.hlsl` | **共通の式**（純粋な関数。Unity は include、UE は下の Custom ノードの文）。文字は ASCII だけ（13 の地雷） |
| `core/scripts/core_reference.py` | 同じ式の Python（numpy）。HLSL と行ごとに `[S01]`〜`[S24]` で対応 |
| `core/scripts/make_ue_custom.py` | core から UE の Custom ノードの文を作る |
| `unreal/LidaAngelToon/Source/hlsl/LidaAngelToon_UECustom_Shade.txt` | UE の Custom ノードに貼る文（色を返す）。手で直さない |
| `unreal/LidaAngelToon/Source/hlsl/LidaAngelToon_UECustom_OutlineWidth.txt` | UE の輪郭線の押し出し量（cm）を返す Custom ノードの文 |
| `unity/com.github.lida-v.lidaangeltoon/` | Unity のパッケージ |
| `unreal/LidaAngelToon/Python/` | UE の資産を作る Python |

---

## 2. 式（やさしい言葉で）

色はすべて**リニア**。画像の色（sRGB）はサンプルするときにリニアに直す。最後に出す色もリニアで、にじみ・表示変換の前の「発光の色」。

1. **向き**：面の向き N、主光へ向かう向き L、カメラへ向かう向き V。N·L（−1〜1）が光の当たり方。
2. **落ち影**：影の中だけ N·L を下げる。`NLs = min(N·L, 落ち影を掛けた N·L)`、受ける強さで混ぜる `Ls0 = mix(N·L, NLs, ReceiveShadow)`。
   - 落ち影を掛けた N·L は、エンジンでは `saturate(N·L) × 影 × 1.25`（`AngelToonShadowedNL`）。**1.25 は Blender の実測**（5 を見る）。
3. **奥の暗さ**：焼いた AO（マスク R、1＝開いている）から `occ = smoothstep(0.05, 0.9, 1 − AO)`、`Ls = Ls0 − occ × OcclusionShift`（奥ほど影になる）。
4. **2 段の坂**：`t1 = smoothstep(Shift1 − Soft1, Shift1 + Soft1, Ls)`（明るい↔影 1）、`t2 = smoothstep(Shift2 − Soft2, Shift2 + Soft2, Ls)`（影 1↔影 2）。
5. **基本色**：白へ寄せる `mix(Base, BaseLiftColor, BaseLift)` → 彩度 `mix(輝度, 色, BaseSaturation)`（輝度は Rec.709 の 0.2126729・0.7151522・0.0721750）。
6. **影の色**：`影 1 = (UseShadeTexture なら影の画像、でなければ基本色) × ShadeTint1`、`影 2 = 影 1 × ShadeTint2`、`明るい色 = 基本色 × LitTint × 主光の色`。
7. **混ぜる**：`C = mix(mix(影 2, 影 1, t2), 明るい色, t1)`。
8. **境目の帯**（肌の淡い赤みなど）：Shift1 の前後 TerminatorWidth の山形の帯で `C × TerminatorColor` を TerminatorStrength だけ混ぜる。
9. **奥の色味**：`mix(C, C × ShadeTint2, occ × OcclusionDarken)`。以下のリム・つや・MatCap は `open = 1 − occ` を掛ける。
10. **リム**：`smoothstep(1 − W − S, 1 − W + S, 1 − max(N·V, 0))` × `mix(1, t1, RimLitBias)` × RimStrength × open を RimColor で足す。
11. **つや**：`H = normalize(L + V)`、`smoothstep(Size − Soft, Size + Soft, max(N·H, 0)) × t1 × SpecStrength × open` を SpecColor で足す。
12. **MatCap**：掛ける `mix(C, C × MatCapMul × 2, MatCapMulStrength)`（0.5＝そのまま）、足す `C + MatCapAdd × (MatCapAddStrength × マスク × open)`。
13. **光に関係ない割合**：`mix(C, 基本色, Unlit)`（目・口・宝石など）。
14. **明るすぎる所**：一番明るいチャンネル m が HighlightKnee（k）を超えた分を `k + (1 − k)(1 − e^(−(m − k)/(1 − k)))` に寄せ、RGB を同じ倍率で縮める（白飛び防止）。
15. Blender の Mix の係数はすべて 0〜1 に切られる（clamp）。式でも同じ所で切る。smoothstep は下限＝上限のとき 0（Blender の Map Range と同じ）。

文そのものは `core/LidaAngelToonCore.hlsl` の `AngelToonShade()`。

---

## 3. 入力と名前の対応

**材質の値**（32 個、材質ごとに固定）：

| Blender（ノードの入力名） | HLSL | Unity のプロパティ | UE のパラメーター |
|---|---|---|---|
| Shade Tint 1 / Shade Shift 1 / Shade Soft 1 | ShadeTint1 / ShadeShift1 / ShadeSoft1 | `_ShadeTint1` / `_ShadeShift1` / `_ShadeSoft1` | ShadeTint1 … |
| Shade Tint 2 / Shift 2 / Soft 2 | ShadeTint2 / ShadeShift2 / ShadeSoft2 | `_ShadeTint2` … | 同 |
| Use Shade Texture / Receive Shadow | UseShadeTexture / ReceiveShadow | `_UseShadeTexture` / `_ReceiveShadow` | 同 |
| Normal Override / Normal Override Mix | NormalOverride / NormalOverrideMix | `_NormalOverride` / `_NormalOverrideMix` | 同 |
| Lit Tint | LitTint | `_LitTint` | 同 |
| Rim Color / Strength / Width / Soft / Lit Bias | RimColor / RimStrength / RimWidth / RimSoft / RimLitBias | `_RimColor` … | 同 |
| Spec Color / Strength / Size / Soft | SpecColor / SpecStrength / SpecSize / SpecSoft | `_SpecColor` … | 同 |
| MatCap Add Strength / MatCap Mul Strength | MatCapAddStrength / MatCapMulStrength | `_MatCapAddStrength` … | 同 |
| Unlit / Highlight Knee | Unlit / HighlightKnee | `_Unlit` / `_HighlightKnee` | 同 |
| Occlusion Shift / Occlusion Darken | OcclusionShift / OcclusionDarken | `_OcclusionShift` … | 同 |
| Terminator Color / Strength / Width | TerminatorColor / TerminatorStrength / TerminatorWidth | `_TerminatorColor` … | 同 |
| Base Lift / Base Lift Color / Base Saturation | BaseLift / BaseLiftColor / BaseSaturation | `_BaseLift` … | 同 |

全部の行は [BLENDER-NODE-MAPPING.md](BLENDER-NODE-MAPPING.md)。色の入力は RGB だけ使う（Blender は RGBA）。LitTint は 1 を超える値もそのまま。

**画素ごとの値**（エンジンが用意する。`AngelToonInput`）：N・L・V・主光の色・落ち影の N·L・基本色・影の画像・AO（マスク R）・落ち影を受ける所（マスク A か 1）・MatCap の 2 つ・MatCap を足す所（マスク A か 1）。画像の入力の名前：

| 中身 | Unity | UE |
|---|---|---|
| 基本色の画像（UV0、sRGB） | `_BaseMap` | BaseMap |
| 影の画像（UV0、sRGB） | `_ShadeMap` | ShadeMap |
| 足す MatCap（sRGB、端はクランプ、bilinear） | `_MatCapAddMap`（色だけなら `_MatCapAddColor`） | MatCapAddMap / MatCapAddColor |
| 掛ける MatCap | `_MatCapMulMap`（色だけなら `_MatCapMulColor`＝0.5） | MatCapMulMap / MatCapMulColor |
| マスク（下の 4） | `_AngelToonMask` | AngelToonMask |
| マスク A をどちらに使うか | `_ReceiveShadowUseMaskA`・`_MatCapAddUseMaskA`（0／1） | ReceiveShadowUseMaskA・MatCapAddUseMaskA |
| 2 層の材質 | `_TwoLayer`（0／1）と 2 組目 `_L2_<名前>` | TwoLayer・L2_<名前> |

MatCap の画像は Unity・UE 版に入っていない（自分で用意する。色だけでも使える）。

---

## 4. マスク画像 `_AngelToonMask`

RGBA・8 bit PNG・**リニア（sRGB をオフで読む）**・UV0（基本色と同じ UV）・2048 以下（512〜1024 で足りる見込み）。

| チャンネル | 意味 | 無いとき |
|---|---|---|
| R | 奥の暗さ（1＝開いている）。焼いた AO など | 1 |
| G | 2 層の割合（1＝2 つ目の層、0＝1 つ目の層） | 0 |
| B | 輪郭線を出す所（0.5 より大きい所だけ。目・口の中などは 0） | 1 |
| A | 材質ごと：落ち影を受ける所（例：顔は首だけ受ける）、または MatCap を足す所（例：髪の天使の輪の範囲）、それ以外は使わない | 1 |

基本色の画像に焼き込むもの（シェーダーには入れない）：頬の赤み、髪の根元→毛先の色など、「基本色」の前にある材質ごとの色の計算すべて。Blender で頂点の値（AO など）から作ったものは、UV の画像（マスク）に焼いて渡す。

---

## 5. 主光・落ち影・環境の光・にじみ・表示

- **主光**：平行光 1 つ。使うのは向きと色（Blender の強さ energy は落ち影の校正にしか効かず、色には掛からない）。基準の場面の光は、キャラクターから見て右・前・上から（右 0.669・前 0.526・上 0.526）。基準の画像では光をカメラと一緒に回した（どの構図でも画面の左上手前から）。
  - エンジンでは場面の主光を使い、キャラクター用の向きに切り替える口を付ける（Unity `_AngelToonKeyDirWS`・`_AngelToonKeyColor`・`_AngelToonKeyOverride`、UE `MPC_LidaAngelToon` の KeyDir・KeyColor・KeyOverride（KeyDirOverride））。
- **落ち影**：Unity は受ける（材質ごとにマスク A で受ける所を決められる）、UE は受けない（Unlit）。**影の強さの倍率 1.25**（`_ShadowGain`、UE は MPC の ShadowGain）。
  - Blender のグループは落ち影を「拡散の明るさ ÷ 0.25464」で測るが、Blender 5.2.1 の EEVEE の実測では影のない所が N·L × 1/π ÷ 0.25464 ＝ **1.25 × N·L** だった。だから Blender では影が 0.8 より薄い所では陰影が変わらない（半影の外側が少し狭い）。エンジンで同じにするには 1.25 を掛ける。ふつうの「N·L × 影」にしたいなら 1.0。
- **環境の光**：Blender は 0。エンジンは少し足す数 `_AngelToonAmbientMix`（UE は MPC の AmbientMix）を用意し、比べるときは 0。
- **にじみ（ブルーム）**：場面の設定に任せる。比べるのはにじみなしで。
- **表示変換**：Blender は「標準」（トーンマップなし、sRGB の表示、露出 0、ガンマ 1）。Unity は Linear・Tonemapping None。UE はトーンカーブ 0 などの後処理の組（[COLOR-AND-TONEMAP.md](COLOR-AND-TONEMAP.md)）。
- 画面の AO（SSAO）は使わない。

---

## 6. 向きの決まり（左右・上下の取り違えに注意）

- **N（面の向き）**：Blender は**裏面を描くとき N を視点側へ反転する**（表が奥を向いた板を手前から見ると、手前向きの N で明るく当たる）。両面の材質（羽など）では、エンジンも裏面で N を反転する（Unity `VFACE`／`SV_IsFrontFace`、UE TwoSidedSign）。N は Blender ではカスタム法線（分割法線）そのもの。
- **L・V**：どちらも「その点から」光へ・カメラへの向き。平行投影の V はカメラの後ろ向きの軸。
- **MatCap**：カメラ空間の法線を正規化し `uv = n.xy × 0.5 + 0.5`。Blender・Unity のカメラ空間は右手系（+X＝画面の右、+Y＝画面の上、+Z＝手前）で、UV の (0,0) は画像の左下。Unity は `AngelToonMatCapUV(mul((float3x3)UNITY_MATRIX_V, N))`。**UE はビュー空間が左手系（+Z が奥）で、画像の上が V＝0** なので `AngelToonMatCapUV_UE()`（V を反転）。右が赤・上が緑・右上に白い点の試験画像を MatCap にして、**赤が画面の右へ、緑が上へ増え、白い点が右上**になれば合っている。
- **座標の換算**（FBX のよくある設定で、キャラクターが前を向く場合の目安。必ず上の目印で確かめる）：Blender (x, y, z) → Unity (−x, z, −y)（キャラクターは +Z を向く）。UE は FBX の読み込みの向きの設定で変わるので、光は「キャラクターから見た向き」で合わせる。
- 確かめの目印：① 主光は画面の左上手前から（正面の顔では画面の左側の頬が明るい）、② MatCap の試験画像の色、③ 裏向きの板が明るい、④ 板に落ちる球の影が板の真ん中に落ちる。

---

## 7. 2 層の材質（肌と服が 1 枚の画像など）

Blender は 1 つ目の組と 2 つ目の組を**別々に最後（寄せ）まで計算して**、仕上がった色をマスク G で混ぜる（Mix Shader）。HLSL は `AngelToonShadeTwoLayer(A, B, G)`。値を混ぜてから 1 回だけ計算するのは同じにならない（式が直線でないため）。足す MatCap を片方の組だけに使ってもよい。輪郭線の色味も G で混ぜる。

---

## 8. 透明・描く順番

不透明・切り抜き・半透明は材質ごとに決める。半透明（BLEND）は `LidaAngelToon/Toon Transparent`（深度を書くかを選べる、`_QueueOffset` で順番を足す）。透明度は基本色の画像のアルファ。羽のような細かい切り抜きは、Unity では不透明のシェーダーの Alpha Clip ＋ Alpha To Coverage（MSAA が要る）、UE では Masked の切り抜き 0.5 がよかった（半透明では重なりの順番が乱れる）。

---

## 9. 輪郭線（「一応うっすら輪郭線が出てアニメっぽく見えるように」）

- **作り**：反転ハル（同じメッシュを法線の向きへ押し出し、表を消して裏だけ描く）。押す向きは**溶接した頂点の法線**がよい（Blender の Solidify は分割法線を使わない）。分割法線で押すと継ぎ目で線が切れるので、平均の法線を別のチャンネルに入れるとよい（Unity のパッケージは UV3 に入れる道具がある）。
- **色**：`元の材質の基本色 × 線の色味`（光・影・寄せは掛けない＝発光そのまま）。黒ではなく下の色を暗くした色で、濃すぎない。
- **出す所**：マスク B が 0.5 より大きい所だけ（目・口の中は出さない）。宝石・目などの材質には線を付けない。
- **太さ（仕様 v1 の決まり B、Unity・UE は必ず入れる）**：世界の mm のままだと全身の距離では約 0.3 画素になって見えない。Unity・UE は**画面の画素で下限と上限を持つ**：

  `画素 = clamp(1.5 × 世界の太さ ÷ その位置の 1 画素の大きさ, 下限, 上限)`
  `1 画素の大きさ ＝ 2 × clip の w ÷ (射影行列 [1][1] × 画面の高さの画素)`（平行投影は w＝1）

  | 種類 | 下限（画素） | 上限（画素） |
  |---|---|---|
  | 肌・服・髪・大きな部品 | 1.0 | 2.0 |
  | 顔 | 1.0 | 1.8 |
  | 小さな花・飾り | 0.8 | 1.6 |
  | 銀・金属の細い縁 | 0.7 | 1.3 |

  結果の目安：全身 1080p は肌・服・髪・顔 1.0 画素、銀 0.7、花 0.8。顔の近く（800 画素、85 mm・0.8 m）は服・肌 1.9〜2.0、髪 1.7〜2.0、顔 1.4、銀 1.0〜1.1。同じ構図を 1080p で撮ると服・髪 2.0、顔 1.7〜1.8。
  - HLSL：`AngelToonPixelWorldSize`・`AngelToonOutlinePixels(世界の太さ, 1 画素, 1.5, 下限, 上限)`・`AngelToonOutlinePushClip`（clip 座標で投影した法線の向きへ押す）。`_OutlinePixelRule`＝0 にすると Blender と同じ世界の mm。
  - UE：輪郭線は 2 つ目の Skeletal Mesh Component（Leader Pose）に `M_LidaAngelToon_Outline`（Unlit・Masked・TwoSided、裏だけ残す）。WPO ＝ 頂点の法線 × `LidaAngelToon_UECustom_OutlineWidth.txt` の値（cm）。
- **VRM（MToon）の案**：`outlineWidthMode = screenCoordinates`、`outlineWidthFactor` 肌・服・髪 0.0011、顔 0.0010、花 0.0008、銀 0.0007（1080p で 1.2・1.1・0.9・0.8 画素）。UniVRM 0.131.2 は画面の高さの割合で、約 1/tan(縦の画角/2) m まで距離によらず同じ太さ（その先は細くなる）。MToon は輪郭線の太さのマスクを G で読むので、B の値を G に入れた別の画像が要る。くわしくは [OUTLINE-RULE-B.md](OUTLINE-RULE-B.md)。

---

## 10. 掛ける層（描いた影の層）

下の色に掛けるだけの層：`dst.rgb *= mix(1, 層の色, 画像のアルファ)`。顔の上に描いた影の層などに使う。顔の後に描く、深度は書かない、線なし。Unity は `LidaAngelToon/Toon Transparent` の `_MultiplyLayer`、UE は `M_LidaAngelToon_MultiplyLayer`（LayerColor・LayerStrength）。描かない材質（完全に透明の部品など）は書き出さないか、描かない。

---

## 11. 確かめの場面と基準の画像

- 確かめの場面（Blender、このリポジトリには入っていない）：球（半径 0.1 m、UV 球 128×64、なめらか）13 個（種類ごと 11、2 層 1、MatCap の向きの試験 1）、板 2 枚（落ち影、裏面）、キャラクターの顔。球の AO：上半分 1、下半分は下へ 0.1 まで。マスク（落ち影を受ける所・天使の輪の所・2 層の割合）：左の端 0 → 右の端 1。カメラは平行投影 2 台（球 1300×850 で 1 画素 1 mm、顔 800×800）。
- 基準の画像：64 サンプル、フィルタ 1.5、にじみありとにじみなし、PNG と リニアの EXR。キャラクターの構図は全身の正面・斜め、顔の正面・斜め、髪の後ろ、背中、輪郭線の比べ用に全身 1080p。
- 比べ方：同じカメラの値（位置・向き・平行投影の高さか縦の画角・解像度）と同じ光で撮り、**にじみなし**の画像と比べる。目安：確かめの場面の球と板は sRGB の差 平均 2/255 以下・最大 8/255 以下（影の縁と輪郭の画素を除く）、キャラクターは目で（画像の並べ）。

---

## 12. 合った程度（Blender の描画 vs Python vs GPU の HLSL）

確かめの場面を 1 サンプル・フィルタなしで描き、グループに入る値を全部 AOV で取り出して、同じ画素で計算し直した。

| | 画素 | Python と Blender（リニアの差） | GPU の HLSL と Blender | GPU と Python |
|---|---|---|---|---|
| 球・板 15 材質 | 488,460 | 平均 0.00013・最大 0.0025・sRGB で最大 1/255 | 同じ（RTX 4090、WARP も） | 最大 0.0000015 |
| 顔（キャラクターの顔の材質 3 つ） | 340,292 | 平均 0.00021・最大 0.0011・最大 1/255 | 同じ | 最大 0.0000003 |

- そのほか：輝度の係数の差 最大 0.0005、MatCap の UV の差 最大 0.0006（AOV の精度の内）、裏面の N は視点側へ反転、MatCap の向き（赤 右・緑 上）、落ち影の倍率 1.2497（中央値）。
- コンパイル：fxc ps_5_0・vs_5_0、dxc ps_6_0・vs_6_0（core）、UE の Custom ノードの文を UE と同じ形（関数の中）に包んで fxc・dxc で通った。
- エンジンでの結果（Blender とのにじみなしの差、sRGB）：Unity は球と板で平均 0.10/255、顔で平均 0.33。UE は球と板で平均 0.43/255、顔で平均 0.64〜0.80。キャラクターの全身 7 構図は Unity 平均 2.4〜2.7、UE 平均 1.9〜3.2（UE は落ち影を受けない）。

---

## 13. Unity・UE で使うときの注意（地雷）

- **シェーダーの文は ASCII だけにする**。日本語のコメントがあると dxc が「0x80070459（文字の変換ができない）」で止まった（UE の DXC も同じ扱いになる見込み）。文の説明はこの文書に書く。
- UE の Custom ノードは関数の中に貼られるので、関数は「関数を持つ構造体」の中に入れてある（生成した文をそのまま貼る）。コアを直したら `python -I core/scripts/make_ue_custom.py . unreal/LidaAngelToon/Source/hlsl dist/ue_custom_check.hlsl`（リポジトリの場所で）で作り直す。
- UE は cm。mm の値は ×0.1。
- テクスチャ：基本色・影の画像・MatCap は sRGB、マスクと毛筋の画像はリニア。MatCap は端をクランプ。
- 2 層の材質は 2 回計算して混ぜる（値を混ぜない）。
- 落ち影の倍率 1.25、環境の光 0（比べるとき）、トーンマップなし、にじみなしで比べる。
- Unity の URP 17.6・Forward+：本体は `UniversalForward`、輪郭線は 2 つ目のパス（`SRPDefaultUnlit`、表を消す）、`ShadowCaster`・`DepthOnly`・`DepthNormals` も入れる。輪郭線は `_OutlinePixelRule`＝1 を既定に。

---

## 14. 知られている違い・残り

- Blender の落ち影はやわらかい影（太陽の角度 6°、ジッター）。エンジンのシャドウマップとは縁が違う。式（影の値の使い方）は同じ。
- Blender の拡散の確かめの値（1/π）は 5.2.1 の EEVEE で測った値。0.25464 はグループの中の校正の数。仕様は「見えている Blender」に合わせて 1.25 にした。
- 輪郭線の太さの決まりの Blender の見本は物体ごとの近似（物体の中心の奥行きで 1 つの太さ）。Unity・UE は頂点ごとなので、奥行きの大きい物体（スカートなど）では少し違う。
