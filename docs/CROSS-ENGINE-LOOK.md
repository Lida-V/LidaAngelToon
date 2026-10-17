<!-- SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.1 -->
# エンジン間の外観差と、ショット間の一貫性

© 2026 Lida · 出典：[LidaAngelToon](https://github.com/Lida-V/LidaAngelToon)

## Blender・Unity・Unrealを移動すると、どこに調整が必要ですか？

今回のキャラクターで差を確認したのは、**肌・髪の色と明暗、髪の影や艶、輪郭線、羽の透過**です。調整量や工数の順位は計測していません。

最初に色管理と露出を揃え、その後で影の境界・濃さ、髪のハイライト、輪郭線を確認します。同じ色の画像でも、sRGBの取り込み設定やトーンマッピングが違うと印象が変わります。取り込みが誤ったまま素材色を塗り直すと、別の環境で再びずれます。

現在のUE版はUnlit方式で、ほかの物体や髪が落とす影を受けません。Blender基準と同じ形でも、前髪の奥行きが弱く見える箇所があります。材質の数値を揃えるだけでは、この仕様差はなくなりません。

| 確認する所 | 調整・確認の方法 | 今回の比較から分かったこと |
|---|---|---|
| 色と明暗 | カメラ・主光・露出・トーン設定を揃える。通常のsRGB基本色画像はsRGB、数値マスクはlinearなど、画像の役割・元の色空間に合わせて読む | UEで色画像が法線マップと自動判定され、sRGBがOFFのままになった例があった。圧縮設定を先に直し、sRGBを設定・再確認する |
| 影と髪の立体感 | 影の境界・幅・濃さと、自己落ち影の有無を分けて比べる | UEの落ち影なし、Unityの髪の自己落ち影の弱さは、形状の違いと分けて判断した |
| 髪の艶 | MatCapの強さ・向きと毛筋マスクを、正面・斜め・横で確認する | MatCapは見る方向に応じて変わる。正面だけの一致では判断できない |
| 輪郭線 | 顔アップと全身を同じ解像度で比べ、線幅・色・法線を確認する | 画面上の幅を基準にする[輪郭線の決まりB](OUTLINE-RULE-B.md)を使った。細い線の見え方にはAA方式の差も残る |
| 羽などの透過 | 重なりが入れ替わる向きと動作で、描画順・切抜きの縁・ちらつきを見る | 半透明には描画順の問題があり、切抜きには半透明の縁が失われる違いがある。方式を変えたら再確認する |

口内の暗さを、全環境に共通する基本色の変更で改善した例もあります。これは元の材質の修正で、エンジン固有差を補正した例とは区別します。

## 映画で、同じキャラクターに見えるように保つには？

次は今回の比較を基にした推奨手順です。映画全編での検証済み工程ではありません。「同じキャラクターに見えること」と「全画素の一致」は別に判定します。

1. **開始ゴールを決めます。** 用途、見る距離、必要な表情・動作、保持する色・形・特徴を短く記録します。終了条件の例は「顔の正面・斜め・横と全身で、肌・髪・目の色と特徴的な影・艶を保つ」です。
2. **基準画像と材質プリセットを保存します。** 同じモデル版・表情・ポーズを使い、カメラ位置・向き・画角・解像度・主光を記録します。比較時は固定露出にし、ブルームやトーン曲線の影響を外します。[色とトーンマップの設定](COLOR-AND-TONEMAP.md)を参照してください。
3. **差の原因を分けます。** 全体の露出差、画像の取り込み設定、特定材質の色、影の仕様差を順に切り分けます。一度に変える項目を絞り、前後画像と変更値を残します。形・UV・表情を変える必要がなければ保持します。
4. **ショットの仕上げ後にも見比べます。** キャラクターの基準プリセットと、ショットごとの照明・露出・カラー調整を別に記録します。素材色をショットごとに変える前に撮影側の違いを確認し、最終の顔アップ・横顔・シルエット・動作で認識を判定します。

固定露出とトーン曲線なしは**比較用の条件**です。映画本番の照明やカラーグレーディング、トーンマッピングを一律に禁止するものではありません。基準の光を各ショットで使い続ける必要もありません。

AIへの依頼例：

> 基準モデルと材質プリセットを使い、顔の正面・斜め・横と全身を、記録したカメラ・主光・固定露出で比較してください。取り込みと色管理を確認してから、基本色・影・髪の艶・輪郭線・透過を別々に調整してください。形・UV・表情は保持し、仕様上揃わない所は記録してください。同条件の前後画像、変更値、使用先の確認結果、残件を提出してください。本番ショットの仕上げ後も基準と比較してください。

## English reply

Thank you! On this character, the areas that needed particular attention were skin and hair colour, hair shading and highlights, outlines, and feather transparency. I have not measured which took the most adjustment.

I first matched colour management and exposure. The same textures can look different when sRGB import settings or tone mapping differ. After checking that baseline, I adjusted shadow thresholds and strength, hair highlights, and outline width. MatCap highlights are view-dependent, so I checked more than the front view.

One limitation of the current Unreal version is that it uses an Unlit implementation and does not receive cast shadows. Some depth in the bangs therefore looks flatter than in the Blender development reference, even with the same geometry. Matching material values alone cannot remove that difference. Transparency also needs checking from several angles: alpha blending can have sorting problems, while cut-outs change the soft edges.

For your film, I would keep a character material preset and front, three-quarter, profile and full-body reference images under a fixed reference light. Record the model version, camera, resolution, light and exposure. Compare each finished shot against those references while adjusting its lighting and colour grade, preserving the character's defining colours, shading, highlights and silhouette. Keep shot adjustments separate from the character baseline. This is a suggested workflow based on these comparisons, not a pipeline validated across an entire film. Fixed exposure and a disabled tone curve are comparison conditions, not restrictions on your final look.

## 確認範囲と参照

実モデルのBlender列は制作材質`LidaSoftToon`の開発基準で、配布Blenderアドオンの実モデル適用例ではありません。Unity・UEはモデル専用の画像・マスク・MatCap・プリセットを設定した例です。配布物の初期値だけで同じ外観になる保証や、Blenderアドオンと共通HLSLの数値一致は示していません。

- [実モデルの比較条件と画像](https://github.com/Lida-V/LidaAngelToon/blob/main/docs/images/engine-models.md)：確認した環境、材質、カメラと比較の範囲。
- [色とトーンマップ](COLOR-AND-TONEMAP.md)：画像の色空間、露出、各環境の比較設定。
- [輪郭線の決まりB](OUTLINE-RULE-B.md)：全身と顔アップでの画面上の線幅。
- [Unreal Engine公式：Auto Exposure](https://dev.epicgames.com/documentation/unreal-engine/auto-exposure-in-unreal-engine)、[Unity公式：URPのトーンマッピング](https://docs.unity3d.com/ja/current/Manual/urp/post-processing-tonemapping.html)：比較設定を選ぶときの参考。

© 2026 Lida · Source: https://github.com/Lida-V/LidaAngelToon
