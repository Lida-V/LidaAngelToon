# 導入と更新

この文書は Blender アドオンの導入です。Unity は [unity/README.md](../unity/README.md)、Unreal Engine は [unreal/README.md](../unreal/README.md) を見てください。

## 用意するもの

- Blender 5.2.1 LTS。表示エンジンはEEVEE。
- 自分で使えるメッシュ。最初はBlenderの球で確認できます。
- Principled BSDFから出力している材質。色画像、AO、髪のマスクは必須ではありません。

## ZIPを入れる

1. [配布元](https://github.com/Lida-V/LidaAngelToon)のReleasesから末尾が `-blender-addon.zip` のファイルを取得します。
2. Blenderの「編集 → プリファレンス → アドオン」で「ディスクからインストール」を選び、ZIPを指定します。
3. LidaAngelToonを有効にします。EEVEEのシーンでメッシュを選び、3Dビューの `N` キーから同名タブを開きます。

ソースZIPは開発者向けです。ソースの `blender/lida_angel_toon/` だけを取り出して配る場合も、LICENSE・NOTICE・LICENSESを保持してください。通常の利用はaddon ZIPを使います。

## 初回の確認

`Cloth` → `Apply to selected meshes` → レンダー表示の順です。主光は `Main sun` で選びます。Sunが存在しないときだけ新規作成し、既存ライトを選んだ場合は光の設定を変えません。全材質は1つの主光を共有します。

基本色の画像接続、定数色、法線の接続を引き継ぎます。元のAlphaが1未満、または接続済みなら透明の混合も作ります。複雑な独自ノード、複数のPrincipledの混合は対象外です。

## 主な項目

| 項目 | 使い方 |
|---|---|
| Material | 布、肌、顔、髪、金属、宝石、目、爪、羽、口から自分で選ぶ |
| Copy shared material | 他の物体と共用する材質をコピーしてから適用。初期値オン |
| Receive cast shadows | 主光1個・環境光0のEEVEEシーンでのみ使用。初期値オフ |
| AO attribute | 任意のFLOAT属性名。1が明るく、0が奥。未指定なら焼いたAOを使わない |
| Hair streak mask | UVのV方向が毛の流れである髪に使用。頭頂の範囲を自動判定しない |
| Add outline | メッシュを押し出した反転ハルを追加。全身表示では太さを調整する |

`Restore original material`で元の出力へ戻し、選択物体の本アドオンの輪郭線モディファイアを外します。生成済みのノード・画像・未使用材質スロットは残るため、元の制作データを完全に復元するには適用前の保存版を使います。

## 更新

1. 制作ファイルを保存し、変更したプリセットやコードを退避します。
2. Blenderでアドオンを無効化し、新版のaddon ZIPをインストールします。
3. 有効にして球で確認後、制作ファイルのコピーで適用します。

既に適用した材質は、新版を入れただけでは自動更新しません。画像は適用時にblendへ同梱します。再適用はノードの値を入れ直すので、手動の調整を先に控えてください。
