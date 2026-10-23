# RS MultiCharacter Sampler

ComfyUIでキャラクター別のプロンプト・LoRA・領域を設定して生成し、検出した人物を部分補正する拡張です。座標・枠・マスクで、それぞれの外見を適用する場所を誘導します。

[English](README.md) · [한국어](README.ko.md) · [ドキュメント](docs/README.md) · [変更履歴](CHANGELOG.md) · [リリース](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/releases) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md)

**現在のバージョン：[1.0.3 Hangeul](docs/release-1.0.3.md)。** ローカルモデルで動作し、RS NovelAI拡張やAPIキーは不要です。

![LoRAなしのAnima 2人生成例](examples/two-characters-result.png)

## 主な機能

- 共通の場面と人物別の文章を分け、**キャラクター・文字を合計10領域まで**設定します。
- 人物別LoRAを指定し、座標・枠・外部マスク・番号別のマスク描画で配置します。
- カラーOpenPose PNG・JSON・`POSE_KEYPOINT`から編集可能な人物マスクを作成します。
- 元の人物プロンプトと対応するLoRAを使い、検出領域を部分補正します。
- PNG/WebPに生成情報を保存し、画像ローダーから復元します。

座標やマスクはプロンプトの適用領域を誘導します。正確な人数・同一性・姿勢・綴りはモデルに依存します。[画像参照](docs/image-reference.md)も**実験的に対応していますが非推奨**です。対応するキャラクターLoRAがあれば優先してください。

## インストールと更新

ComfyUI-Managerで **RS MultiCharacter Sampler** を検索するか、[Comfy Registry](https://registry.comfy.org/publishers/raspie10032/nodes/comfyui-rs-multicharacter-sampler)からインストールします。パッケージIDは `comfyui-rs-multicharacter-sampler` です。

Gitの場合は **`ComfyUI/custom_nodes` 内で**実行します。

```sh
git clone https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler.git
```

更新はManager、または既存のGitインストール先で `git pull --ff-only` を使用します。導入・更新後は **ComfyUIを再起動し、ブラウザーを再読み込み**してください。同じ拡張を重複して配置しないでください。

Python **3.11以上**とTorch・NumPy・Pillowが必要です。ComfyUI本体が選択したモデルに標準対応している必要があります。拡散モデル・対応するテキストエンコーダー・VAEは別途用意してください。Load CLIPに `krea2` や `moss_image` がなければ、本体とPython環境を更新します。[互換性と検証バージョン](docs/compatibility.md)

追加機能には個別の準備が必要です。

| 機能 | 準備 |
| --- | --- |
| ローカルディテイラー | Managerで **ComfyUI-Impact-Pack**・**ComfyUI-Impact-Subpack** を導入し、ComfyUIのPythonで `requirements-detailer.txt` をインストールします。SAMは任意です。選択した検出・タグ付け用カタログモデルがない場合は実行時に取得します。 |
| 画像参照・実験的 | ComfyUIのPythonで `requirements-reference.txt` をインストールします。有効な参照での生成時に追加モデルを取得する場合があります。OFF・強度0では読み込みません。[方式と制限](docs/image-reference.md) |

## ワークフローから始める

[役割別Anima 2人ワークフロー](examples/modular/two-characters-anima.json)を読み込むか、下の表からモデルに合う例を選びます。UIでは通常のJSONを使用し、`-api.json` はAPIクライアント用です。[元のワークフローPNG](examples/two-characters-workflow.png)をキャンバスにドロップすることもできます。

1. ローダーで導入済みの **MODEL・CLIP・VAE** を選びます。Anima例のLoad CLIPタイプは `stable_diffusion` です。
2. STRING文章ノードを **RS Character Prompt** の番号別入力に接続し、各人物の外見・動作を書きます。場面・画風・総人数はサンプラーの共通プロンプト、除外内容は共通ネガティブに記入します。
3. **RS Character Position** で配置します。X/Yは0～1、左上が `(0, 0)` です。Prompt・LoRA・Positionの同じ番号が同じ人物を指します。
4. 組み立てノードを **RS Finalize Character Pipe** でまとめ、`character_pipe` 出力を **RS MultiCharacter Sampler** に接続します。LoRA・Positionは任意で、Finalizeまでの役割ノードは任意の順序にできます。
5. **モデル系統プリセット → プリセットを適用** を選び、解像度とモデル固有の設定を確認して実行します。プリセットはサンプリング・領域設定をコピーします。モデル・LoRA・文章・配置・解像度・シードは別途指定してください。

自動保存先は `output/RS_MultiCharacter/` です。PNG・可逆WebP・非可逆WebPに生成情報を保存します。編集用ワークフローも埋め込む場合は、ComfyUI標準の **Save Image** を使用してください。

[役割別入力ガイド](docs/modular-characters.md) · [プリセット値](docs/model-presets.md) · [Animaのサンプラー比較](docs/sampler-combinations.md)

## モデルと使用例

以下は各例の開始設定であり、全モデル・場面の品質を保証しません。FLUXは変種ごとのワークフローを使用してください。

| モデル系統 | ワークフロー | 開始設定・範囲 |
| --- | --- | --- |
| **Anima** | [2人の例](examples/modular/two-characters-anima.json) | 基本例。対応エンコーダーとQwen Image VAEを使用。既定ペアはEuler ancestral / SGM uniformです。 |
| **SDXL / Illustrious** | [2人の例](examples/two-characters-sdxl.json) · [人物LoRA](examples/character-lora/illustrious.json) | Load CheckpointからMODEL・CLIP・VAEを取得。基本例は30ステップ・CFG 5.5・Euler ancestral / normalです。[検証した派生モデルと制限](docs/sdxl-validation.md) |
| **FLUX.1 / 2 / 3** | [モデル別の例](examples/flux) | Dev・Schnell・Kleinを含みます。[検証した組み合わせ](docs/flux-validation.md) |
| **Krea 2 Turbo** | [2人の例](examples/two-characters-krea2.json) · [人物LoRA](examples/character-lora/krea2.json) | 8ステップ・CFG 1・Euler / simple。Qwen3-VL 4B（`krea2`）+ Qwen Image VAE。CFG 1では共通ネガティブは適用されません。 |
| **MOSS-Image SFT** | [基本](examples/two-characters-moss.json) · [8ステップLoRA](examples/moss-8step/two-cfg3.json) | 基本は50ステップ・CFG 3・Euler / simple。Qwen3.5 9B（`moss_image`）+ Flux2 VAE。[8ステップ設定](docs/moss-8step.md)には別の加速LoRAが必要です。 |
| **SD1.5・実験的・不安定** | [2人の例](examples/two-characters-sd15.json) | 実行は確認済みですが、人数・外見の分離は不安定です。[試験と制限](docs/sd15-validation.md) |

Krea 2・MOSSの領域生成は実験的対応です。MOSSは通常のComfyUI CFGを使用し、公式パイプラインのネガティブ分岐におけるレイヤー22のスキップは行いません。[モデルファイルと検証範囲](docs/krea-moss-validation.md)

## キャラクターLoRAとアダプター

**RS Character LoRA** で番号別のファイル・モデル強度・CLIP強度を選びます。サンプラー前の通常のComfyUI LoRAローダーは全体に適用されます。チェックポイントとアダプターのモデル構造・次元が一致する必要があります。

- **Precision** が既定です。LoRA設定ごとに独立した予測を計算し、対応する場合は小行列の最適化を使います。
- **Normal** は対応するAnima・SDXL線形LoRAのレイヤー計算を共有します。非対応のモデル・アダプターは理由を表示してPrecisionに切り替えます。モードにより人物の細部は変わる場合があります。
- **LoRA・LoCon/Tucker・DoRA・LoHa/DoHa・LoKr/DoKr・GLoRA・OFT/BOFT・IA³・形状が一致するdiff/setパッチ**に対応します。MOSS INT8・FP8のQ/K/V部分適用LoRAも処理します。複雑な形式は時間と一時メモリーを多く使う場合があります。

**GGUF:** 別途インストールした **ComfyUI-GGUF** ローダーのMODELを接続します。圧縮した重みを保持して人物別LoRAを適用します。FLUXはPrecisionを使い、Normalを選んでも自動で切り替わります。[導入方法と検証範囲](docs/gguf-compatibility.md)

**ネイティブ量子化:** 対応モデル系列のFP8・INT8圧縮重みを保持し、接続したローダーの演算で人物別LoRAを適用します。利用できるカーネルと画質は量子化モデル・ComfyUI・GPUによって異なります。[形式・検証範囲・制限](docs/quantization-compatibility.md)

**T-LoRA・GLoKr・その他の独自テンソル・レイヤー形状を変更するパッチは、このアダプター経路の対応範囲外です。** モデル・CLIPの制限と数値検証は[形式ガイド](docs/adapter-formats.md)を参照してください。[LoRA設定](docs/regional-lora.md) · [モード比較](docs/shared-lora-experiment.md) · [人物LoRAの検証組み合わせ](docs/character-lora-matrix-20261021.md)

## 配置・マスク・部分補正

**RS Character Position** で番号を選び、点・枠・マスクを移動・拡縮します。外部MASKは **RS Character Mask**、下絵に直接描く場合は **RS Character Mask Drawing** を使います。下絵は表示専用です。[マスクの使い方と例](docs/character-masks.md)

**人物2人 + 単語1つ**は3スロットを使い、2人を `character`・点、文字を `text`・枠に設定します。文字行のSTRINGには実際の単語を接続し、LoRAはNoneにします。物体には `character`・枠と物体の説明を使います。`layout_method=regional` を選び、MOSSネイティブ配置では全領域に枠が必要です。[混合配置例](examples/epsilon) · [物体例](examples/epsilon/objects) · [配置ガイド](docs/regional-layout.md)

**RS OpenPose Masks (Experimental)** は概略の人物マスクを生成します。骨格自体はモデルに入力しません。部位名による誘導は既定OFFでAnima・SDXLに対応します。**RS Character Interaction** の追加分離保持はAnima・SDXL・実験的SD1.5で重ならない領域に適用します。正確な関節や接触は保証しません。[入力・プレビュー・制限](docs/openpose-mask-guides.md) · [ポーズ例](examples/openpose)

部分補正は[生成 + ディテイラー例](examples/two-characters-detailer-anima.json)から始めてください。画像・人物パイプ・同じMODEL/CLIP/VAEを **RS MultiCharacter Detailer** に接続し、**RS Detection Combine Loader**・**RS Character Tagger Loader** を追加します。顔SEGM・WD ViT v3・denoise **0.25** が開始点です。タグ付けは元の人物文章を選択するために使い、推定タグを補正文章に追加しません。人物の割り当て報告を確認してください。[実行検証と制限](docs/detailer-validation.md)

## 画像から生成設定を復元

元のPNG/WebPを **RS MultiCharacter Load Image** で開き、人物パイプをサンプラーに接続します。画像の文章・人物情報が共通プロンプト欄を置き換えます。**use_image_settings** を有効にするとシード・解像度・サンプリング・領域設定も復元します。プリセットや現在のノード設定を使う場合は無効にします。

モデル・LoRA・CLIP・VAEは明示的に接続してください。メタデータから自動取得・読み込みは行いません。画像参照には元画像の再接続が必要です。これは文章とシードによる再生成で、マスクimg2imgはディテイラーが別途行います。NAI V4形式の人物キャプションは読み込めますが、NAIのサンプリング設定をローカルで再現する機能ではありません。[メタデータと復元範囲](docs/architecture.md)

## ノード一覧

現在 **15ノード**を登録します。表示名・選択案内・ヘルプはComfyUIの英語・韓国語・日本語・簡体字中国語・繁体字中国語設定に従います。

| ノード | 用途 |
| --- | --- |
| Character Prompt / LoRA / Position / Finalize Character Pipe | 番号別の設定を組み立て、最終パイプを作成します。 |
| Character Mask / Mask Drawing | 外部マスクの接続と番号別の描画。 |
| OpenPose Masks (Experimental) / Character Interaction | ポーズ由来の領域作成と重なり周辺の分離設定。 |
| Image Reference (Experimental · Not Recommended) | 人物番号に参照画像を関連付けます。 |
| MultiCharacter Sampler / Load Image | 生成と保存設定の復元。 |
| MultiCharacter Detailer / Detection Combine Loader / Character Tagger Loader | 人物の検出・照合・部分補正。 |
| MultiCharacter Prompts・旧形式 | 既存ワークフロー用の統合入力。新規作成には役割別ノードを使ってください。 |

## 制限とトラブルシューティング

- 実行ごとに画像1枚、入力は最大10スロットです。密な配置や交差する小物では人物の重複・欠落・属性混合・パネル分割が発生する場合があります。人物1人では画面全体を使うため、その点を動かしても人物の位置は固定できません。
- 領域サンプラーは共通ネガティブを使用します。人物別ネガティブと時間によって変化するテキスト条件は非対応です。
- SD2・インペイント/Refinerチェックポイント・FLUX Fill/Control・外部ControlNet/attentionパッチは領域サンプラーの対応範囲外です。任意の画像参照機能には別途、方式と制限があります。
- サンプラーは **2～100ステップ・CFG 1～20** に対応します。プリセットはモデルを自動識別せず、品質も保証しません。モデル別の例から始めてください。
- 復元には元の画像メタデータと同じアセット・互換環境が必要です。SNSなどでメタデータが削除される場合があります。自動保存は無関係なEXIF・GPS・カメラ情報を保持しません。
- 不具合は拡張・本体のバージョン、正確なチェックポイント・LoRAのバージョン、ワークフローJSONとエラー全文を添えて[報告](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/issues)してください。

[ドキュメントと検証の索引](docs/README.md)では実生成、アダプター数値試験、CPU・CI互換性検査を区別しています。

## 開発とライセンス

Torch・NumPy・Pillowを導入した環境で、リポジトリのルートから実行します。

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_ui.cjs
```

ネイティブ統合試験には `RS_MC_TEST_COMFYUI` にComfyUIのパスを指定します。全11種のJavaScript UI試験と本体・OSの組み合わせは[CI設定](.github/workflows/tests.yml)を参照してください。

GPL-3.0-only。[COPYING](COPYING) · [第三者に関する通知](THIRD_PARTY_NOTICES.md) · [ソースの系譜](docs/source-lineage.json)
