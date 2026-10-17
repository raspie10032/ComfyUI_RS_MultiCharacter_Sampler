# ComfyUI_RS_MultiCharacter_Sampler

**0.1.2 ベータ · Anima・SDXL・Krea 2・MOSS**。共通プロンプトと各キャラクターの文章・XY座標を専用パイプで渡し、領域ごとに attention を制御します。RS NAI 拡張や API キーは不要です。

**0.1.2 ベータ更新:** ローカルのキャラクターディテイラー・検出/タグローダー、SDXL・Krea 2・MOSS での生成、インストール済み全サンプラー/スケジューラーの選択に対応しました。[変更点と検証範囲](docs/release-0.1.2.md)

## 使用方法

ComfyUI-Manager で **RS MultiCharacter Sampler (Beta)** を検索するか、[Comfy Registry](https://registry.comfy.org/publishers/raspie10032/nodes/comfyui-rs-multicharacter-sampler) からインストールします。パッケージ ID は `comfyui-rs-multicharacter-sampler` です。インストール後に ComfyUI を再起動してください。新しい項目が表示されない場合は Manager の一覧を更新するか、Git でインストールできます。

Git の場合はこのリポジトリを `ComfyUI/custom_nodes` に clone します。既存の Git インストールがある場合は重複インストールせず、そちらを更新してください。拡散モデル・テキストエンコーダー・VAEは別途用意します。ディテイラーの検出・タグローダーは、選択したカタログモデルが未導入の場合に実行時ダウンロードし、進捗を表示します。

[ワークフロー入りの元PNG](examples/two-characters-workflow.png)をキャンバスにドロップするか、[2人のサンプルJSON](examples/two-characters-anima.json)を読み込み、インストール済みの Anima・テキストエンコーダー・VAE を選びます。サンプルの CLIP タイプは `stable_diffusion` です。通常の LoRA ローダーも利用できます。

1. **RS MultiCharacter Prompts** で人数とキャラクター別の文章を入力します。最大10枠です。人数を減らすと非表示の枠は生成対象から外れます。
2. XY は 0〜1、左上が `(0,0)` です。同一座標の枠は番号順に左から並べます。
3. **RS MultiCharacter Sampler** に全体の人数・画風・背景を入力します。各キャラクターの文章には外見や動作を記入します。試験では各枠に `1girl` / `1boy` を使いました。
4. 最初は30ステップ・CFG 4・Euler ancestral・SGM uniform を使用してください。シードはランダム化できます。
5. 自動保存先は `output/RS_MultiCharacter`。PNG / WebP に生成情報を保存します。ワークフローも埋め込む場合は ComfyUI の通常の Save Image を使ってください。

**RS MultiCharacter Load Image** は元の PNG/WebP から文章と座標を復元します。`character_pipe` をサンプラーに接続し、`use_image_settings` を有効にするとシード・サイズ・サンプリング・領域設定も復元できます。モデル・LoRA・CLIP・VAE は手動接続です。この経路は T2I 再生成であり、img2img ではありません。

共有用サンプルPNGには ComfyUI の `workflow` と `prompt` メタデータが入っています。通常の自動保存は従来どおり生成情報のみです。

## SDXL の実験対応

[SDXL 2人用ワークフロー](examples/two-characters-sdxl.json)は通常のチェックポイントローダーから MODEL・CLIP・VAE を受け取ります。Illustrious XL v1.0 と NoobAI XL epsilon-pred 1.1 で実生成と左右の文章交換を試験しました。SDXL 全派生モデルや全サンプラーの検証ではありません。

例の開始値は **30ステップ・CFG 5.5・Euler ancestral + normal**、共通強度 **0.3**、キャラクター強度 **1.3**、境界分離 **0.5** です。既存の Anima の初期値は維持します。Anima の 0.05 / 1.7 / 0.9 をそのまま使うと、パネル状の境界が目立つ場合があります。

XY は文章の適用領域を指定し、正確な人数や姿勢を保証しません。多人数・格子配置では人物の重複、特徴の混合、画面分割が発生します。SDXL Refiner・インペイントモデル・ControlNet・他の attention パッチは非対応です。PNG/WebP は SDXL の生成情報を保存し、画像ローダーで復元できます。[方式と試験結果](docs/sdxl-validation.md)



## Krea 2 / MOSS-Image 実験対応

両モデルを標準で扱える最新の ComfyUI が必要です。`Load CLIP` に `krea2` / `moss_image` がなければ、ComfyUI とその実行環境の依存関係を更新してください。モデル選択だけではサンプリング設定は変わりません。

| モデル | 例 | テキストエンコーダー / VAE | 開始設定 |
| --- | --- | --- | --- |
| Krea 2 Turbo | [2人ワークフロー](examples/two-characters-krea2.json) | Qwen3-VL 4B, `krea2` / Qwen Image VAE | 8ステップ · CFG 1 · Euler + simple |
| MOSS-Image SFT | [2人ワークフロー](examples/two-characters-moss.json) | Qwen3.5 9B, `moss_image` / Flux2 VAE | 50ステップ · CFG 3 · Euler + simple |

MODEL・CLIP・VAE と既存のキャラクターパイプを接続します。共通欄には場面、個別欄には各人物の外見や行動を自然言語で記入します。Krea 2 Turbo の CFG 1 では共通ネガティブは影響しません。MOSS の例は通常の ComfyUI CFG を使用し、公式パイプラインのネガティブ分岐22番レイヤーの省略は適用しません。

サンプラーは **2～100ステップ** に対応し、Anima / SDXL の既定値は30のままです。XY はプロンプトの領域指定であり、正確な人数・姿勢・複雑な相互作用を保証しません。対応範囲は T2I です。参照画像の編集と新モデルでのディテーラー品質は未検証です。[モデルファイル・利用条件・検証範囲](docs/krea-moss-validation.md)も参照してください。


## ローカルのマルチキャラクター・ディテイラー

Manager から **ComfyUI-Impact-Pack** と **ComfyUI-Impact-Subpack** を導入し、**ComfyUI の Python 環境**で `requirements-detailer.txt` をインストールして再起動します。SAM は任意で、使用するモデルの事前導入が必要です。一部のタグモデルには、選択時に案内される追加依存関係が必要です。

[生成 → ディテイラーのサンプル](examples/two-characters-detailer-anima.json)を読み込みます。生成に使う MODEL・CLIP・VAE（LoRA を含む）をディテイラーにも接続し、サンプラーの `image` と `character_pipe` を渡してください。**RS 検出コンバインローダー**と**RS キャラクタータグローダー**も接続します。既存画像には **RS MultiCharacter Load Image** の画像とパイプを使用できます。

最初は既定の顔 SEGM・WD ViT v3・**denoise 0.25**を使用してください。基本表示は補正強度・シード・自動保存で、クロップ・マスク・照合・サンプリング設定は詳細オプションにあります。SEGM を選ぶと BBOX・SAM は読み込みません。SEGM が OFF の場合は BBOX 単独または BBOX + SAM を使用します。OFF のモデルは実行しません。`ultralytics/segm`・`ultralytics/bbox`・`sams` に追加したモデルも一覧更新後に選択できます。

タグ推論はキャラクターの照合だけに使用し、補正には**入力した元の文章**を使います。穴埋めと凹凸の補修は既定で有効です。元画像から各クロップを取り、修正マスクの重複を防ぎます。判定が曖昧な領域はそのまま残し、理由をレポートに記録します。高いスコアでも誤認識はあり得るため、特に似た外見の場合はレポートのキャラクター番号と結果を確認してください。パイプは**最大10人**、補正領域は**既定10・最大64個**です。処理数が増えるほど品質を保証できません。

PNG/WebP の自動保存は元の生成設定を保持し、補正履歴を別に追加します。ワークフローが必要な場合は通常の Save Image を使用してください。PNG・可逆 WebP は適用マスク外の画素を保持しますが、非可逆 WebP は圧縮によって変わる場合があります。実際の補正検証は Anima のみで、他のモデル系列は未確認です。[検証記録](docs/detailer-validation.md)


## サンプラーとスケジューラー

インストール済み ComfyUI に登録されているサンプラーとスケジューラーを**すべて選択**できます。まずは既定の組み合わせを使い、必要に応じて次の候補も試してください。選択欄のツールチップにも同じ候補を記載しています。

| 用途 | サンプラー | スケジューラー | 今回の試験での観察 |
| --- | --- | --- | --- |
| 既定の開始点 | `euler_ancestral` | `sgm_uniform` | 各キャラクターの特徴と共通背景が鮮明 |
| 別の構図を試す | `euler` | `linear_quadratic` | 特徴を保ち、向かい合って座る指示も反映 |
| 鮮明な別候補 | `dpmpp_2m_sde_gpu` | `beta` | 髪・服・カップが区別できる。ただし対面ではなく横並び |

条件は **Anima Base v1.0・2人のカフェ場面・1シード・1536×768・30ステップ・CFG 4・LoRAなし**。45×9=405通りすべて生成は完了しましたが、品質まで合格したわけではありません。上記は試す際の候補であり、多様な場面での成功率や順位ではありません。

両方の項目を手動で選択します。推奨外の組み合わせも使用でき、自動置換や選択肢の改名は行いません。既定値は `euler_ancestral + sgm_uniform` のままです。選択肢は ComfyUI のバージョンによって異なります。

一部の CFG++ は今回の固定条件で品質が低下しましたが、低CFG・少ステップでの再試験は未実施です。未対応と断定するものではありません。サンプラーは **2～100ステップ・CFG 1〜20** に対応します。Anima の推奨は元の30ステップ試験に基づき、低CFG・少ステップの CFG++ 回復は未検証です。[全組み合わせ試験と推奨の根拠](docs/sampler-combinations.md)

## 制限

対応する Anima・SDXL・Krea 2・MOSS の単一画像が対象です。サンプラーは T2I、ディテイラーはマスク付きクロップの img2img を実行します。入力上限は10人です。実画像試験は Anima 1〜6人、SDXL 2〜6人、Krea 2・MOSS 2〜4人です。**人数が増えるほど品質を保証できません。** 横並びが比較的安定しており、新モデルの2×2成功例も一般的な成功率を示すものではありません。

座標は文章を適用する領域であり、身体位置や人数の固定ではありません。1人の場合は画面全体が一つの領域です。キャラクター別ネガティブはメタデータに保存できますが、リージョナルサンプラーではエラーになります。サンプラーには共通ネガティブを使用してください。ディテーラーは照合したキャラクターの個別ネガティブも使えます。サンプラーは2～100ステップ、Anima / SDXL の既定値は30です。ディテーラーのステップ数は個別に調整できます。他のモデル系統・ControlNet・attention パッチは未対応です。

NAI V4 形式のキャプションも読み込めますが、NAI の設定をローカル生成設定として適用することはできません。その場合は `use_image_settings` を無効にしてください。モデルは自動変更されません。

[English](README.md) · [検証記録](docs/validation.md) · [内部構造](docs/architecture.md)
