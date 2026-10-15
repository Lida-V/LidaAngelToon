# LidaAngelToon

**Blender EEVEE用の、やわらかい2段階トゥーンシェーダーです。** バージョン0.1.0。
肌・髪・布・金属などのプリセットを選び、選択したメッシュの材質へ適用できます。モデル本体は含みません。

配布元：[Lida-V/LidaAngelToon](https://github.com/Lida-V/LidaAngelToon)

## 初めて使う

1. Releasesから `lida_angel_toon-0.1.0-addon.zip` を取得します。
2. Blenderの「編集 → プリファレンス → アドオン → ディスクからインストール」で、そのZIPを展開せずに選びます。LidaAngelToonを有効にします。
3. レンダーエンジンを **EEVEE** にします。まず球を1つ追加し、3Dビューで `N` キーを押して **LidaAngelToon** を開きます。
4. `Cloth`を選び、`Apply to selected meshes`を押します。「レンダー」表示にすると見えます。Sunがなければ1個作ります。

既存の基本色と画像の接続を引き継ぎます。各選択メッシュの**アクティブ材質だけ**が対象です。元のノードは残し、`Restore original material`で元の出力へ戻せます。適用前のファイルも保存してください。

詳しい導入・更新：[INSTALL](docs/INSTALL.md)。対応と制限：[SUPPORT](docs/SUPPORT.md)。
実際に確認した範囲：[VALIDATION](docs/VALIDATION.md)。

## できること

- 明るい色と2段の影をなめらかにつなぐ陰影。
- 肌の影の境目の色、縁の光、小さなつや、MatCap。
- 白い素材の明るさを抑えるHighlight Knee。
- 任意のAO属性、髪の毛筋マスク、反転ハルの輪郭線。
- 自作のMatCap5枚と毛筋マスク1枚。画像の生成器も収録しています。

材質の細かな値はShader Editorの `LidaAngelToon` ノードで調整します。プリセットを再適用すると値を入れ直します。

## 対応範囲

**Blender 5.2.1 LTS / EEVEEで検証済み。** Cycles、他のBlender版、Unity、Unreal Engineは未対応・未検証です。Unity/UE実装やVRMへの自動変換は収録していません。Blenderで表示できることは、別の使用先で同じ見た目になる保証ではありません。

ランタイムに外部Pythonパッケージは不要です。AOは任意で、未指定なら1（奥の暗さなし）。顔の形や髪の頭頂を自動検出する処理はありません。形状・骨・ウェイト・表情は変更しません。輪郭線を選んだ場合のみSolidifyモディファイアと材質スロットを追加します。

## 配布条件と出典

[LICENSE](LICENSE)が適用範囲の案内、[NOTICE](NOTICE.md)が出典情報です。
Blenderアドオン／bpyを使うテストは **GPL-3.0-or-later**。自作画像・文書・Blenderに依存しない生成器は、同梱の **Lida Attribution License 1.0** が対象です。ファイルのSPDX表示も確認してください。

通常の描画画像や、シェーダーで作ったモデル成果へのクレジットは不要です。アプリ、配布コード、派生Skillsへ本資料やコードを組み込んで公開する際は、LICENSEとNOTICEの出典情報を残してください。GPL部分には独自ライセンスの追加制限を課しません。GPLのアドオンを使用しただけで、モデルや描画成果がGPLになるわけではありません。

## 開発者向け

```text
python -m unittest discover -s tests -p "test_*.py"
python scripts/validate_release.py
python scripts/build_release.py
```

配布ZIPは `dist/` へ作成します。`manifest.json` のallowlistだけを梱包し、モデル・FBX・VRM・参考モーション・外部素材を拒否します。依存ライブラリを同梱しません。

手続き画像を再生成する場合だけ `python -m pip install -r requirements-dev.txt`、続いて `python tools/generate_textures.py` を実行します。

Blender本体で原始図形の描画・保存・再読込を確認する例：

```text
blender --background --factory-startup --python tests/blender_smoke.py -- --output dist/smoke
```

検査は任意のモデルを開かず、球と自作テクスチャだけで行います。確認用blend/PNGは公開ZIPに含めません。
