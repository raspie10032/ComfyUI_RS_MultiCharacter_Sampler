# RS MultiCharacter Sampler

**漸進解析度：**[RS 漸進解析度取樣器](docs/progressive-resolution.md)以最終寬高的0.5–1.0倍開始，使用Lanczos逐步放大，以部分細節換取大尺寸圖像的取樣速度。起始比例越低，細節損失和構圖變化可能越大，無法保證品質。實際速度取決於模型和設定。原有多角色取樣功能仍可使用。

用於 ComfyUI 的區域生成與本地細節修復。為每個角色提供獨立提示詞、可選 LoRA，以及點、矩形或遮罩，引導角色特徵在畫面中的分佈。

[English](README.md) · [한국어](README.ko.md) · [日本語](README.ja.md) · [简体中文](README.zh-CN.md) · **繁體中文** · [詳細文件](docs/README.md) · [更新記錄](CHANGELOG.md) · [釋出版本](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/releases)

**當前版本：[1.0.6 Hangeul](docs/release-1.0.6.md)。** 使用本地模型，無需安裝 RS NovelAI 擴充套件或提供 API 金鑰。

![未使用 LoRA 的 Anima 雙角色示例](examples/two-characters-result.png)

**相機視角：** [RS Camera Control](docs/camera-control.md) 向RS與NAI共用上下文加入視角標籤，可在節點內調整方向、高度、距離、隨機視角，還可選擇區域縮放、旋轉和平面透視變換。生成的三維姿態取決於模型。

**相機功能參考：** [Anima 相機標籤輔助](https://arca.live/b/aiart/179423561) / `ComfyUI-KR-Camera-Control`（原始署名：`ComfyUI_bsk_UI` / 灰暗x）。[參考範圍與來源說明](THIRD_PARTY_NOTICES.md#camera-control-references)。

## 主要功能

- 公共場景提示詞與獨立角色提示詞，最多 **10 個角色/文字區域**。
- 為各角色指定 LoRA，透過點、矩形、外部遮罩或按編號繪製的遮罩設定位置。
- 將彩色 OpenPose PNG、JSON 或 `POSE_KEYPOINT` 資料轉換為可編輯的人物遮罩。
- 檢測角色，使用對應的原始提示詞和 LoRA 進行區域性細節修復。
- 儲存 PNG/WebP 生成設定，並透過影像載入器恢復。

座標與遮罩只引導提示詞影響區域，不保證準確人數、身份、姿勢或文字拼寫。[角色影像參考](docs/image-reference.md) 為**實驗性支援，不推薦使用**；有合適的角色 LoRA 時優先使用 LoRA。


**Anima Role K/V · 實驗性：** 影像參考節點可選擇編號區域各自獨立的參考K/V。首次生成時自動下載約504 MiB專用轉接器，預設仍使用原有參考影格。[使用方法、限制與驗證](docs/anima-role-kv.md)。

**Anima 2B/2.9B參考影格：** 使用者自行選擇檢查點，採樣器自動準備符合模型的參考轉接器。品質與速度可能不同。獨立的Role K/V轉接器目前僅支援2B。[用法與限制](docs/anima-reference-frame.md)。

## 安裝與更新

在 ComfyUI-Manager 中搜尋 **RS MultiCharacter Sampler**，或檢視 [Comfy Registry 頁面](https://registry.comfy.org/publishers/raspie10032/nodes/comfyui-rs-multicharacter-sampler)。包 ID：`comfyui-rs-multicharacter-sampler`。

手動安裝時，在 **`ComfyUI/custom_nodes` 資料夾內**執行：

```sh
git clone https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler.git
```

透過 Manager 更新，或在已有 Git 安裝資料夾內執行 `git pull --ff-only`。安裝或更新後，**重啟 ComfyUI 並重新整理瀏覽器**。同一擴充套件只保留一個安裝副本。

需要 Python **3.11+**、Torch、NumPy 和 Pillow。ComfyUI 核心必須原生支援所選模型系列；擴散模型、匹配的文字編碼器和 VAE 需自行準備。如果 Load CLIP 缺少 `krea2` 或 `moss_image` 選項，請更新核心及執行環境。參閱[相容性與測試版本](docs/compatibility.md)。

在 ComfyUI 設定中將語言切換為 **中文**或**繁體中文**，即可顯示相應的節點名稱、輸入/輸出標籤、說明面板和懸停提示。滑鼠停留約 **2 秒**後顯示簡短說明。內部節點 ID、模型檔名及 `regional`、`moss_native` 等設定值保持原樣，已有工作流仍可使用。詳細專題文件目前主要為英文。

可選功能需另行配置：

| 功能 | 配置 |
| --- | --- |
| 本地細節修復 | 透過 Manager 安裝 **ComfyUI-Impact-Pack** 和 **ComfyUI-Impact-Subpack**，再用 ComfyUI 的 Python 安裝 `requirements-detailer.txt`。SAM 可選。執行時自動下載所選且缺失的檢測/標籤目錄模型。 |
| 影像參考 · 實驗性 | Anima 使用參考幀，Krea 2 使用 Identity Edit v2，FLUX 使用原生參考（FLUX.1 需要 Kontext）。SD1.5、SDXL、MOSS 保留現有方式。用 ComfyUI 的 Python 安裝 `requirements-reference.txt`。啟用參考可能下載額外模型；關閉或強度為 0 時不載入。[後端與限制](docs/image-reference.md) |

## 從示例工作流開始

載入[模組化 Anima 雙角色工作流](examples/modular/two-characters-anima.json)，或使用下方對應模型的示例。普通 JSON 用於介面匯入，檔名以 `-api.json` 結尾的檔案用於 API。也可將原始[工作流 PNG](examples/two-characters-workflow.png) 拖入畫布。

1. 在載入器中選擇已安裝的 **MODEL、CLIP、VAE**。Anima 示例的 Load CLIP 型別保持為 `stable_diffusion`。
2. 將 STRING 文字節點連線到 **RS 角色提示詞**，每行填寫對應角色的外觀和動作。公共場景、風格、總人數寫在取樣器的公共提示詞中，排除項寫在公共負向提示詞中。
3. 使用 **RS 角色位置**設定佈局。X/Y 為 0–1，左上角是 `(0, 0)`。提示詞、LoRA、位置節點的編號必須對應。
4. 將構建節點連線到 **RS 角色管線彙總**，再將 `character_pipe` 連線到 **RS 多角色取樣器**。LoRA 和位置可省略，彙總前各構建節點的連線順序不限。
5. 選擇**模型系列預設 → 套用預設**，確認解析度和模型相關設定後執行。預設只複製取樣/區域引數，模型、LoRA、提示詞、佈局、尺寸與種子需另行選擇。

自動儲存將結果寫入 `output/RS_MultiCharacter/`，支援 PNG、無損 WebP 和有損 WebP，並保留生成資訊。若需要在影像中嵌入可編輯工作流，請使用 ComfyUI 標準的 **Save Image** 節點。

[角色構建指南](docs/modular-characters.md) · [預設數值](docs/model-presets.md) · [Anima 取樣器/排程器比較](docs/sampler-combinations.md)

## 模型與示例

**RS NAI 互通：** 更新兩個擴充套件後，角色與上下文管線、偵測組合載入器及標籤器可相互連接。共用提示詞與座標，並在往返時保留本機遮罩、LoRA 和各後端的生成設定。[行為與限制](docs/shared-nai-context.md)。

下列配置是起點，並非通用的品質保證。FLUX 各變體有不同工作流與取樣要求。

| 模型系列 | 工作流 | 起始設定與範圍 |
| --- | --- | --- |
| **Anima** | [雙角色](examples/modular/two-characters-anima.json) | 主要示例；使用匹配的編碼器和 Qwen Image VAE。預設 Euler ancestral / SGM uniform。 |
| **SDXL / Illustrious** | [雙角色](examples/two-characters-sdxl.json) · [角色 LoRA](examples/character-lora/illustrious.json) | Load Checkpoint 提供 MODEL/CLIP/VAE。基礎示例：30 步、CFG 5.5、Euler ancestral / normal。[已測試衍生模型與限制](docs/sdxl-validation.md) |
| **FLUX.1 / 2 / 3** | [各模型工作流](examples/flux) | 包括 Dev、Schnell、Klein 等變體。[變體矩陣與驗證](docs/flux-validation.md) |
| **Krea 2 Turbo** | [雙角色](examples/two-characters-krea2.json) · [角色 LoRA](examples/character-lora/krea2.json) | 8 步、CFG 1、Euler / simple；Qwen3-VL 4B（`krea2`）+ Qwen Image VAE。CFG 1 時公共負向不生效。 |
| **MOSS-Image SFT** | [基礎](examples/two-characters-moss.json) · [8 步 LoRA](examples/moss-8step/two-cfg3.json) | 基礎：50 步、CFG 3、Euler / simple；Qwen3.5 9B（`moss_image`）+ Flux2 VAE。[8 步配置](docs/moss-8step.md) 需另接加速 LoRA。 |
| **SD1.5 · 實驗性，不穩定** | [雙角色](examples/two-characters-sd15.json) | 已驗證執行，人數和外觀分離不穩定。[試驗與限制](docs/sd15-validation.md) |

Krea 2 和 MOSS 的區域支援為實驗性。MOSS 使用 ComfyUI 普通 CFG，不包含官方管線中負向分支跳過第 22 層的邏輯。[模型檔案與驗證](docs/krea-moss-validation.md)

## 角色 LoRA 與介面卡

在 **RS 角色 LoRA** 中選擇各角色的檔案及模型/CLIP 強度。取樣器前連線標準 ComfyUI LoRA 載入器可應用全域性 LoRA。基礎模型、介面卡架構與維度必須匹配。

- **精確套用**為預設：每組 LoRA 設定獨立預測，受支援路徑使用低秩矩陣最佳化。
- **一般套用**：受支援的 Anima/SDXL 線性 LoRA 共享層計算。不支援的模型或介面卡自動使用精確模式，並說明原因。兩種模式的角色細節可能不同。
- 靜態介面卡支援 **LoRA、LoCon/Tucker、DoRA、LoHa/DoHa、LoKr/DoKr、GLoRA、OFT/BOFT、IA³ 及匹配的 diff/set 補丁**。打包 INT8/FP8 路徑包括 MOSS 的部分 Q/K/V LoRA。複雜介面卡可能增加耗時與臨時記憶體。

**GGUF：**連接另行安裝的 **ComfyUI-GGUF** 載入器的 MODEL 輸出。套用角色 LoRA 時保留壓縮權重。FLUX 使用精確模式，選擇一般模式也會自動切換。[安裝與已驗證範圍](docs/gguf-compatibility.md)

**原生量化：**在支援的模型系列中保留 FP8／INT8 壓縮權重，使用所連接載入器的運算套用角色 LoRA。可用核心與畫質取決於量化模型、ComfyUI 和 GPU。[格式、驗證範圍與限制](docs/quantization-compatibility.md)

**T-LoRA、GLoKr、其他自訂張量及改變形狀的補丁不在此介面卡路徑的支援範圍內。** 模型/CLIP 限制和數值檢查見[介面卡格式指南](docs/adapter-formats.md)。另見 [LoRA 配置](docs/regional-lora.md)、[模式比較](docs/shared-lora-experiment.md)和[角色 LoRA 測試矩陣](docs/character-lora-matrix-20261021.md)。

## 佈局、遮罩與區域性修復

在 **RS 角色位置**中拖動編號點、矩形或遮罩。外部 MASK 使用 **RS 角色遮罩**，也可透過 **RS 角色遮罩繪製**在僅供顯示的參考圖上塗畫。[遮罩指南與示例](docs/character-masks.md)

生成**兩個人和一個詞**時使用三個槽位：兩個 `character` 點區域與一個 `text` 矩形。將實際文字連線到文字行的 STRING，LoRA 保持 None。物體可使用 `character` 矩形槽位並填寫物體描述。區域控制使用 `layout_method=regional`；MOSS 原生布局的每個區域需為矩形或遮罩。**`moss_native` 會將最終遮罩轉換為外接矩形，不保留輪廓細節。** [混合佈局](examples/epsilon) · [物體示例](examples/epsilon/objects) · [佈局指南](docs/regional-layout.md)

**RS OpenPose 自動遮罩**從骨架構建大致的人物遮罩，不向模型輸入骨架本身。可選部位名稱引導預設關閉，支援 Anima/SDXL。**RS 角色重疊控制**可在 Anima/SDXL 和實驗性 SD1.5 中延後非重疊區域的分離衰減。均不保證準確關節與接觸。[姿勢輸入、預覽與限制](docs/openpose-mask-guides.md) · [姿勢示例](examples/openpose)

區域性修復可載入[生成＋細節修復工作流](examples/two-characters-detailer-anima.json)。向 **RS 多角色細節修復**連線影像、角色管線、相同 MODEL/CLIP/VAE，以及 **RS 檢測組合載入器**和 **RS 角色標籤模型載入器**。建議從面部 SEGM、WD ViT v3、重繪強度 **0.25** 開始。標籤模型只選擇原有角色提示詞，不追加推斷標籤。請檢查輸出的角色分配報告。[執行檢查與限制](docs/detailer-validation.md)

## 恢復生成設定

在 **RS 多角色影像載入器**中開啟原始 PNG/WebP，將其角色管線連線到取樣器。影像內提示詞和角色會覆蓋公共提示詞輸入。開啟 **use_image_settings** 可同時恢復種子、尺寸及取樣/區域引數；使用預設或當前控制元件時請關閉。

模型、LoRA、CLIP、VAE 需顯式連線；後設資料不會自動下載或載入檔案。參考圖需重新連線。這是基於文字與種子的重新生成；細節修復另行執行遮罩 img2img。可匯入 NAI V4 風格角色描述，但無法在本地復現其取樣設定。[後設資料與恢復範圍](docs/architecture.md)

## 節點一覽

共 **15 個節點**。介面標籤與說明支援英語、韓語、日語、簡體中文和繁體中文，並跟隨 ComfyUI 語言設定。

| 節點 | 用途 |
| --- | --- |
| RS 角色提示詞 / LoRA / 位置 / 管線彙總 | 按編號構建角色設定，輸出取樣器/細節修復管線。 |
| RS 角色遮罩 / 遮罩繪製 | 連線外部遮罩或按編號繪製。 |
| RS OpenPose 自動遮罩 / 角色重疊控制 | 建立姿勢遮罩並調節重疊區域分離。 |
| RS 角色影像參考（實驗性，不推薦） | 將參考圖關聯到角色編號。 |
| RS 多角色取樣器 / 影像載入器 | 生成影像並恢復儲存設定。 |
| RS 多角色細節修復 / 檢測組合載入器 / 角色標籤模型載入器 | 檢測、匹配和區域性修復角色。 |
| RS 多角色提示詞（舊版） | 保留以相容舊工作流，新工作流請使用模組化節點。 |

## 限制與排錯

- 每次生成一張，最多 10 個輸入槽位。密集佈局與交叉物體可能導致多餘/缺失人物、特徵混合或分鏡。只有一個角色時佔用全畫布，移動唯一的點不會移動人物。
- 區域取樣器使用公共負向提示詞，不支援單獨角色負向及按時間排程的文字條件。
- 區域取樣器不支援 SD2、專用 inpainting/refiner 檢查點、FLUX Fill/Control 或外部 ControlNet/注意力補丁。可選影像參考有獨立的後端與限制。
- 取樣器支援 **2–100 步、CFG 1–20**。預設不識別所連線的模型，也不保證品質。優先從對應模型工作流開始。
- 恢復需原始後設資料及匹配的檔案/環境。社交平臺可能剝離後設資料；自動儲存不保留無關 EXIF/GPS/相機資訊。
- 報錯時請在 [issue](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/issues) 中附上擴充套件/核心版本、準確的模型與 LoRA 版本、工作流 JSON 和完整 traceback。

[文件與驗證索引](docs/README.md) 分別記錄實際生成、介面卡數值及 CPU/CI 相容性檢查。

## 開發與許可證

安裝 Torch、NumPy、Pillow 後，在倉庫根目錄執行：

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_ui.cjs
```

原生整合測試可將 `RS_MC_TEST_COMFYUI` 設為 ComfyUI 原始碼目錄。[CI 配置](.github/workflows/tests.yml) 列出全部 JavaScript 介面測試及核心/系統矩陣。

GPL-3.0-only。參閱 [COPYING](COPYING)、[第三方宣告](THIRD_PARTY_NOTICES.md)及[原始碼來源](docs/source-lineage.json)。
