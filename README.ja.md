# ComfyUI_RS_MultiCharacter_Sampler

**0.1.0a1 · Anima 専用アルファ版**。共通プロンプトと各キャラクターの文章・XY座標を専用パイプで渡し、領域ごとに attention を制御します。RS NAI 拡張や API キーは不要です。

## 使用方法

この非公開リポジトリを `ComfyUI/custom_nodes` に clone し、ComfyUI を再起動してください。モデルの自動ダウンロードはありません。

[2人のサンプルワークフロー](examples/two-characters-anima.json)を読み込み、インストール済みの Anima・テキストエンコーダー・VAE を選びます。サンプルの CLIP タイプは `stable_diffusion` です。通常の LoRA ローダーも利用できます。

1. **RS MultiCharacter Prompts** で人数とキャラクター別の文章を入力します。最大10枠です。人数を減らすと非表示の枠は生成対象から外れます。
2. XY は 0〜1、左上が `(0,0)` です。同一座標の枠は番号順に左から並べます。
3. **RS MultiCharacter Sampler** に全体の人数・画風・背景を入力します。各キャラクターの文章には外見や動作を記入します。試験では各枠に `1girl` / `1boy` を使いました。
4. 最初は30ステップ・CFG 4・Euler ancestral・SGM uniform を使用してください。シードはランダム化できます。
5. 自動保存先は `output/RS_MultiCharacter`。PNG / WebP に生成情報を保存します。ワークフローも埋め込む場合は ComfyUI の通常の Save Image を使ってください。

**RS MultiCharacter Load Image** は元の PNG/WebP から文章と座標を復元します。`character_pipe` をサンプラーに接続し、`use_image_settings` を有効にするとシード・サイズ・サンプリング・領域設定も復元できます。モデル・LoRA・CLIP・VAE は手動接続です。この経路は T2I 再生成であり、img2img ではありません。

## 制限

Anima の単一画像 T2I のみ。実画像試験は1〜6人、入力上限は10人です。**人数が増えるほど品質を保証できません。** 横並びが比較的安定しており、複数行・格子状配置では人数の増減が発生します。

座標は文章を適用する領域であり、身体位置や人数の固定ではありません。1人の場合は画面全体が一つの領域です。キャラクター別ネガティブはメタデータに保存できますが、このアルファの生成ではエラーになります。共通ネガティブを使用してください。30ステップ固定、他のモデル系統・ControlNet・attention パッチは未対応です。

NAI V4 形式のキャプションも読み込めますが、NAI の設定をローカル生成設定として適用することはできません。その場合は `use_image_settings` を無効にしてください。モデルは自動変更されません。

[English](README.md) · [検証記録](docs/validation.md) · [内部構造](docs/architecture.md)
