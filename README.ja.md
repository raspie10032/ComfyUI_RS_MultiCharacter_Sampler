# ComfyUI_RS_MultiCharacter_Sampler

**0.1.0-alpha1 · Anima 専用アルファ版**。共通プロンプトと各キャラクターの文章・XY座標を専用パイプで渡し、領域ごとに attention を制御します。RS NAI 拡張や API キーは不要です。

## 使用方法

ComfyUI-Manager で **RS MultiCharacter Sampler (Anima Alpha)** を検索するか、[Comfy Registry](https://registry.comfy.org/publishers/raspie10032/nodes/comfyui-rs-multicharacter-sampler) からインストールします。パッケージ ID は `comfyui-rs-multicharacter-sampler` です。インストール後に ComfyUI を再起動してください。新しい項目が表示されない場合は Manager の一覧を更新するか、Git でインストールできます。

Git の場合はこのリポジトリを `ComfyUI/custom_nodes` に clone します。既存の Git インストールがある場合は重複インストールせず、そちらを更新してください。モデルの自動ダウンロードはありません。

[ワークフロー入りの元PNG](examples/two-characters-workflow.png)をキャンバスにドロップするか、[2人のサンプルJSON](examples/two-characters-anima.json)を読み込み、インストール済みの Anima・テキストエンコーダー・VAE を選びます。サンプルの CLIP タイプは `stable_diffusion` です。通常の LoRA ローダーも利用できます。

1. **RS MultiCharacter Prompts** で人数とキャラクター別の文章を入力します。最大10枠です。人数を減らすと非表示の枠は生成対象から外れます。
2. XY は 0〜1、左上が `(0,0)` です。同一座標の枠は番号順に左から並べます。
3. **RS MultiCharacter Sampler** に全体の人数・画風・背景を入力します。各キャラクターの文章には外見や動作を記入します。試験では各枠に `1girl` / `1boy` を使いました。
4. 最初は30ステップ・CFG 4・Euler ancestral・SGM uniform を使用してください。シードはランダム化できます。
5. 自動保存先は `output/RS_MultiCharacter`。PNG / WebP に生成情報を保存します。ワークフローも埋め込む場合は ComfyUI の通常の Save Image を使ってください。

**RS MultiCharacter Load Image** は元の PNG/WebP から文章と座標を復元します。`character_pipe` をサンプラーに接続し、`use_image_settings` を有効にするとシード・サイズ・サンプリング・領域設定も復元できます。モデル・LoRA・CLIP・VAE は手動接続です。この経路は T2I 再生成であり、img2img ではありません。

共有用サンプルPNGには ComfyUI の `workflow` と `prompt` メタデータが入っています。通常の自動保存は従来どおり生成情報のみです。

## サンプラーとスケジューラー

インストール済み ComfyUI に登録されているサンプラーとスケジューラーを**すべて選択**できます。まずは既定の組み合わせを使い、必要に応じて次の候補も試してください。選択欄のツールチップにも同じ候補を記載しています。

| 用途 | サンプラー | スケジューラー | 今回の試験での観察 |
| --- | --- | --- | --- |
| 既定の開始点 | `euler_ancestral` | `sgm_uniform` | 各キャラクターの特徴と共通背景が鮮明 |
| 別の構図を試す | `euler` | `linear_quadratic` | 特徴を保ち、向かい合って座る指示も反映 |
| 鮮明な別候補 | `dpmpp_2m_sde_gpu` | `beta` | 髪・服・カップが区別できる。ただし対面ではなく横並び |

条件は **Anima Base v1.0・2人のカフェ場面・1シード・1536×768・30ステップ・CFG 4・LoRAなし**。45×9=405通りすべて生成は完了しましたが、品質まで合格したわけではありません。上記は試す際の候補であり、多様な場面での成功率や順位ではありません。

両方の項目を手動で選択します。推奨外の組み合わせも使用でき、自動置換や選択肢の改名は行いません。既定値は `euler_ancestral + sgm_uniform` のままです。選択肢は ComfyUI のバージョンによって異なります。

一部の CFG++ は今回の固定条件で品質が低下しましたが、低CFG・少ステップでの再試験は未実施です。未対応と断定するものではありません。現アルファは **30ステップ固定・CFG 1〜20**で、それより低いCFGや別のステップ数の推奨値はありません。[全組み合わせ試験と推奨の根拠](docs/sampler-combinations.md)

## 制限

Anima の単一画像 T2I のみ。実画像試験は1〜6人、入力上限は10人です。**人数が増えるほど品質を保証できません。** 横並びが比較的安定しており、複数行・格子状配置では人数の増減が発生します。

座標は文章を適用する領域であり、身体位置や人数の固定ではありません。1人の場合は画面全体が一つの領域です。キャラクター別ネガティブはメタデータに保存できますが、このアルファの生成ではエラーになります。共通ネガティブを使用してください。30ステップ固定、他のモデル系統・ControlNet・attention パッチは未対応です。

NAI V4 形式のキャプションも読み込めますが、NAI の設定をローカル生成設定として適用することはできません。その場合は `use_image_settings` を無効にしてください。モデルは自動変更されません。

[English](README.md) · [検証記録](docs/validation.md) · [内部構造](docs/architecture.md)
