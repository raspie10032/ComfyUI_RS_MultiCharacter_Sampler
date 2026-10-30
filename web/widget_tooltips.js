// SPDX-License-Identifier: GPL-3.0-only
import { chineseLocale, chineseText } from "./i18n.js";
import { app } from "../../scripts/app.js";

// One catalogue for canvas widgets, multiline DOM widgets and Vue node rows.
// The frontend's native delay is global; do not change other nodes' settings.
export const HOVER_DELAY = 2000;
const tips = {
    mask_transforms: ["Saved mask placement. Select a numbered region above the layout to move or resize it.", "마스크 배치 저장값입니다. 배치도 위에서 번호를 선택해 이동·크기를 조절하세요.", "マスク配置の保存値。配置図の上で番号を選び移動・拡縮します。"],
    drawing: ["Select a character number and paint over the reference. The image is a guide only; numbered masks are saved in the workflow.", "번호를 고르고 밑그림 위에 칠하세요. 이미지는 참조용이며 번호별 마스크는 워크플로에 저장됩니다.", "番号を選び下絵の上に塗ります。画像は参照のみで番号別マスクはワークフローに保存されます。"],
    character_id: ["Character Prompt row number. Attach one mask to each character you want to shape.", "프롬프트 노드의 캐릭터 번호입니다. 모양을 정할 캐릭터마다 마스크 하나를 붙이세요.", "Promptのキャラクター番号です。形を指定するキャラクターごとに1枚接続します。"],
    enabled: ["Off clears this character's mask and restores its XY/box; other characters keep their masks.", "끄면 이 번호의 마스크를 지우고 좌표·상자로 돌아갑니다. 다른 번호는 유지합니다.", "OFFでこの番号のマスクを消し、座標・ボックスに戻します。他の番号は保持します。"],
    margin: ["Expand white by this many source pixels. Leave space for hair, clothing and contact.", "원본 마스크에서 흰 영역을 이 픽셀 수만큼 확장합니다. 머리·옷·접촉에 여유를 주세요.", "元マスクの白領域をこのピクセル数だけ拡張します。髪・服・接触に余白を残します。"],
    threshold: ["Pixels above this value select the character region. Gray is converted to black or white.", "이 값보다 밝은 픽셀을 캐릭터 영역으로 씁니다. 회색은 흑백으로 바꿉니다.", "この値より明るい画素をキャラクター領域にします。グレーは白黒に変換します。"],
    mask: ["One full-canvas MASK: white selects the region. Shift/scale overflow is clipped; pose remains approximate.", "전체 캔버스 MASK 한 장: 흰색이 영역입니다. 이동·확대로 넘친 부분은 잘리며 자세는 대략 유도합니다.", "全キャンバスのMASK1枚：白が領域。移動・拡大で外に出る部分は切り取り、ポーズは目安です。"],
    offset_x: ["Shift by a fraction of canvas width: +0.1 moves right 10%. Overflow is clipped.", "캔버스 가로 대비 이동량입니다. +0.1은 오른쪽 10%이며, 밖으로 나가면 잘립니다.", "幅に対する移動比率。+0.1で右へ10%。外側は切り取ります。"],
    offset_y: ["Shift by a fraction of canvas height: +0.1 moves down 10%. Overflow is clipped.", "캔버스 세로 대비 이동량입니다. +0.1은 아래 10%이며, 밖으로 나가면 잘립니다.", "高さに対する移動比率。+0.1で下へ10%。外側は切り取ります。"],
    scale: ["Uniform size about the canvas centre: 0.5 half, 1 original, 2 double. Overflow is clipped.", "캔버스 중심 기준 크기 비율입니다. 0.5 절반·1 원본·2 두 배이며, 넘친 부분은 잘립니다.", "キャンバス中央基準の倍率。0.5半分・1元・2倍。外側は切り取ります。"],
    character_count: ["Active slots (1–10), including text. Prompt excludes slots above this count; match numbers across role nodes.", "사용할 슬롯 수(1–10)로 텍스트도 포함합니다. 프롬프트에서 줄인 번호 밖은 제외되므로 노드별 번호를 맞추세요.", "使用するスロット数（1–10）で文字も含みます。Promptで指定数を超えた番号は除外されるため、ノード間で番号を合わせてください。"],
    enable: ["Enable this numbered slot. Disabled slots are excluded from generation.", "이 번호를 생성에 사용할지 선택합니다. 끄면 해당 슬롯을 제외합니다.", "この番号を生成に使うか選びます。OFFのスロットは除外されます。"],
    kind: ["Character uses the STRING as a prompt; Text uses it as literal lettering. Text needs box geometry.", "같은 STRING을 캐릭터 프롬프트 또는 실제 글자로 사용합니다. 텍스트는 위치 노드에서 박스를 선택하세요.", "同じSTRINGをキャラクタープロンプトまたは描く文字に使います。Textの位置はBoxにしてください。"],
    character: ["Connect the positive prompt STRING, or exact lettering for a text slot. Put shared scene/style instructions in the sampler.", "긍정 프롬프트 STRING을 연결합니다. 텍스트 슬롯이면 그릴 글자를 연결하세요.", "肯定プロンプトのSTRINGを接続します。Textなら描く文字を接続してください。"],
    text: ["Exact lettering for the legacy text slot. New Prompt nodes use the shared STRING input instead.", "이전 노드의 실제 글자 입력입니다. 새 프롬프트 노드는 공용 STRING 연결을 사용합니다.", "旧ノードの文字列入力です。新しいPromptは共通のSTRING接続を使います。"],
    uc: ["Per-character negatives are unsupported. Leave empty and use the sampler's common negative prompt.", "캐릭터별 네거티브는 지원하지 않습니다. 비워두고 샘플러의 공통 네거티브를 사용하세요.", "個別ネガティブは未対応です。空欄にし、Samplerの共通ネガティブを使ってください。"],
    lora: ["LoRA for this character; None disables it. Use a compatible base model; text slots cannot use LoRAs.", "이 캐릭터에 적용할 LoRA로 None이면 끕니다. 기본 모델과 호환되어야 하며 텍스트 슬롯에는 쓸 수 없습니다.", "このキャラクター用LoRAで、Noneなら無効です。基本モデルとの互換性が必要で、Textには使えません。"],
    lora_strength: ["Model LoRA strength. 0 disables its model effect; higher values strengthen it and can distort the image.", "생성 모델 쪽 LoRA 강도입니다. 0이면 모델 효과를 끕니다.", "生成モデル側のLoRA強度。0でモデル効果を無効にします。"],
    lora_clip_strength: ["Text-encoder LoRA strength; 0 disables it. Only works if the LoRA has compatible text-encoder weights.", "텍스트 인코더의 LoRA 강도로 0이면 끕니다. 호환되는 인코더 가중치가 없는 LoRA에는 효과가 없습니다.", "テキストエンコーダーのLoRA強度で、0なら無効です。対応するエンコーダー重みがないLoRAには効果がありません。"],
    lora_application_mode: ["Normal shares layers for speed; Precision computes each LoRA setting separately. See the panel below for support and fallback details.", "일반은 계산을 공유해 빠르게, 정밀은 LoRA별로 따로 계산합니다. 지원 범위와 예외는 하단 설명을 보세요.", "Normalは計算を共有して高速化し、PrecisionはLoRA別に計算します。対応範囲と例外は下の説明をご覧ください。"],
    geometry: ["Point uses X/Y; Box uses a centered rectangle. Text requires a box, and boxes take priority in mixed layouts.", "XY는 좌표 주변, 박스는 중심과 너비·높이로 영역을 정합니다. 텍스트는 박스가 필수이며 혼합 시 박스가 우선합니다.", "PointはXYの周り、Boxは中心と幅・高さで領域を決めます。TextはBox必須で、混在時はBoxが優先されます。"],
    x: ["Horizontal center (0–1): left to right. This guides prompt regions rather than exact body positions.", "가로 중심(0–1)으로 왼쪽에서 오른쪽 방향입니다. 프롬프트 영역의 기준이며 신체 위치를 고정하지 않습니다.", "横方向の中心（0–1）で左から右へ移動します。プロンプト領域の目安で、身体位置を固定するものではありません。"],
    y: ["Vertical center, normalized 0–1: 0 is top, 1 is bottom. This controls prompt regions rather than exact body positions.", "세로 중심 좌표(0–1)입니다. 0은 위, 1은 아래입니다.", "縦方向の中心（0–1）。0は上、1は下。"],
    slot_width: ["Box width as a fraction of the whole image (0.01–1). Only used for box geometry; it is not the output image width.", "전체 이미지 대비 박스 너비 비율(0.01–1)입니다. 박스 배치에서만 사용하며 출력 이미지의 해상도와는 다릅니다.", "画像全体に対するBox幅の比率（0.01–1）。Box配置のみで使い、出力解像度とは異なります。"],
    slot_height: ["Box height as a fraction of the whole image (0.01–1). Only used for box geometry; it is not the output image height.", "전체 이미지 대비 박스 높이 비율(0.01–1)입니다. 박스 배치에서만 사용하며 출력 이미지의 해상도와는 다릅니다.", "画像全体に対するBox高さの比率（0.01–1）。Box配置のみで使い、出力解像度とは異なります。"],
    layout_mode: ["Legacy layout: points, boxes or mixed. Choose mixed to set geometry separately per slot; lettering needs a box.", "이전 노드의 배치 방식입니다. points는 XY, boxes는 박스, mixed는 번호별 선택입니다.", "旧ノードの配置方式。pointsはXY、boxesは矩形、mixedは番号別の選択です。"],
    prompt: ["Shared scene, style and total subject count. An image-derived character pipe supplies its own prompts, overriding this local field.", "공통 장면·화풍·전체 인원수를 적습니다. 이미지에서 읽은 파이프에는 자체 프롬프트가 있어 이 입력보다 우선합니다.", "共通の場面・画風・全体人数を入力します。画像由来のパイプにプロンプトがある場合は、そちらが優先されます。"],
    negative_prompt: ["Shared unwanted features; image-derived negatives can override it. Remove text exclusions when generating lettering.", "공통으로 피할 요소이며 이미지의 네거티브가 우선할 수 있습니다. 글자를 만들 때는 text 등 제외어를 빼세요.", "共通で避ける要素で、画像由来の設定が優先される場合があります。文字を描くときはtextなどの除外語を外してください。"],
    width: ["Output width in pixels, divisible by 16. Larger images need more time and VRAM.", "출력 가로 픽셀 수로 16의 배수입니다. 클수록 시간·VRAM을 더 사용합니다.", "出力幅のピクセル数（16の倍数）。大きいほど時間・VRAMが増えます。"],
    height: ["Output height in pixels, divisible by 16. Larger images need more time and VRAM.", "출력 세로 픽셀 수로 16의 배수입니다. 클수록 시간·VRAM을 더 사용합니다.", "出力高さのピクセル数（16の倍数）。大きいほど時間・VRAMが増えます。"],
    seed: ["Initial noise seed. Keep it fixed when comparing settings.", "시작 노이즈의 시드입니다. 설정 비교 시 고정하세요.", "初期ノイズのシード。設定比較では固定してください。"],
    control_after_generate: ["Choose whether the seed stays fixed, increments, decrements or is randomized after each generation.", "생성 후 시드를 고정·증가·감소·무작위 중 어떻게 바꿀지 선택합니다.", "生成後のシードを固定・増加・減少・ランダムのどれにするか選びます。"],
    steps: ["Denoising step count; more steps take longer. Start with the model preset, especially for accelerated models.", "노이즈를 제거할 횟수로 많으면 느려집니다. 고속화 모델을 포함해 모델별 프리셋에서 시작하세요.", "ノイズ除去の回数で、多いほど遅くなります。高速モデルも含めモデル用プリセットから始めてください。"],
    cfg: ["Prompt guidance strength; excessive values can distort. CFG++ and distilled models may need lower values.", "프롬프트를 따르는 강도로 과하면 왜곡될 수 있습니다. CFG++·증류 모델은 낮은 값이 필요할 수 있습니다.", "プロンプトへの誘導強度で、過大だと歪む場合があります。CFG++・蒸留モデルは低い値が必要な場合があります。"],
    sampler_name: ["Denoising algorithm from this ComfyUI installation. Select a scheduler separately; model presets provide tested starting pairs.", "현재 ComfyUI의 노이즈 제거 알고리즘입니다. 스케줄러는 별도로 고릅니다.", "このComfyUIのノイズ除去アルゴリズムです。スケジューラーは別に選びます。"],
    scheduler: ["How noise levels are distributed across steps. Changing the sampler does not automatically choose its scheduler.", "스텝별 노이즈 수준을 배분하는 방식입니다. 샘플러를 바꿔도 스케줄러는 자동으로 바뀌지 않습니다.", "ステップ間のノイズレベルの配分です。Samplerを変更しても自動では切り替わりません。"],
    autosave: ["Automatically saves the output with generation/character metadata. This autosave does not embed a ComfyUI workflow; use Save Image if you need one.", "결과와 생성·캐릭터 메타데이터를 자동 저장합니다. 워크플로는 넣지 않으므로 필요하면 기본 이미지 저장 노드를 쓰세요.", "結果と生成・キャラクターメタデータを自動保存します。ワークフローは含めないため、必要なら標準のSave Imageを使ってください。"],
    save_format: ["PNG/lossless WebP preserve pixels; lossy WebP reduces size. All keep generation metadata, without an embedded workflow.", "PNG·무손실 WebP는 픽셀을 보존하고 손실 WebP는 용량을 줄입니다. 모두 생성 메타데이터를 보존하며 워크플로는 넣지 않습니다.", "PNG・可逆WebPは画素を保持し、非可逆WebPは容量を減らします。生成メタデータは保持しますがワークフローは含めません。"],
    webp_quality: ["Lossy WebP quality (1–100). Higher values usually use more space.", "손실 WebP의 품질(1–100)입니다. 높을수록 보통 용량이 커집니다.", "非可逆WebPの品質（1–100）。高いほど通常は容量が増えます。"],
    prompt_syntax: ["Choose how prompt weights are interpreted: ComfyUI parentheses or NovelAI syntax. Image-derived prompts keep their recorded syntax.", "가중치를 ComfyUI 괄호 방식 또는 NovelAI 문법으로 해석할지 선택합니다. 이미지에서 읽은 프롬프트는 기록된 문법을 따릅니다.", "重みをComfyUIの括弧構文とNovelAI構文のどちらで解釈するか選びます。画像由来のプロンプトは記録された構文を使います。"],
    use_image_settings: ["Restore saved sampling/region settings from the image pipe. Prompts are used even when OFF; model/CLIP/VAE remain manual connections.", "이미지의 샘플링·영역 설정을 복원합니다. 꺼도 이미지 프롬프트는 쓰며 모델·CLIP·VAE는 직접 연결합니다.", "画像のサンプリング・領域設定を復元します。OFFでも画像のプロンプトは使い、モデル・CLIP・VAEは手動接続です。"],
    region_feather: ["Softens transitions between point regions. Higher values blend boundaries more.", "XY 영역 사이의 전환을 부드럽게 합니다. 높이면 경계가 더 섞입니다.", "Point領域間の境界を滑らかにします。高いほど混ざりやすくなります。"],
    initial_common_prior: ["Initial relative influence of the common prompt. Lower values emphasize character prompts early; common influence then increases with the schedule.", "초반 공통 프롬프트의 상대 영향입니다. 낮추면 초반 캐릭터 프롬프트를 더 강조합니다.", "序盤の共通プロンプトの相対的な影響です。下げると序盤はキャラクターが強くなり、その後はスケジュールに従って共通の影響が増します。"],
    common_after_step3_boost: ["Extra common-prompt influence after the first three scheduled steps. Higher values introduce shared scene/style more strongly from that point.", "초기 3스텝 이후 공통 프롬프트에 더할 영향입니다. 높이면 그 시점부터 공통 장면·화풍이 더 강하게 들어갑니다.", "最初の3ステップ後に加える共通プロンプトの影響です。高いほど、その時点から共通の場面・画風が強くなります。"],
    initial_character_gain: ["Early character value gain. Higher values emphasize individual features; later it returns toward ordinary strength.", "초반 캐릭터 특징의 증폭 강도입니다. 높이면 개별 특징을 강조하고 후반에는 보통 강도로 돌아갑니다.", "序盤のキャラクター特徴の増幅率。高いほど個別の特徴を強め、後半は通常の強度に戻ります。"],
    initial_spatial_separation: ["Initial separation between regions. Higher values isolate them more strongly; later boundary decay allows regions to interact.", "초반 영역 분리 강도입니다. 높이면 영역을 강하게 구분합니다.", "序盤の領域分離強度。高いほど領域を強く分けます。"],
    boundary_hold_steps: ["Sampling steps to keep the initial separation before decay; capped by the selected step count. Longer holds can make regions look more isolated.", "초기 분리 강도를 유지할 스텝 수이며 전체 스텝을 넘지 않습니다. 오래 유지하면 영역이 더 분리되어 보일 수 있습니다.", "初期分離を維持するステップ数で、全ステップ数までに制限されます。長くすると領域が分離して見える場合があります。"],
    boundary_decrement: ["Amount subtracted from boundary separation at each decay stage. Higher values release separation faster after the hold.", "감소 단계마다 경계 분리 강도에서 뺄 값입니다. 높이면 유지 구간 뒤 경계를 더 빨리 풉니다.", "減衰段階ごとに境界の分離強度から引く値。高いほど維持期間後に境界を早く解放します。"],
    layout_method: ["Auto: MOSS pose → native JSON; otherwise regional. Regional routes prompts by region. moss_native needs MOSS; masks become enclosing boxes. Regional strength/boundary controls are ignored.", "auto: MOSS 포즈는 네이티브 JSON, 나머지는 regional. regional은 영역별 프롬프트 제어입니다. moss_native는 MOSS 전용이며 마스크는 외곽 사각형으로 변환됩니다. 영역 강도·경계 설정은 쓰지 않습니다.", "auto：MOSSポーズはネイティブJSON、それ以外はregional。Regionalは領域別のプロンプト制御です。moss_nativeはMOSS専用。マスクは外接矩形に変換され、領域強度・境界設定は使いません。"],
    flux_guidance: ["Embedded guidance, separate from CFG, for FLUX.1/2 Dev. Schnell, Klein and FLUX 3 ignore this control.", "CFG와 별도인 FLUX.1·2 Dev 내장 가이던스입니다. Schnell·Klein·FLUX 3는 쓰지 않습니다.", "CFGとは別のFLUX.1・2 Dev内蔵ガイダンスです。Schnell・Klein・FLUX 3では使いません。"],
    rs_mc_preset: ["Select a model-family starting point. Selection alone changes no generation settings; press Apply preset.", "모델 계열별 시작 설정을 고릅니다. 선택만으로 생성값이 바뀌지 않으며 프리셋 적용을 눌러야 합니다.", "モデル系統別の開始設定を選びます。選ぶだけでは生成値は変わらず、Apply presetが必要です。"],
    rs_mc_apply_preset: ["Apply the selected preset to local controls. Disable image-settings restoration and disconnect converted controls first.", "선택한 프리셋을 조절 항목에 적용합니다. 이미지 설정 복원을 끄고 연결된 항목은 입력칸으로 되돌리세요.", "選択プリセットを操作項目に適用します。画像設定の復元をOFFにし、接続項目はウィジェットに戻してください。"],
    image: ["Read pixels and this extension's character settings from PNG/WebP. Model/CLIP/VAE files must be connected separately.", "PNG·WebP에서 이미지와 이 확장의 캐릭터 설정을 읽습니다. 모델·CLIP·VAE 파일은 직접 연결하세요.", "PNG・WebPから画像と本拡張のキャラクター設定を読みます。モデル・CLIP・VAEは別途接続してください。"],
    upload: ["Upload a local image to ComfyUI's input folder, then load its pixels and supported character metadata.", "로컬 이미지를 ComfyUI 입력 폴더로 올린 뒤 이미지와 지원되는 캐릭터 메타데이터를 읽습니다.", "ローカル画像をComfyUIの入力フォルダーにアップロードし、画像と対応するキャラクターメタデータを読み込みます。"],
    denoise: ["How much the crop may be redrawn. Lower preserves the original; higher can change identity.", "크롭을 다시 그릴 정도입니다. 낮으면 원본을 유지하고 높으면 외형이 달라질 수 있습니다.", "切り抜きを描き直す量です。低いと原画を保ち、高いと外見が変わる場合があります。"],
    show_advanced: ["Show advanced detailer controls. Folding them does not reset or disable their saved values.", "디테일러 상세 조절 항목을 펼칩니다. 접어도 저장된 값은 초기화되거나 꺼지지 않습니다.", "Detailerの詳細項目を表示します。折り畳んでも保存値はリセット・無効化されません。"],
    guide_size: ["Target short side of a sampled crop, capped by max_size. Higher values use more VRAM.", "보정 크롭의 목표 짧은 변으로 긴 변은 최대 크기로 제한합니다. 높이면 VRAM을 더 씁니다.", "補正する切り抜きの目標短辺で、長辺はmax_sizeで制限します。高いほどVRAMを使います。"],
    max_size: ["Maximum long side of a sampled crop. Limits the resolution requested by guide_size and therefore memory use.", "보정 크롭의 긴 변 최대 픽셀 수입니다. 목표 짧은 변 크기로 늘린 해상도와 메모리 사용을 제한합니다.", "補正する切り抜きの長辺の最大ピクセル数。guide_sizeで拡大する解像度とメモリ使用量を制限します。"],
    max_regions: ["Maximum detected regions to correct (1–64), not the number of characters. More processed regions do not guarantee quality.", "수정할 감지 영역 수의 상한(1–64)이며 캐릭터 수가 아닙니다. 처리수가 많을수록 품질을 보장하지 못합니다.", "修正する検出領域数の上限（1–64）で、人数ではありません。処理領域を増やしても品質は保証されません。"],
    bbox_threshold: ["Minimum detector confidence. Higher values reject uncertain detections; lower values may include more false positives.", "감지 결과를 받을 최소 신뢰도입니다. 높이면 불확실한 감지를 거르고 낮추면 오탐도 늘 수 있습니다.", "検出を採用する最小信頼度。高くすると不確かな検出を除外し、低くすると誤検出も増える場合があります。"],
    crop_factor: ["Context around each detected region for correction. Higher values include more surrounding pixels, giving the model more context.", "보정할 감지 영역 주변의 여백 배율입니다. 높이면 주변 픽셀을 더 포함해 모델에 더 넓은 맥락을 줍니다.", "補正領域の周辺余白の倍率。高いほど周辺画素を含め、モデルに広い文脈を与えます。"],
    dilation: ["Expand the edit mask in source-image pixels. Adds room around detections; too much may affect nearby features.", "원본 픽셀 단위로 보정 마스크를 확장합니다. 감지 주변에 여유를 주며 과하면 인접 특징에도 영향을 줄 수 있습니다.", "原画像のピクセル単位で補正マスクを拡張します。検出周辺に余裕を加えますが、過大だと隣の特徴に影響する場合があります。"],
    fill_holes: ["Fill holes inside the detected mask so missed eyes or interior pixels can be corrected too.", "감지 마스크 내부의 구멍을 채워 빠진 눈·내부 픽셀도 보정할 수 있게 합니다.", "検出マスク内部の穴を埋め、抜けた目や内部画素も補正できるようにします。"],
    closing: ["Close small notches and gaps in mask edges before dilation. Helps avoid narrow unedited cutouts.", "확장 전에 마스크 가장자리의 작은 요철·틈을 메웁니다. 가늘게 남는 미보정 부분을 줄입니다.", "拡張前にマスク端の小さな凹凸や隙間を埋めます。細い未補正部分を減らします。"],
    mask_feather: ["Soften the compositing edge inside disjoint masks. Higher values blend more gradually without editing outside the final masks.", "서로 분리된 마스크 안에서 합성 경계를 부드럽게 합니다. 높이면 최종 마스크 밖을 수정하지 않으면서 경계를 완만하게 섞습니다.", "分離したマスク内で合成境界を滑らかにします。高いほど最終マスク外を変えずに境界を緩やかに混ぜます。"],
    match_min_score: ["Minimum tagger match score for the original character prompt. Raising it skips more uncertain matches; tagger output is never added to the prompt.", "원래 캐릭터 프롬프트를 선택할 최소 태거 매칭 점수입니다. 높이면 불확실한 매칭을 더 건너뜁니다.", "元のキャラクタープロンプトを選ぶ最小タガー一致点数。上げると不確かな一致を多くスキップします。"],
    match_min_margin: ["Minimum score gap between the best and second-best character. Higher values reject ambiguous assignments; ambiguous regions stay unchanged.", "1위와 2위 캐릭터 점수의 최소 차이입니다. 높이면 애매한 배정을 더 거릅니다.", "1位と2位のキャラクターの最小点差。高いほど曖昧な割り当てを除外し、曖昧な領域は原画を保持します。"],
    match_crop_factor: ["Context around each crop for tagger matching, separate from correction. Too much can include a neighboring character.", "태거 매칭용 여백으로 보정 크롭과 별도입니다. 과하면 옆 캐릭터가 함께 들어올 수 있습니다.", "タガー照合用の余白で、補正用とは別です。大きすぎると隣のキャラクターが入る場合があります。"],
    model_name: ["Select the tagger used for character matching. Only the selected model downloads on first use; cached files are reused.", "캐릭터 매칭에 사용할 태거입니다. 선택한 모델만 첫 사용에 받고 캐시를 재사용합니다.", "キャラクター照合用のタガーです。選んだモデルだけを初回に取得し、キャッシュを再利用します。"],
    device: ["Auto follows ComfyUI's execution device; CPU forces CPU tagging. This controls the tagger, not the generation model.", "자동은 ComfyUI 실행 장치를 따르고 CPU는 태거를 CPU에서 실행합니다. 생성 모델이 아니라 태거에만 적용합니다.", "AutoはComfyUIの実行デバイスに従い、CPUはタガーをCPUで実行します。生成モデルではなくタガーだけに適用します。"],
    batch_size: ["Crops inferred together by the tagger, not character count. Larger batches use more memory.", "태거가 동시에 추론할 크롭 수이며 캐릭터 수가 아닙니다. 높이면 메모리를 더 씁니다.", "タガーが同時推論する切り抜き数で人数ではありません。大きいほどメモリが増えます。"],
    face_segm_model: ["Segmentation detector; OFF excludes it. The default downloads if missing, and selecting SEGM skips BBOX/SAM loading.", "영역 분할 모델로 OFF면 끕니다. 기본 모델은 없으면 받으며 SEGM 선택 시 BBOX·SAM은 로드하지 않습니다.", "領域分割モデルで、OFFなら除外します。既定モデルがなければ取得し、SEGM選択時はBBOX・SAMを読み込みません。"],
    face_bbox_model: ["Box detector used only when SEGM is OFF. Optional SAM refines its masks; OFF excludes the detector.", "SEGM이 OFF일 때 쓰는 박스 감지 모델입니다. SAM으로 마스크를 다듬을 수 있고 OFF면 끕니다.", "SEGMがOFFのとき使う矩形検出モデルです。SAMでマスクを整えられ、OFFなら除外します。"],
    sam_model: ["Optional mask refinement for BBOX; SEGM must be OFF. Not loaded when SEGM is selected.", "BBOX 마스크를 다듬는 선택 모델로 SEGM은 꺼야 합니다. SEGM 선택 시 로드하지 않습니다.", "BBOXマスクを整える任意モデルで、SEGMはOFFが必要です。SEGM選択時は読み込みません。"],
    show_optional_models: ["Show BBOX/SAM selections. Folding only hides the controls; select OFF to disable a model.", "BBOX·SAM 선택을 펼칩니다. 접기는 표시만 숨기므로 모델을 끄려면 OFF를 고르세요.", "BBOX・SAMの選択を表示します。折り畳みは非表示にするだけなので、無効化はOFFを選んでください。"],
};

export function fieldHelp(type, name, locale = "en") {
    if (name === "start_scale") {
        const messages = ["Starting width/height ratio. Lower values may reduce quality or change composition; 1.0 is ordinary sampling.", "시작 너비·높이 비율. 낮을수록 품질 저하·구도 변화 가능. 1.0은 일반 생성입니다.", "開始幅・高さの倍率。低いほど品質低下・構図変化の可能性。1.0は通常生成。"];
        return locale.startsWith("ko") ? messages[1] : locale.startsWith("ja") ? messages[2] : messages[0];
    }
    if (type === "RSAnimaReferenceAdapter") {
        const rows = {
            strength: ["Adapter strength; 0 bypasses reference processing.", "어댑터 강도. 0이면 참조 처리를 생략합니다.", "アダプター強度。0で参照処理を省略。"],
            reference_guidance: ["Reference influence. For a global image, 1 skips an extra prediction.", "참조 영향. 전역 참조에서 1은 추가 예측을 생략합니다.", "参照の影響。全体参照では1で追加予測を省略。"],
            adapter_name: ["Dedicated Anima reference adapter, not a style LoRA.", "스타일 LoRA가 아닌 Anima 전용 참조 어댑터입니다.", "Style LoRAではなくAnima専用参照アダプター。"],
            cache_text_kv: ["Temporary text cache, up to 256 MiB; disabled with character LoRAs.", "최대 256MiB 임시 텍스트 캐시. 캐릭터별 LoRA와 함께 쓰면 꺼집니다.", "最大256MiBの一時テキストキャッシュ。人物別LoRA併用時は無効。"],
            correction: ["Reference guidance correction: APG, rescale or none.", "참조 가이던스 보정: APG·리스케일·없음.", "参照ガイダンス補正：APG・Rescale・なし。"],
            image: ["One reference influences the whole image, including other characters.", "참조 한 장이 다른 캐릭터를 포함한 이미지 전체에 영향을 줍니다.", "参照1枚が他の人物を含む画像全体に影響。"],
        };
        const row = rows[name];
        if (row) return chineseLocale(locale) ? chineseText(row[0], locale) : row[locale.startsWith("ko") ? 1 : locale.startsWith("ja") ? 2 : 0];
    }
    if (type === "RSMultiCharacterReference" || type === "RSAnimaCharacterReference") {
        const reference = {
            character_id: ["Character Prompt number; shares its point, box or mask.", "프롬프트의 번호와 맞추세요. 같은 포인트·박스·마스크를 씁니다.", "Promptと同じ番号に指定。同じPoint・Box・Maskを使います。"],
            image: ["One reference image; experimental and not recommended.", "참조 이미지 한 장. 실험적 지원이며 권장하지 않습니다.", "参照画像1枚。実験的対応・非推奨です。"],
            enabled: ["OFF removes this number's reference; its mask and prompt remain.", "끄면 이 번호의 참조만 제거합니다. 마스크·프롬프트는 유지합니다.", "OFFでこの番号の画像参照だけを解除。Mask・Promptは維持します。"],
            resolution: ["Longest edge, 64–1024 in 64px steps. Keeps aspect ratio; encoders may use a fixed grid.", "긴 변 64~1024px, 64px 단위. 비율을 유지하며 인코더에 따라 고정 크기로 처리합니다.", "長辺64～1024px、64px単位。比率を維持し、Encoderにより固定サイズで処理します。"],
            strength: ["Image influence, 0–2. Zero skips reference models; stronger can distort color or layout.", "참조 영향 0~2. 0은 참조 처리를 생략합니다. 높이면 색·구도가 왜곡될 수 있습니다.", "参照の影響0～2。0で処理を省略。高すぎると色・構図が崩れる場合があります。"],
        }[name];
        if (reference) return chineseLocale(locale) ? chineseText(reference[0], locale) : reference[locale.startsWith("ko") ? 1 : locale.startsWith("ja") ? 2 : 0];
    }
    let key = name;
    const slot = /^character\d+(?:_(.*))?$/.exec(name);
    if (slot) key = slot[1] ?? "character";
    if (slot && (key === "width" || key === "height")) key = `slot_${key}`;
    if (name.startsWith("upload")) key = "upload";
    const row = tips[key];
    return chineseLocale(locale) ? chineseText(row?.[0] ?? "", locale) : row?.[locale.startsWith("ko") ? 1 : locale.startsWith("ja") ? 2 : 0] ?? "";
}

const isOurs = node => String(node?.comfyClass ?? node?.type ?? "").startsWith("RSMultiCharacter") || ["RSAnimaReferenceAdapter", "RSAnimaCharacterReference"].includes(String(node?.comfyClass ?? node?.type ?? ""));
const hidden = widget => widget.hidden || widget.type === "hidden" || String(widget.type).startsWith("converted-widget");

// Timer logic is independent of the renderer so cancellation can be tested.
export function hoverController({ setTimer, clearTimer, show, hide, valid }) {
    let timer, current;
    const clear = () => { clearTimer(timer); timer = undefined; current = undefined; hide(); };
    return {
        clear,
        move(target) {
            if (target && current?.node === target.node && current?.widget === target.widget && current?.text === target.text) {
                Object.assign(current, target);
                return;
            }
            clear();
            if (!target?.text) return;
            current = target;
            timer = setTimer(() => {
                timer = undefined;
                if (valid(target)) show(target);
                else clear();
            }, HOVER_DELAY);
        },
    };
}

app.registerExtension({
    name: "RS.MultiCharacter.WidgetTooltips",
    beforeConfigureGraph() { this._hoverController?.clear(); },
    setup() {
        let bubble, titles = [];
        const style = document.createElement("style");
        style.textContent = `
            body.rs-mc-hovering-control .node-tooltip,
            body.rs-mc-hovering-control .p-tooltip { visibility:hidden !important; }
            .rs-mc-field-tooltip { position:fixed; z-index:100001; pointer-events:none;
                max-width:min(420px,calc(100vw - 24px)); box-sizing:border-box; padding:10px 12px;
                border:1px solid var(--border-color,#686868); border-radius:6px;
                background:var(--comfy-input-bg,#222); color:var(--input-text,#eee);
                font:13px/1.5 sans-serif; white-space:pre-wrap; overflow-wrap:anywhere;
                box-shadow:0 4px 16px #0006; }
        `;
        document.head.appendChild(style);
        const clear = () => {
            bubble?.remove(); bubble = null;
            document.body.classList.remove("rs-mc-hovering-control");
            for (const [el, title] of titles) if (!el.hasAttribute("title")) el.setAttribute("title", title);
            titles = [];
        };
        const active = ({ node, widget }) => {
            const graph = app.canvas?.graph ?? app.graph;
            return graph?.getNodeById(node.id) === node && node.widgets?.includes(widget) && !hidden(widget);
        };
        const controller = hoverController({
            setTimer: (fn, ms) => window.setTimeout(fn, ms), clearTimer: id => window.clearTimeout(id),
            valid: active, hide: clear,
            show({ text, x, y, element }) {
                bubble = document.createElement("div");
                bubble.className = "rs-mc-field-tooltip";
                bubble.setAttribute("role", "tooltip");
                bubble.textContent = text;
                document.body.appendChild(bubble);
                if (element) {
                    bubble.id = "rs-mc-field-tooltip";
                    // Do not alter aria-describedby supplied by the frontend.
                }
                const box = bubble.getBoundingClientRect();
                bubble.style.left = `${Math.max(12, Math.min(x + 12, window.innerWidth - box.width - 12))}px`;
                bubble.style.top = `${Math.max(12, Math.min(y + 18, window.innerHeight - box.height - 12))}px`;
            },
        });
        const targetAt = event => {
            const graph = app.canvas?.graph ?? app.graph;
            const el = event.target;
            // Canvas-backed multiline inputs live in DOM overlays, not the canvas.
            const host = el.closest?.("[data-node-id]");
            let node = host ? graph?.getNodeById(host.dataset.nodeId) : null, widget;
            const row = el.closest?.('[data-testid="node-widget"]');
            if (node && row) {
                // Vue rows expose the actual field name on their input/label.
                const name = row.querySelector("[name]")?.getAttribute("name") ?? row.querySelector("[aria-label]")?.getAttribute("aria-label") ?? row.querySelector('[data-testid="widget-layout-field-label"]')?.textContent?.trim();
                widget = node.widgets?.find(w => w.name === name || w.label === name);
            }
            if (!widget && el.nodeName !== "CANVAS") {
                const nodes = node ? [node] : graph?._nodes ?? [];
                outer: for (const candidate of nodes) {
                    if (!isOurs(candidate)) continue;
                    for (const w of candidate.widgets ?? []) {
                        const input = w.inputEl ?? w.element;
                        if (input?.contains?.(el)) { node = candidate; widget = w; break outer; }
                    }
                }
            }
            if (el.nodeName === "CANVAS" && el === app.canvas?.canvas) {
                node = app.canvas.node_over;
                widget = app.canvas.getWidgetAtCursor?.();
            }
            if (!isOurs(node) || !widget || hidden(widget)) return;
            const locale = app.extensionManager?.setting?.get?.("Comfy.Locale") ?? navigator.language ?? "en";
            const text = fieldHelp(node.comfyClass ?? node.type, widget.name, locale) || widget.tooltip;
            return text ? { node, widget, text, x:event.clientX, y:event.clientY, element:el } : null;
        };
        const move = event => {
            if (event.buttons || app.canvas?.dragging_canvas || app.extensionManager?.setting?.get?.("Comfy.EnableTooltips") === false) {
                controller.clear(); return;
            }
            const target = targetAt(event);
            controller.move(target);
            if (!target) return;
            document.body.classList.add("rs-mc-hovering-control");
            // Browser-native title tooltips have no configurable delay.
            for (let el=event.target; el && el !== document.body; el=el.parentElement) {
                if (el.hasAttribute?.("title")) { titles.push([el, el.getAttribute("title")]); el.removeAttribute("title"); }
            }
        };
        window.addEventListener("mousemove", move);
        for (const name of ["pointerdown", "wheel", "keydown", "blur", "resize"]) window.addEventListener(name, controller.clear, { capture:true, passive:true });
        window.addEventListener("mouseout", event => { if (!event.relatedTarget) controller.clear(); });
        document.addEventListener("visibilitychange", controller.clear);
        // Nodes can be deleted/replaced without a pointer movement.
        app.canvas?.canvas?.addEventListener("mouseleave", event => {
            if (!event.relatedTarget?.closest?.(".dom-widget")) controller.clear();
        });
        this._hoverController = controller;
    },
});
