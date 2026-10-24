// SPDX-License-Identifier: GPL-3.0-only
// Simplified Chinese / Traditional Chinese (Taiwan) display text.
export const zhMessages = {
  "Metadata has {0} characters. Local nodes use 1–10; source data stays intact.": [
    "元数据含{0}个角色。本地节点使用第1–10个，原始数据会保留。",
    "後設資料含{0}個角色。本機節點使用第1–10個，原始資料會保留。"
  ],
  "Baseline: no extra separation. Delay and decrement values are inactive.": [
    "默认：不增加分离。延迟和递减值不生效。",
    "預設：不增加分離。延遲和遞減值不生效。"
  ],
  "Custom: use delay_steps and decrement below.": [
    "自定义：使用下方的延迟步数和递减值。",
    "自訂：使用下方的延遲步數和遞減值。"
  ],
  "delay3 / delay6: hold exclusive boundaries 3 / 6 extra steps; decay follows the sampler. Custom values are inactive.": [
    "delay3 / delay6：非重叠边界额外保持3 / 6步，递减幅度遵循采样器。不使用自定义值。",
    "delay3 / delay6：非重疊邊界額外保持3 / 6步，遞減幅度遵循取樣器。不使用自訂值。"
  ],
  "Only non-overlapping character regions are protected. Overlap/background keep their schedule. Extra separation supports Anima, SDXL and SD1.5; it does not lock poses.": [
    "只额外保护非重叠的角色区域，重叠和背景保持原有调度。额外分离支持Anima、SDXL和SD1.5，不锁定姿势。",
    "只額外保護非重疊的角色區域，重疊和背景保持原有排程。額外分離支援Anima、SDXL和SD1.5，不鎖定姿勢。"
  ],
  "Autosave OFF: connect an image save node to keep the result.": [
    "自动保存已关闭：请连接图像保存节点以保留结果。",
    "自動儲存已關閉：請連線影像儲存節點以保留結果。"
  ],
  "Autosave: {0}. Keeps generation metadata, without a workflow.": [
    "自动保存：{0}。保留生成元数据，不包含工作流。",
    "自動儲存：{0}。保留生成後設資料，不包含工作流。"
  ],
  "Lossy WebP changes pixels; quality controls compression, not generation.": [
    "有损 WebP 会改变像素；质量值控制保存压缩，不影响生成。",
    "有損 WebP 會改變畫素；品質值控制儲存壓縮，不影響生成。"
  ],
  "Experimental support · NOT RECOMMENDED": [
    "实验性支持 · 不推荐",
    "實驗性支援 · 不推薦"
  ],
  "Character {0} · {1}px · strength {2}": [
    "角色 {0} · {1}px · 强度 {2}",
    "角色 {0} · {1}px · 強度 {2}"
  ],
  "Reuses its point/box/mask. Prefer a character LoRA; reference fidelity varies. OFF or strength 0 skips reference models.": [
    "沿用此编号的点、矩形或遮罩。还原程度不稳定，推荐角色 LoRA。关闭或强度为 0 时不加载参考模型。",
    "沿用此編號的點、矩形或遮罩。還原程度不穩定，推薦角色 LoRA。關閉或強度為 0 時不載入參考模型。"
  ],
  "Sampler only. Saved metadata records settings, not reference images.": [
    "仅适用于采样器。元数据只记录设置，不保存参考图。",
    "僅適用於取樣器。後設資料只記錄設定，不儲存參考圖。"
  ],
  "Mask drawing · choose a number, then paint": [
    "遮罩绘制 · 选择编号后绘制",
    "遮罩繪製 · 選擇編號後繪製"
  ],
  "The reference stays behind the masks. Each number uses the same Prompt/LoRA slot, regardless of the person shown.": [
    "在底图上按编号绘制。每个编号使用对应提示词和 LoRA，与底图中的人物身份无关。",
    "在底圖上按編號繪製。每個編號使用對應提示詞和 LoRA，與底圖中的人物身份無關。"
  ],
  "Paint, erase, undo, move and resize one layer at a time. Blank layers fall back to XY/boxes. This node replaces earlier masks; add individual masks after it to override.": [
    "可绘制、擦除、撤销、移动和缩放各图层。空白图层使用坐标或矩形。本节点替换前面的遮罩；后接单独遮罩可覆盖。",
    "可繪製、擦除、撤銷、移動和縮放各圖層。空白圖層使用座標或矩形。本節點替換前面的遮罩；後接單獨遮罩可覆蓋。"
  ],
  "Only masks enter generation. Canvas overflow is clipped; pose is approximate. The colored preview includes margin. Text needs a box. MOSS native converts masks to enclosing boxes; mask shapes are lost.": [
    "仅遮罩参与生成。超出画布的部分会裁剪，姿势只作大致引导。彩色预览含留白。文字需用矩形；MOSS 原生模式将遮罩转为外接矩形，不保留形状。",
    "僅遮罩參與生成。超出畫布的部分會裁剪，姿勢只作大致引導。彩色預覽含留白。文字需用矩形；MOSS 原生模式將遮罩轉為外接矩形，不保留形狀。"
  ],
  "Character mask · white selects the region": [
    "角色遮罩 · 白色为应用区域",
    "角色遮罩 · 白色為應用區域"
  ],
  "Overrides this character's XY/box in any builder order. Off restores them.": [
    "替代此编号的坐标或矩形，连接顺序不限。关闭后恢复。",
    "替代此編號的座標或矩形，連線順序不限。關閉後恢復。"
  ],
  "Use one full-canvas mask per character; overlaps share captions. Margin uses source pixels.": [
    "每个角色使用一张全画布遮罩。重叠处共享提示词；留白以原图像素计。",
    "每個角色使用一張全畫布遮罩。重疊處共享提示詞；留白以原影像素計。"
  ],
  "Size ×{0}; shift X {1}, Y {2}. Outside the canvas is clipped.": [
    "缩放 ×{0}；偏移 X {1}、Y {2}。超出画布的部分会裁剪。",
    "縮放 ×{0}；偏移 X {1}、Y {2}。超出畫布的部分會裁剪。"
  ],
  "Guides prompt attention, not exact pose. MOSS native converts masks to enclosing boxes; mask shapes are lost.": [
    "引导提示词影响区域，不能锁定姿势。MOSS 原生模式将遮罩转为外接矩形，不保留形状。",
    "引導提示詞影響區域，不能鎖定姿勢。MOSS 原生模式將遮罩轉為外接矩形，不保留形狀。"
  ],
  "Prompt slots · shared STRING input": [
    "提示词槽位 · 共用 STRING 输入",
    "提示詞槽位 · 共用 STRING 輸入"
  ],
  "Character: {0} / Text: {1}": [
    "角色：{0} / 文字：{1}",
    "角色：{0} / 文字：{1}"
  ],
  "Character uses STRING as its positive prompt; Text uses it as the words to draw. Switching kind keeps the connection.": [
    "角色将 STRING 用作正向提示词，文字将其用作实际绘制内容。切换类型保留连接。",
    "角色將 STRING 用作正向提示詞，文字將其用作實際繪製內容。切換型別保留連線。"
  ],
  "Text needs a box in Position. Remove text from the common negative. Short words work better; spelling is not guaranteed.": [
    "文字需在位置节点中设为矩形。移除公共负向中的 text。短词更容易生成，但不保证拼写正确。",
    "文字需在位置節點中設為矩形。移除公共負向中的 text。短詞更容易生成，但不保證拼寫正確。"
  ],
  "This node sets the active count. Disabled and out-of-count slots are excluded. Use the sampler for the common negative.": [
    "本节点决定有效数量；禁用或超出数量的槽位不参与生成。公共负向提示词在采样器中填写。",
    "本節點決定有效數量；禁用或超出數量的槽位不參與生成。公共負向提示詞在取樣器中填寫。"
  ],
  "Position · points, boxes and masks": [
    "位置 · 点、矩形与遮罩",
    "位置 · 點、矩形與遮罩"
  ],
  "Select a numbered region above the layout before dragging. Corner/−/+ resizes boxes and masks; mask scaling keeps its shape and number. Undo/reset restores placement.": [
    "在布局上方选编号后拖动。角点或 −/+ 可缩放矩形与遮罩，保留形状和编号。可撤销或重置位置。",
    "在佈局上方選編號後拖動。角點或 −/+ 可縮放矩形與遮罩，保留形狀和編號。可撤銷或重置位置。"
  ],
  "Rows: {0}; boxes: {1}. X/Y are normalized 0–1; (0,0) is top left.": [
    "显示 {0} 行；矩形编号：{1}。X/Y 为 0–1，左上角为 (0,0)。",
    "顯示 {0} 行；矩形編號：{1}。X/Y 為 0–1，左上角為 (0,0)。"
  ],
  "Point partitions use the nearest XY. Coincident points spread left to right by number. Box uses center XY and width/height; boxes take priority over points.": [
    "点按最近坐标分区；相同坐标按编号从左到右分布。矩形使用中心坐标与宽高，优先于点区域。",
    "點按最近座標分割槽；相同座標按編號從左到右分佈。矩形使用中心座標與寬高，優先於點區域。"
  ],
  "Text requires a box. Match numbers with Prompt/LoRA. The diagram guides prompt regions; it does not guarantee body positions.": [
    "文字必须使用矩形。编号需与提示词和 LoRA 对应。布局只引导提示词区域，不保证人物位置。",
    "文字必須使用矩形。編號需與提示詞和 LoRA 對應。佈局只引導提示詞區域，不保證人物位置。"
  ],
  "Finalize · connect to Sampler / Detailer": [
    "汇总管线 · 连接采样器或细节修复",
    "彙總管線 · 連線取樣器或細節修復"
  ],
  "Prompt, LoRA and Position merge by slot number in any order. Prompt determines count; missing LoRA/Position default to None/center.": [
    "提示词、LoRA 和位置按编号汇总，顺序不限。提示词决定数量；省略的 LoRA/位置默认为 None/中心。",
    "提示詞、LoRA 和位置按編號彙總，順序不限。提示詞決定數量；省略的 LoRA/位置預設為 None/中心。"
  ],
  "Up to 10 character/text slots. Missing prompts are reported at execution. More processed regions do not guarantee quality.": [
    "角色与文字合计最多 10 个槽位。运行时提示缺失的提示词。处理区域越多，越难保证质量。",
    "角色與文字合計最多 10 個槽位。執行時提示缺失的提示詞。處理區域越多，越難保證品質。"
  ],
  "Sampling · current selections": [
    "采样 · 当前设置说明",
    "取樣 · 當前設定說明"
  ],
  "Image settings ON: the image pipe supplies dimensions, seed and sampling/routing settings as well as prompts. Select MODEL/CLIP/VAE and global LoRAs manually.": [
    "图像设置恢复已开启：从图像管线读取提示词、尺寸、种子及采样/区域设置。MODEL/CLIP/VAE 和全局 LoRA 需手动连接。",
    "影像設定恢復已開啟：從影像管線讀取提示詞、尺寸、種子及取樣/區域設定。MODEL/CLIP/VAE 和全域性 LoRA 需手動連線。"
  ],
  "Image settings OFF: use this node's sampling controls. An image-loaded pipe still supplies its prompts and characters.": [
    "图像设置恢复已关闭：使用当前采样设置；图像管线仍提供提示词和角色。",
    "影像設定恢復已關閉：使用當前取樣設定；影像管線仍提供提示詞和角色。"
  ],
  "MOSS native: requires MOSS and box or mask regions. Regional strengths, boundary and feather controls are ignored.": [
    "MOSS 原生模式需要 MOSS 模型及矩形或遮罩区域。区域强度、边界和羽化设置不生效。",
    "MOSS 原生模式需要 MOSS 模型及矩形或遮罩區域。區域強度、邊界和羽化設定不生效。"
  ],
  "Masks become enclosing rectangles after placement; their detailed shapes are not preserved.": [
    "遮罩按最终位置转为外接矩形，不保留轮廓细节。",
    "遮罩按最終位置轉為外接矩形，不保留輪廓細節。"
  ],
  "Regional: controls prompt influence by region. Normal/Precision LoRA mode comes from the pipe. Presets apply only when you press Apply.": [
    "区域模式按区域控制提示词。普通/精确 LoRA 模式由管线传入；预设需点击应用后生效。",
    "區域模式按區域控制提示詞。普通/精確 LoRA 模式由管線傳入；預設需點選應用後生效。"
  ],
  "Sampling pair: {0} / {1}. Changing one does not reset the other.": [
    "采样组合：{0} / {1}。修改其中一项不会重置另一项。",
    "取樣組合：{0} / {1}。修改其中一項不會重置另一項。"
  ],
  "Image load · restore the character pipe": [
    "加载图像 · 恢复角色管线",
    "載入影像 · 恢復角色管線"
  ],
  "Reads supported PNG/WebP character metadata, including per-slot LoRAs and Normal/Precision mode. Use the generation info output to check what was restored.": [
    "读取受支持 PNG/WebP 的角色元数据，包括各槽 LoRA 和普通/精确模式。请查看生成信息输出确认恢复内容。",
    "讀取受支援 PNG/WebP 的角色後設資料，包括各槽 LoRA 和普通/精確模式。請檢視生成資訊輸出確認恢復內容。"
  ],
  "Files are not embedded: base model and global LoRAs must be connected manually. Missing character LoRAs cause an error at sampling. Enable sampler use_image_settings to restore sampling too.": [
    "不包含模型文件：基础模型与全局 LoRA 需手动连接。缺少角色 LoRA 会在采样时报错。启用 use_image_settings 可同时恢复采样设置。",
    "不包含模型檔案：基礎模型與全域性 LoRA 需手動連線。缺少角色 LoRA 會在取樣時報錯。啟用 use_image_settings 可同時恢復取樣設定。"
  ],
  "Detailer · one matched character per crop": [
    "细节修复 · 按匹配角色逐块修复",
    "細節修復 · 按匹配角色逐塊修復"
  ],
  "Connect the image and pipe, matching MODEL/CLIP/VAE, and detectors. Multiple characters require a tagger. Uncertain matches are skipped; text slots are excluded.": [
    "连接图像、角色管线、对应 MODEL/CLIP/VAE 及检测模型。多角色需要标签模型。跳过不明确的匹配，文字槽位不参与修复。",
    "連線影像、角色管線、對應 MODEL/CLIP/VAE 及檢測模型。多角色需要標籤模型。跳過不明確的匹配，文字槽位不參與修復。"
  ],
  "Each matched crop uses its character prompt and LoRA in Precision. Higher denoise permits larger changes. max_regions limits edits, not character count.": [
    "每个匹配区域使用对应提示词和精确 LoRA。重绘强度越高，变化越大。max_regions 限制修复区域数，并非角色数。",
    "每個匹配區域使用對應提示詞和精確 LoRA。重繪強度越高，變化越大。max_regions 限制修復區域數，並非角色數。"
  ],
  "Advanced controls are visible: mask repair and matching thresholds affect which areas change.": [
    "高级设置已展开：遮罩修复和匹配阈值影响修复区域。",
    "高階設定已展開：遮罩修復和匹配閾值影響修復區域。"
  ],
  "Advanced controls are folded; their saved values still apply.": [
    "高级设置已折叠，已保存的值仍然生效。",
    "高階設定已摺疊，已儲存的值仍然生效。"
  ],
  "Tagger · character matching only": [
    "标签模型 · 仅用于角色匹配",
    "標籤模型 · 僅用於角色匹配"
  ],
  "Selected model: {0}. Downloads only the selected model at execution and reuses cached files.": [
    "所选模型：{0}。执行时仅下载所选模型，已下载文件使用缓存。",
    "所選模型：{0}。執行時僅下載所選模型，已下載檔案使用快取。"
  ],
  "batch_size is the number of crops inferred together, not character count. Lower it if memory is tight. Tag scores choose your original prompt; tags never enter it.": [
    "batch_size 是同时推理的裁剪数量，并非角色数。内存不足时请调低。分数用于选择原提示词，不会追加标签。",
    "batch_size 是同時推理的裁剪數量，並非角色數。記憶體不足時請調低。分數用於選擇原提示詞，不會追加標籤。"
  ],
  "CPU selected: runs tagging on CPU.": [
    "已选择 CPU：标签推理在 CPU 上运行。",
    "已選擇 CPU：標籤推理在 CPU 上執行。"
  ],
  "Auto device: follows ComfyUI's execution device; falls back to CUDA/CPU if ComfyUI management is unavailable.": [
    "自动设备：跟随 ComfyUI 执行设备；设备管理不可用时选择 CUDA/CPU。",
    "自動裝置：跟隨 ComfyUI 執行裝置；裝置管理不可用時選擇 CUDA/CPU。"
  ],
  "This selection needs additional tagger dependencies and more memory; start with batch_size=1.": [
    "此模型需要额外依赖和更多内存，请从 batch_size=1 开始。",
    "此模型需要額外依賴和更多記憶體，請從 batch_size=1 開始。"
  ],
  "Legacy prompt node · workflow compatibility": [
    "旧版提示词节点 · 兼容已有工作流",
    "舊版提示詞節點 · 相容已有工作流"
  ],
  "New workflows can use Prompt → LoRA → Position → Finalize in any role order. This legacy node stays available for existing graphs.": [
    "新工作流请将提示词、LoRA、位置按任意顺序连接后汇总。本旧版节点保留用于兼容已有工作流。",
    "新工作流請將提示詞、LoRA、位置按任意順序連線後彙總。本舊版節點保留用於相容已有工作流。"
  ],
  "Layout: {0}. Text requires boxes/mixed and the literal-text field. Per-character negatives are unsupported; use the common negative.": [
    "布局：{0}。文字需使用 boxes/mixed 及实际文字输入。不支持单独角色负向，请使用公共负向。",
    "佈局：{0}。文字需使用 boxes/mixed 及實際文字輸入。不支援單獨角色負向，請使用公共負向。"
  ],
  "Connected control values are resolved at execution; this panel describes local widget selections.": [
    "连接的设置值在执行时确定；此面板说明当前节点中的选择。",
    "連線的設定值在執行時確定；此面板說明當前節點中的選擇。"
  ],
  "Layout guide · XY 0–1": [
    "布局预览 · XY 0–1",
    "佈局預覽 · XY 0–1"
  ],
  "By number · composition is approximate": [
    "按编号设置 · 构图仅作参考",
    "按編號設定 · 構圖僅作參考"
  ],
  "Linked values: layout resolved at execution": [
    "已连接输入：执行时确定布局",
    "已連線輸入：執行時確定佈局"
  ],
  "Prompt connection missing: ": [
    "提示词尚未连接：",
    "提示詞尚未連線："
  ],
  "Mask guide · overflow is clipped": [
    "遮罩预览 · 超出画布会裁剪",
    "遮罩預覽 · 超出畫布會裁剪"
  ],
  "Connect/run mask nodes: ": [
    "请连接或运行遮罩节点：",
    "請連線或執行遮罩節點："
  ],
  "Normal · Fast layer sharing": [
    "普通应用 · 共享计算",
    "一般套用 · 共享計算"
  ],
  "Supported Anima/SDXL linear LoRAs share layer calculations. Details can differ from Precision.": [
    "受支持的 Anima/SDXL 线性 LoRA 共享层计算，细节可能与精确模式不同。",
    "受支援的 Anima/SDXL 線性 LoRA 共享層計算，細節可能與精確模式不同。"
  ],
  "Unsupported models/adapters use Precision and report the reason in generation info.": [
    "不支持的模型或适配器使用精确模式，并在生成信息中说明原因。",
    "不支援的模型或介面卡使用精確模式，並在生成資訊中說明原因。"
  ],
  "Applies to every character slot. Detailer corrects one character at a time using Precision in both modes.": [
    "应用到全部角色槽位。细节修复在两种模式下均逐角色使用精确方式。",
    "應用到全部角色槽位。細節修復在兩種模式下均逐角色使用精確方式。"
  ],
  "Precision · Independent character predictions": [
    "精确应用 · 按角色独立预测",
    "精確套用 · 按角色獨立預測"
  ],
  "Each LoRA setting gets separate model predictions. Supported LoRAs use low-rank optimization.": [
    "每组 LoRA 设置独立预测，受支持的 LoRA 使用低秩矩阵优化。",
    "每組 LoRA 設定獨立預測，受支援的 LoRA 使用低秩矩陣最佳化。"
  ],
  "More distinct LoRA settings take longer than Normal. This does not guarantee better artwork or complete separation.": [
    "不同 LoRA 设置越多，越慢于普通模式。不保证更好的画质或完全分离。",
    "不同 LoRA 設定越多，越慢於普通模式。不保證更好的畫質或完全分離。"
  ],
  "Compatibility default for existing workflows. Applies to every character slot; Detailer uses this method too.": [
    "已有工作流默认方式，应用到全部角色槽位；细节修复也使用此方式。",
    "已有工作流預設方式，應用到全部角色槽位；細節修復也使用此方式。"
  ],
  "Reference image": [
    "打开参考图",
    "開啟參考圖"
  ],
  "Hide reference": [
    "隐藏参考图",
    "隱藏參考圖"
  ],
  "Undo": [
    "撤销",
    "撤銷"
  ],
  "Clear layer": [
    "清空当前图层",
    "清空當前圖層"
  ],
  "Paint": [
    "绘制",
    "繪製"
  ],
  "Erase": [
    "擦除",
    "擦除"
  ],
  "Move": [
    "移动",
    "移動"
  ],
  "Brush ": [
    "画笔",
    "畫筆"
  ],
  "Size ×": [
    "缩放 ×",
    "縮放 ×"
  ],
  "Selected layer only; overflow is clipped.": [
    "仅调整所选图层；超出画布会裁剪。",
    "僅調整所選圖層；超出畫布會裁剪。"
  ],
  "Character mask drawing": [
    "角色遮罩绘制",
    "角色遮罩繪製"
  ],
  "Select a character number, then paint its region. Reference only; masks guide placement, not exact pose. Blank layers use XY/boxes. Canvas overflow is clipped.": [
    "选择角色编号后绘制区域。底图仅供参考；遮罩引导位置，不锁定姿势。空白图层使用坐标或矩形，超出画布会裁剪。",
    "選擇角色編號後繪製區域。底圖僅供參考；遮罩引導位置，不鎖定姿勢。空白圖層使用座標或矩形，超出畫布會裁剪。"
  ],
  "Too many strokes: undo and simplify.": [
    "笔画过多，请撤销并简化。",
    "筆畫過多，請撤銷並簡化。"
  ],
  "Reference missing; painted masks are still saved.": [
    "参考图缺失，已绘制遮罩仍保留。",
    "參考圖缺失，已繪製遮罩仍保留。"
  ],
  "Character {0} · {1}×{2} · colored regions include margin": [
    "角色 {0} · {1}×{2} · 彩色区域含留白",
    "角色 {0} · {1}×{2} · 彩色區域含留白"
  ],
  "Loading reference…": [
    "正在加载参考图…",
    "正在載入參考圖…"
  ],
  "Reference load failed: ": [
    "参考图加载失败：",
    "參考圖載入失敗："
  ],
  "Invalid drawing data. Restore a valid workflow.": [
    "绘制数据无效，请恢复有效的工作流。",
    "繪製資料無效，請恢復有效的工作流。"
  ],
  "Edit region": [
    "选择编辑区域",
    "選擇編輯區域"
  ],
  "Regional layout": [
    "区域布局",
    "區域佈局"
  ],
  "Reset selected": [
    "重置所选位置",
    "重置所選位置"
  ],
  "Shrink selected": [
    "缩小所选区域",
    "縮小所選區域"
  ],
  "Enlarge selected": [
    "放大所选区域",
    "放大所選區域"
  ],
  "Mask": [
    "遮罩",
    "遮罩"
  ],
  "Box": [
    "矩形",
    "矩形"
  ],
  "Point": [
    "点",
    "點"
  ],
  " · Text": [
    " · 文字",
    " · 文字"
  ],
  "Linked or unready values: edit the source or run the mask first.": [
    "存在连接值或尚未就绪的遮罩，请修改来源或先运行遮罩节点。",
    "存在連線值或尚未就緒的遮罩，請修改來源或先執行遮罩節點。"
  ],
  "Select a number above, then drag. Corner/−/+ resizes boxes and masks. Mask overflow is clipped; layout is approximate.": [
    "在上方选择编号后拖动。角点或 −/+ 缩放矩形与遮罩。超出画布会裁剪，布局仅作大致引导。",
    "在上方選擇編號後拖動。角點或 −/+ 縮放矩形與遮罩。超出畫布會裁剪，佈局僅作大致引導。"
  ],
  "Mask is outside the canvas. Move it back, enlarge it, or reset placement.": [
    "遮罩位于画布外，请移回、放大或重置位置。",
    "遮罩位於畫布外，請移回、放大或重置位置。"
  ],
  "Run once to preview connected pose inputs.": [
    "运行一次以预览已连接的姿势输入。",
    "執行一次以預覽已連線的姿勢輸入。"
  ],
  "People: ": [
    "人数：",
    "人數："
  ],
  "PNG · numbered left to right. Check overlapping joints.": [
    "PNG · 从左到右编号，请检查重叠关节。",
    "PNG · 從左到右編號，請檢查重疊關節。"
  ],
  "Canvas overflow is clipped.": [
    "裁剪超出画布的部分。",
    "裁剪超出畫布的部分。"
  ],
  "Load or drop a colored pose PNG to create masks.": [
    "打开或拖入彩色骨架 PNG 以创建遮罩。",
    "開啟或拖入彩色骨架 PNG 以建立遮罩。"
  ],
  "Load Pose PNG": [
    "打开骨架 PNG",
    "開啟骨架 PNG"
  ],
  "Reading pose PNG…": [
    "正在读取骨架 PNG…",
    "正在讀取骨架 PNG…"
  ],
  "Load JSON (advanced)": [
    "打开 JSON（高级）",
    "開啟 JSON（高階）"
  ],
  "Show / hide JSON": [
    "展开 / 折叠 JSON",
    "展開 / 摺疊 JSON"
  ],
  "SEGM model": [
    "SEGM 模型",
    "SEGM 模型"
  ],
  "BBOX model": [
    "BBOX 模型",
    "BBOX 模型"
  ],
  "SAM model": [
    "SAM 模型",
    "SAM 模型"
  ],
  "Next run": [
    "下次运行方式",
    "下次執行方式"
  ],
  "SEGM only. BBOX / SAM are skipped.": [
    "仅使用 SEGM，跳过 BBOX 和 SAM。",
    "僅使用 SEGM，跳過 BBOX 和 SAM。"
  ],
  "BBOX + SAM masks.": [
    "用 BBOX 检测，并用 SAM 创建遮罩。",
    "用 BBOX 檢測，並用 SAM 建立遮罩。"
  ],
  "BBOX rectangles (SAM OFF).": [
    "使用 BBOX 矩形（SAM 关闭）。",
    "使用 BBOX 矩形（SAM 關閉）。"
  ],
  "Select SEGM or BBOX. SAM alone cannot detect regions.": [
    "请选择 SEGM 或 BBOX；SAM 无法单独检测区域。",
    "請選擇 SEGM 或 BBOX；SAM 無法單獨檢測區域。"
  ],
  "Connected model inputs are resolved when the workflow runs.": [
    "已连接的模型输入在执行时确定。",
    "已連線的模型輸入在執行時確定。"
  ],
  "Model family preset": [
    "模型系列预设",
    "模型系列預設"
  ],
  "Choose a preset": [
    "选择预设",
    "選擇預設"
  ],
  "Apply preset": [
    "应用预设",
    "套用預設"
  ],
  "Preset guidance": [
    "预设说明",
    "預設說明"
  ],
  "Choose a starting point, then Apply preset. Sampling and regional controls remain editable.": [
    "选择起始配置后点击应用预设，之后仍可手动调整采样和区域参数。",
    "選擇起始配置後點選套用預設，之後仍可手動調整取樣和區域引數。"
  ],
  "Selected; press Apply preset to copy the values.": [
    "已选择，点击应用预设以载入数值。",
    "已選擇，點選套用預設以載入數值。"
  ],
  "Current controls match this preset.": [
    "当前设置与此预设一致。",
    "當前設定與此預設一致。"
  ],
  "Current controls differ from this preset. Your manual settings will be used.": [
    "当前设置与预设不同，将使用手动设置。",
    "當前設定與預設不同，將使用手動設定。"
  ],
  "Turn off use_image_settings first. Image settings take priority over these controls.": [
    "请先关闭 use_image_settings；图像恢复设置会优先应用。",
    "請先關閉 use_image_settings；影像恢復設定會優先應用。"
  ],
  "Choose regional layout first. These presets tune regional sampling, not MOSS native layout.": [
    "请先切换到 regional；此预设用于区域采样，不适用于 MOSS 原生布局。",
    "請先切換到 regional；此預設用於區域取樣，不適用於 MOSS 原生布局。"
  ],
  "Disconnect or convert these inputs back to widgets before applying: ": [
    "应用前请断开以下输入或转回控件：",
    "應用前請斷開以下輸入或轉回控制元件："
  ],
  "This installation cannot apply the preset. Unavailable control or value: ": [
    "当前环境无法应用此预设，缺少控件或值：",
    "當前環境無法應用此預設，缺少控制元件或值："
  ],
  "No values were changed.": [
    "未更改设置。",
    "未更改設定。"
  ],
  "Saved mask placement. Select a numbered region above the layout to move or resize it.": [
    "保存的遮罩位置。请在布局上方选择编号以移动或缩放。",
    "儲存的遮罩位置。請在佈局上方選擇編號以移動或縮放。"
  ],
  "Select a character number and paint over the reference. The image is a guide only; numbered masks are saved in the workflow.": [
    "选择编号，在底图上绘制。底图仅供参考，编号遮罩保存在工作流中。",
    "選擇編號，在底圖上繪製。底圖僅供參考，編號遮罩儲存在工作流中。"
  ],
  "Character Prompt row number. Attach one mask to each character you want to shape.": [
    "对应提示词行编号。每个需要指定形状的角色连接一张遮罩。",
    "對應提示詞行編號。每個需要指定形狀的角色連線一張遮罩。"
  ],
  "Off clears this character's mask and restores its XY/box; other characters keep their masks.": [
    "关闭后清除此编号的遮罩，恢复坐标或矩形。其他角色不变。",
    "關閉後清除此編號的遮罩，恢復座標或矩形。其他角色不變。"
  ],
  "Expand white by this many source pixels. Leave space for hair, clothing and contact.": [
    "按原图像素扩张白色区域，为头发、衣物和接触留出空间。",
    "按原影像素擴張白色區域，為頭髮、衣物和接觸留出空間。"
  ],
  "Pixels above this value select the character region. Gray is converted to black or white.": [
    "亮于此值的像素作为角色区域，灰度转为黑白。",
    "亮於此值的畫素作為角色區域，灰度轉為黑白。"
  ],
  "One full-canvas MASK: white selects the region. Shift/scale overflow is clipped; pose remains approximate.": [
    "一张全画布 MASK，白色为区域。移动或缩放后裁剪超出部分；姿势仅作引导。",
    "一張全畫布 MASK，白色為區域。移動或縮放後裁剪超出部分；姿勢僅作引導。"
  ],
  "Shift by a fraction of canvas width: +0.1 moves right 10%. Overflow is clipped.": [
    "相对画布宽度偏移，+0.1 向右移动 10%。超出部分会裁剪。",
    "相對畫布寬度偏移，+0.1 向右移動 10%。超出部分會裁剪。"
  ],
  "Shift by a fraction of canvas height: +0.1 moves down 10%. Overflow is clipped.": [
    "相对画布高度偏移，+0.1 向下移动 10%。超出部分会裁剪。",
    "相對畫布高度偏移，+0.1 向下移動 10%。超出部分會裁剪。"
  ],
  "Uniform size about the canvas centre: 0.5 half, 1 original, 2 double. Overflow is clipped.": [
    "以画布中心等比缩放：0.5 为一半，1 为原始，2 为两倍。超出部分会裁剪。",
    "以畫布中心等比縮放：0.5 為一半，1 為原始，2 為兩倍。超出部分會裁剪。"
  ],
  "Active slots (1–10), including text. Prompt excludes slots above this count; match numbers across role nodes.": [
    "有效槽位数 1–10，包含文字。提示词节点排除超出此数量的编号，各节点编号应一致。",
    "有效槽位數 1–10，包含文字。提示詞節點排除超出此數量的編號，各節點編號應一致。"
  ],
  "Enable this numbered slot. Disabled slots are excluded from generation.": [
    "是否使用此编号。关闭的槽位不参与生成。",
    "是否使用此編號。關閉的槽位不參與生成。"
  ],
  "Character uses the STRING as a prompt; Text uses it as literal lettering. Text needs box geometry.": [
    "同一 STRING 作为角色提示词或实际文字。文字需在位置节点中选矩形。",
    "同一 STRING 作為角色提示詞或實際文字。文字需在位置節點中選矩形。"
  ],
  "Connect the positive prompt STRING, or exact lettering for a text slot. Put shared scene/style instructions in the sampler.": [
    "连接正向提示词 STRING；文字槽位连接实际文字。公共场景和风格在采样器中填写。",
    "連線正向提示詞 STRING；文字槽位連線實際文字。公共場景和風格在取樣器中填寫。"
  ],
  "Exact lettering for the legacy text slot. New Prompt nodes use the shared STRING input instead.": [
    "旧版文字槽位的实际文字。新版提示词节点使用共用 STRING 输入。",
    "舊版文字槽位的實際文字。新版提示詞節點使用共用 STRING 輸入。"
  ],
  "Per-character negatives are unsupported. Leave empty and use the sampler's common negative prompt.": [
    "不支持单独角色负向提示词，请留空并使用采样器公共负向。",
    "不支援單獨角色負向提示詞，請留空並使用取樣器公共負向。"
  ],
  "LoRA for this character; None disables it. Use a compatible base model; text slots cannot use LoRAs.": [
    "此角色的 LoRA，None 为禁用。须匹配基础模型，文字槽位不可使用。",
    "此角色的 LoRA，None 為禁用。須匹配基礎模型，文字槽位不可使用。"
  ],
  "Model LoRA strength. 0 disables its model effect; higher values strengthen it and can distort the image.": [
    "模型 LoRA 强度。0 为禁用，过高可能导致画面失真。",
    "模型 LoRA 強度。0 為禁用，過高可能導致畫面失真。"
  ],
  "Text-encoder LoRA strength; 0 disables it. Only works if the LoRA has compatible text-encoder weights.": [
    "文本编码器 LoRA 强度，0 为禁用。仅对含兼容编码器权重的 LoRA 有效。",
    "文字編碼器 LoRA 強度，0 為禁用。僅對含相容編碼器權重的 LoRA 有效。"
  ],
  "Normal shares layers for speed; Precision computes each LoRA setting separately. See the panel below for support and fallback details.": [
    "普通模式共享计算，精确模式按 LoRA 独立计算。支持范围及回退说明见下方面板。",
    "普通模式共享計算，精確模式按 LoRA 獨立計算。支援範圍及回退說明見下方面板。"
  ],
  "Point uses X/Y; Box uses a centered rectangle. Text requires a box, and boxes take priority in mixed layouts.": [
    "点使用 X/Y，矩形使用中心与宽高。文字必须用矩形，混合布局中矩形优先。",
    "點使用 X/Y，矩形使用中心與寬高。文字必須用矩形，混合佈局中矩形優先。"
  ],
  "Horizontal center (0–1): left to right. This guides prompt regions rather than exact body positions.": [
    "水平中心坐标 0–1，0 为左，1 为右。控制提示词区域，不保证准确人物位置。",
    "水平中心座標 0–1，0 為左，1 為右。控制提示詞區域，不保證準確人物位置。"
  ],
  "Vertical center, normalized 0–1: 0 is top, 1 is bottom. This controls prompt regions rather than exact body positions.": [
    "垂直中心坐标 0–1，0 为上，1 为下。控制提示词区域，不保证准确人物位置。",
    "垂直中心座標 0–1，0 為上，1 為下。控制提示詞區域，不保證準確人物位置。"
  ],
  "Box width as a fraction of the whole image (0.01–1). Only used for box geometry; it is not the output image width.": [
    "矩形占整图的宽度比例 0.01–1，仅用于矩形布局，不是输出分辨率。",
    "矩形佔整圖的寬度比例 0.01–1，僅用於矩形佈局，不是輸出解析度。"
  ],
  "Box height as a fraction of the whole image (0.01–1). Only used for box geometry; it is not the output image height.": [
    "矩形占整图的高度比例 0.01–1，仅用于矩形布局，不是输出分辨率。",
    "矩形佔整圖的高度比例 0.01–1，僅用於矩形佈局，不是輸出解析度。"
  ],
  "Legacy layout: points, boxes or mixed. Choose mixed to set geometry separately per slot; lettering needs a box.": [
    "旧版布局：points 为点，boxes 为矩形，mixed 按槽位选择。文字需要矩形。",
    "舊版佈局：points 為點，boxes 為矩形，mixed 按槽位選擇。文字需要矩形。"
  ],
  "Shared scene, style and total subject count. An image-derived character pipe supplies its own prompts, overriding this local field.": [
    "公共场景、风格和总人数。图像管线自带的提示词优先于此项。",
    "公共場景、風格和總人數。影像管線自帶的提示詞優先於此項。"
  ],
  "Shared unwanted features; image-derived negatives can override it. Remove text exclusions when generating lettering.": [
    "公共排除项，图像管线的负向可能覆盖此项。生成文字时移除 text 等排除词。",
    "公共排除項，影像管線的負向可能覆蓋此項。生成文字時移除 text 等排除詞。"
  ],
  "Output width in pixels, divisible by 16. Larger images need more time and VRAM.": [
    "输出宽度，单位像素，须为 16 的倍数。越大越耗时和显存。",
    "輸出寬度，單位畫素，須為 16 的倍數。越大越耗時和視訊記憶體。"
  ],
  "Output height in pixels, divisible by 16. Larger images need more time and VRAM.": [
    "输出高度，单位像素，须为 16 的倍数。越大越耗时和显存。",
    "輸出高度，單位畫素，須為 16 的倍數。越大越耗時和視訊記憶體。"
  ],
  "Initial noise seed. Keep it fixed when comparing settings.": [
    "初始噪声种子。对比设置时请固定。",
    "初始噪聲種子。對比設定時請固定。"
  ],
  "Choose whether the seed stays fixed, increments, decrements or is randomized after each generation.": [
    "生成后固定、递增、递减或随机更换种子。",
    "生成後固定、遞增、遞減或隨機更換種子。"
  ],
  "Denoising step count; more steps take longer. Start with the model preset, especially for accelerated models.": [
    "去噪步数，越多越慢。请从对应模型预设开始，尤其是加速模型。",
    "去噪步數，越多越慢。請從對應模型預設開始，尤其是加速模型。"
  ],
  "Prompt guidance strength; excessive values can distort. CFG++ and distilled models may need lower values.": [
    "提示词引导强度，过高可能失真。CFG++ 和蒸馏模型可能需要更低值。",
    "提示詞引導強度，過高可能失真。CFG++ 和蒸餾模型可能需要更低值。"
  ],
  "Denoising algorithm from this ComfyUI installation. Select a scheduler separately; model presets provide tested starting pairs.": [
    "此 ComfyUI 的去噪算法。调度器需单独选择；模型预设提供测试过的起始组合。",
    "此 ComfyUI 的去噪演算法。排程器需單獨選擇；模型預設提供測試過的起始組合。"
  ],
  "How noise levels are distributed across steps. Changing the sampler does not automatically choose its scheduler.": [
    "各步噪声水平的分布方式。更改采样器不会自动切换调度器。",
    "各步噪聲水平的分佈方式。更改取樣器不會自動切換排程器。"
  ],
  "Automatically saves the output with generation/character metadata. This autosave does not embed a ComfyUI workflow; use Save Image if you need one.": [
    "自动保存图像及生成/角色元数据，不含工作流。需要工作流时请使用 Save Image。",
    "自動儲存影像及生成/角色後設資料，不含工作流。需要工作流時請使用 Save Image。"
  ],
  "PNG/lossless WebP preserve pixels; lossy WebP reduces size. All keep generation metadata, without an embedded workflow.": [
    "PNG 和无损 WebP 保留像素；有损 WebP 减小体积。均保留生成元数据，不含工作流。",
    "PNG 和無損 WebP 保留畫素；有損 WebP 減小體積。均保留生成後設資料，不含工作流。"
  ],
  "Lossy WebP quality (1–100). Higher values usually use more space.": [
    "有损 WebP 质量 1–100，越高通常文件越大。",
    "有損 WebP 品質 1–100，越高通常檔案越大。"
  ],
  "Choose how prompt weights are interpreted: ComfyUI parentheses or NovelAI syntax. Image-derived prompts keep their recorded syntax.": [
    "选择 ComfyUI 括号权重或 NovelAI 语法。图像管线保留记录的语法。",
    "選擇 ComfyUI 括號權重或 NovelAI 語法。影像管線保留記錄的語法。"
  ],
  "Restore saved sampling/region settings from the image pipe. Prompts are used even when OFF; model/CLIP/VAE remain manual connections.": [
    "从图像管线恢复尺寸、种子及采样/区域参数。关闭后仍保留管线中的角色提示词。",
    "從影像管線恢復尺寸、種子及取樣/區域引數。關閉後仍保留管線中的角色提示詞。"
  ],
  "Softens transitions between point regions. Higher values blend boundaries more.": [
    "区域边缘羽化宽度。提高可柔化过渡，也可能增加特征混合。",
    "區域邊緣羽化寬度。提高可柔化過渡，也可能增加特徵混合。"
  ],
  "Initial relative influence of the common prompt. Lower values emphasize character prompts early; common influence then increases with the schedule.": [
    "初期公共提示词强度。较低有利于角色分区，较高强化公共场景。",
    "初期公共提示詞強度。較低有利於角色分割槽，較高強化公共場景。"
  ],
  "Extra common-prompt influence after the first three scheduled steps. Higher values introduce shared scene/style more strongly from that point.": [
    "第 3 步后增加的公共强度，用于逐步补充共享场景。",
    "第 3 步後增加的公共強度，用於逐步補充共享場景。"
  ],
  "Early character value gain. Higher values emphasize individual features; later it returns toward ordinary strength.": [
    "初期角色提示词强度。过高可能夸大特征或导致失真。",
    "初期角色提示詞強度。過高可能誇大特徵或導致失真。"
  ],
  "Initial separation between regions. Higher values isolate them more strongly; later boundary decay allows regions to interact.": [
    "初期区域分离强度。越高分区越严格，后期衰减允许互动。",
    "初期區域分離強度。越高分割槽越嚴格，後期衰減允許互動。"
  ],
  "Sampling steps to keep the initial separation before decay; capped by the selected step count. Longer holds can make regions look more isolated.": [
    "衰减前保持初始分离的步数，不超过总步数。保持太久可能使区域割裂。",
    "衰減前保持初始分離的步數，不超過總步數。保持太久可能使區域割裂。"
  ],
  "Amount subtracted from boundary separation at each decay stage. Higher values release separation faster after the hold.": [
    "每个衰减阶段减少的分离强度，越大释放越快。",
    "每個衰減階段減少的分離強度，越大釋放越快。"
  ],
  "Regional routes prompts by region. moss_native needs MOSS; masks become enclosing boxes. Regional strength/boundary controls are ignored.": [
    "regional 按区域控制提示词。moss_native 需 MOSS，遮罩转为外接矩形；忽略区域强度和边界设置。",
    "regional 按區域控制提示詞。moss_native 需 MOSS，遮罩轉為外接矩形；忽略區域強度和邊界設定。"
  ],
  "Embedded guidance, separate from CFG, for FLUX.1/2 Dev. Schnell, Klein and FLUX 3 ignore this control.": [
    "FLUX.1/2 Dev 内置引导，独立于 CFG。Schnell、Klein、FLUX 3 忽略此项。",
    "FLUX.1/2 Dev 內建引導，獨立於 CFG。Schnell、Klein、FLUX 3 忽略此項。"
  ],
  "Select a model-family starting point. Selection alone changes no generation settings; press Apply preset.": [
    "选择模型系列的起始配置。仅选择不会更改设置，请点击应用预设。",
    "選擇模型系列的起始配置。僅選擇不會更改設定，請點選套用預設。"
  ],
  "Apply the selected preset to local controls. Disable image-settings restoration and disconnect converted controls first.": [
    "将预设应用到本地控件。请先关闭图像设置恢复，并断开已连接的控件输入。",
    "將預設應用到本地控制元件。請先關閉影像設定恢復，並斷開已連線的控制元件輸入。"
  ],
  "Read pixels and this extension's character settings from PNG/WebP. Model/CLIP/VAE files must be connected separately.": [
    "从 PNG/WebP 读取图像及角色设置。模型、CLIP、VAE 需另行连接。",
    "從 PNG/WebP 讀取影像及角色設定。模型、CLIP、VAE 需另行連線。"
  ],
  "Upload a local image to ComfyUI's input folder, then load its pixels and supported character metadata.": [
    "上传本地图像到 ComfyUI 输入文件夹，并读取像素和受支持的角色元数据。",
    "上傳本地影像到 ComfyUI 輸入資料夾，並讀取畫素和受支援的角色後設資料。"
  ],
  "How much the crop may be redrawn. Lower preserves the original; higher can change identity.": [
    "裁剪区域的重绘程度。较低保留原图，较高可能改变角色外观。",
    "裁剪區域的重繪程度。較低保留原圖，較高可能改變角色外觀。"
  ],
  "Show advanced detailer controls. Folding them does not reset or disable their saved values.": [
    "显示细节修复高级设置。折叠不会重置或禁用保存的值。",
    "顯示細節修復高階設定。摺疊不會重置或禁用儲存的值。"
  ],
  "Target short side of a sampled crop, capped by max_size. Higher values use more VRAM.": [
    "采样裁剪的目标短边，受 max_size 限制。提高会增加显存占用。",
    "取樣裁剪的目標短邊，受 max_size 限制。提高會增加視訊記憶體佔用。"
  ],
  "Maximum long side of a sampled crop. Limits the resolution requested by guide_size and therefore memory use.": [
    "裁剪长边上限，限制 guide_size 带来的分辨率及内存开销。",
    "裁剪長邊上限，限制 guide_size 帶來的解析度及記憶體開銷。"
  ],
  "Maximum detected regions to correct (1–64), not the number of characters. More processed regions do not guarantee quality.": [
    "最大修复区域数 1–64，并非角色数。更多区域不保证质量。",
    "最大修復區域數 1–64，並非角色數。更多區域不保證品質。"
  ],
  "Minimum detector confidence. Higher values reject uncertain detections; lower values may include more false positives.": [
    "最低检测置信度。提高会过滤不确定检测，降低可能增加误检。",
    "最低檢測置信度。提高會過濾不確定檢測，降低可能增加誤檢。"
  ],
  "Context around each detected region for correction. Higher values include more surrounding pixels, giving the model more context.": [
    "修复裁剪周围的留白倍率。提高可让模型看到更广的上下文。",
    "修復裁剪周圍的留白倍率。提高可讓模型看到更廣的上下文。"
  ],
  "Expand the edit mask in source-image pixels. Adds room around detections; too much may affect nearby features.": [
    "按原图像素扩张修复遮罩。为检测区域留白，过高可能影响邻近特征。",
    "按原影像素擴張修復遮罩。為檢測區域留白，過高可能影響鄰近特徵。"
  ],
  "Fill holes inside the detected mask so missed eyes or interior pixels can be corrected too.": [
    "填充检测遮罩内部孔洞，使遗漏的眼睛或内部像素也能修复。",
    "填充檢測遮罩內部孔洞，使遺漏的眼睛或內部畫素也能修復。"
  ],
  "Close small notches and gaps in mask edges before dilation. Helps avoid narrow unedited cutouts.": [
    "扩张前填补边缘小凹口与缝隙，减少未修复的细窄区域。",
    "擴張前填補邊緣小凹口與縫隙，減少未修復的細窄區域。"
  ],
  "Soften the compositing edge inside disjoint masks. Higher values blend more gradually without editing outside the final masks.": [
    "在互不重叠的最终遮罩内柔化合成边缘，不修改遮罩外部。",
    "在互不重疊的最終遮罩內柔化合成邊緣，不修改遮罩外部。"
  ],
  "Minimum tagger match score for the original character prompt. Raising it skips more uncertain matches; tagger output is never added to the prompt.": [
    "匹配原角色提示词的最低分数。提高会跳过更多不确定匹配，不会追加标签。",
    "匹配原角色提示詞的最低分數。提高會跳過更多不確定匹配，不會追加標籤。"
  ],
  "Minimum score gap between the best and second-best character. Higher values reject ambiguous assignments; ambiguous regions stay unchanged.": [
    "第一与第二角色的最低分差。提高会拒绝更多模糊匹配，保留原区域。",
    "第一與第二角色的最低分差。提高會拒絕更多模糊匹配，保留原區域。"
  ],
  "Context around each crop for tagger matching, separate from correction. Too much can include a neighboring character.": [
    "标签匹配专用留白，与修复裁剪不同。过高可能包含邻近人物。",
    "標籤匹配專用留白，與修復裁剪不同。過高可能包含鄰近人物。"
  ],
  "Select the tagger used for character matching. Only the selected model downloads on first use; cached files are reused.": [
    "用于角色匹配的标签模型。首次仅下载所选模型，之后使用缓存。",
    "用於角色匹配的標籤模型。首次僅下載所選模型，之後使用快取。"
  ],
  "Auto follows ComfyUI's execution device; CPU forces CPU tagging. This controls the tagger, not the generation model.": [
    "auto 跟随 ComfyUI 设备，CPU 强制在 CPU 上推理；仅影响标签模型。",
    "auto 跟隨 ComfyUI 裝置，CPU 強制在 CPU 上推理；僅影響標籤模型。"
  ],
  "Crops inferred together by the tagger, not character count. Larger batches use more memory.": [
    "标签模型同时处理的裁剪数量，并非角色数。越大越占内存。",
    "標籤模型同時處理的裁剪數量，並非角色數。越大越佔記憶體。"
  ],
  "Segmentation detector; OFF excludes it. The default downloads if missing, and selecting SEGM skips BBOX/SAM loading.": [
    "分割模型，OFF 禁用。默认模型缺失时下载；选用 SEGM 后不加载 BBOX/SAM。",
    "分割模型，OFF 禁用。預設模型缺失時下載；選用 SEGM 後不載入 BBOX/SAM。"
  ],
  "Box detector used only when SEGM is OFF. Optional SAM refines its masks; OFF excludes the detector.": [
    "仅在 SEGM 关闭时使用。可由 SAM 优化遮罩，OFF 禁用。",
    "僅在 SEGM 關閉時使用。可由 SAM 最佳化遮罩，OFF 禁用。"
  ],
  "Optional mask refinement for BBOX; SEGM must be OFF. Not loaded when SEGM is selected.": [
    "可选 BBOX 遮罩优化，需关闭 SEGM。选用 SEGM 时不加载。",
    "可選 BBOX 遮罩最佳化，需關閉 SEGM。選用 SEGM 時不載入。"
  ],
  "Show BBOX/SAM selections. Folding only hides the controls; select OFF to disable a model.": [
    "显示 BBOX/SAM 选项。折叠仅隐藏控件，禁用模型需选择 OFF。",
    "顯示 BBOX/SAM 選項。摺疊僅隱藏控制元件，禁用模型需選擇 OFF。"
  ],
  "Character Prompt number; shares its point, box or mask.": [
    "对应提示词编号，沿用其点、矩形或遮罩。",
    "對應提示詞編號，沿用其點、矩形或遮罩。"
  ],
  "One reference image; experimental and not recommended.": [
    "一张参考图。实验性支持，不推荐使用。",
    "一張參考圖。實驗性支援，不推薦使用。"
  ],
  "OFF removes this number's reference; its mask and prompt remain.": [
    "关闭仅移除此编号的参考图，保留遮罩及提示词。",
    "關閉僅移除此編號的參考圖，保留遮罩及提示詞。"
  ],
  "Longest edge, 64–1024 in 64px steps. Keeps aspect ratio; encoders may use a fixed grid.": [
    "最长边 64–1024px，步长 64px。保持比例，编码器可能使用固定网格。",
    "最長邊 64–1024px，步長 64px。保持比例，編碼器可能使用固定網格。"
  ],
  "Image influence, 0–2. Zero skips reference models; stronger can distort color or layout.": [
    "参考强度 0–2。0 跳过参考模型；过高可能改变颜色或布局。",
    "參考強度 0–2。0 跳過參考模型；過高可能改變顏色或佈局。"
  ],
  "Missing catalog SEGM/BBOX models download on execution; cached files are reused. SAM must already be installed. OFF does not load that model.\nChoose a detector for the area to edit: face, eyes, hands, clothes or person. Folding optional controls keeps their values active.": [
    "执行时下载缺失的目录 SEGM/BBOX 模型，并复用缓存。SAM 需提前安装，OFF 不加载。\n按面部、眼睛、手、衣物或人物选择检测模型。折叠可选项后，设置仍然生效。",
    "執行時下載缺失的目錄 SEGM/BBOX 模型，並複用快取。SAM 需提前安裝，OFF 不載入。\n按面部、眼睛、手、衣物或人物選擇檢測模型。摺疊可選項後，設定仍然生效。"
  ],
  "Region shape": ["区域形状", "區域形狀"]
};
