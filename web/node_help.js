// SPDX-License-Identifier: GPL-3.0-only
import { app } from "../../scripts/app.js";

const targets = new Set([
    "RSMultiCharacterPrompt", "RSMultiCharacterPosition", "RSMultiCharacterFinalize", "RSMultiCharacterMask", "RSMultiCharacterMaskDraw",
    "RSMultiCharacterSampler", "RSMultiCharacterLoadImage", "RSMultiCharacterDetailer",
    "RSMultiCharacterTaggerLoader", "RSMultiCharacterPrompts",
]);
const locale = () => String(app.extensionManager?.setting?.get?.("Comfy.Locale")
    ?? app.ui?.settings?.getSettingValue?.("Comfy.Locale") ?? globalThis.navigator?.language ?? "en").slice(0, 2);
const value = (node, name, fallback) => node.widgets?.find(w => w.name === name)?.value ?? fallback;
const typeOf = node => node.comfyClass ?? node.type;

// Display only: inspect controls, never execute connected nodes or change inputs.
export function nodeHelp(node) {
    const lang = locale();
    const text = (en, ko, ja) => lang === "ko" ? ko : lang === "ja" ? ja : en;
    const v = (name, fallback) => value(node, name, fallback);
    const lines = [];
    const add = (en, ko, ja) => lines.push(text(en, ko, ja));
    const saving = () => {
        if (!v("autosave", true)) return add("Autosave OFF: connect an image save node to keep the result.", "자동 저장 OFF: 결과를 보관하려면 이미지 저장 노드를 연결하세요.", "自動保存OFF：結果を残すには画像保存ノードを接続してください。");
        const format = v("save_format", "PNG");
        add(`Autosave: ${format}. Keeps generation metadata, without a workflow.`, `자동 저장: ${format}. 생성 메타데이터를 보존하며 워크플로는 포함하지 않습니다.`, `自動保存：${format}。生成メタデータを保持し、ワークフローは含めません。`);
        if (format === "WebP lossy") add("Lossy WebP changes pixels; quality controls compression, not generation.", "손실 WebP는 픽셀이 달라집니다. 품질 값은 생성 품질이 아닌 저장 압축률입니다.", "非可逆WebPは画素が変わります。品質値は生成品質ではなく保存時の圧縮設定です。");
    };
    switch (typeOf(node)) {
        case "RSMultiCharacterMaskDraw":
            add("Mask drawing · choose a number, then paint", "마스크 그리기 · 번호 선택 후 칠하기", "マスク描画 · 番号を選んで塗る");
            add("The reference stays behind the masks. Each number uses the same Prompt/LoRA slot, regardless of the person shown.", "밑그림 위에 번호별로 칠하세요. 참조 인물과 무관하게 같은 번호의 프롬프트·LoRA가 적용됩니다.", "下絵の上に番号別で塗ります。参照人物とは関係なく同じ番号のPrompt・LoRAを使います。");
            add("Paint, erase, undo, move and resize one layer at a time. Blank layers fall back to XY/boxes. This node replaces earlier masks; add individual masks after it to override.", "그리기·지우개·되돌리기와 번호별 이동·크기를 지원합니다. 빈 번호는 XY·박스를 씁니다. 이전 마스크는 대체하며 개별 마스크를 뒤에 연결하면 덮어쓸 수 있습니다.", "描画・消去・元に戻す・番号別の移動と倍率を使えます。空の番号はXY・ボックスに戻ります。以前のマスクは置換し、後ろに個別マスクを繋ぐと上書きできます。");
            add("Only masks enter generation. Canvas overflow is clipped; pose is approximate. The colored preview includes margin. Text needs a box; MOSS masks need regional mode.", "생성에는 마스크만 전달합니다. 캔버스 밖은 자르며 자세는 대략 유도합니다. 색 미리보기는 여유 폭 포함입니다. 텍스트는 박스, MOSS 마스크는 regional을 쓰세요.", "生成にはマスクだけを渡します。外側は切り取り、ポーズは目安です。色プレビューは余白込み。文字はボックス、MOSSマスクはregionalを使ってください。");
            break;
        case "RSMultiCharacterMask":
            add("Character mask · white selects the region", "캐릭터 마스크 · 흰색이 적용 영역", "キャラクターマスク · 白が適用領域");
            add("Overrides this character's XY/box in any builder order. Off restores them.", "노드 순서와 무관하게 해당 번호의 좌표·상자를 대체합니다. 끄면 복원됩니다.", "ノード順に関係なく同じ番号の座標・ボックスを置き換えます。OFFで戻ります。");
            add("Use one full-canvas mask per character; overlaps share captions. Margin uses source pixels.", "캐릭터마다 전체 캔버스 마스크 한 장을 연결하세요. 겹친 곳은 조건을 공유합니다. 여유 폭은 원본 픽셀 기준입니다.", "1人につきキャンバス全体のマスク1枚を接続。重複部分は条件を共有し、余白は元画像のピクセル単位です。");
            add(`Size ×${v("scale", 1)}; shift X ${v("offset_x", 0)}, Y ${v("offset_y", 0)}. Outside the canvas is clipped.`, `크기 ×${v("scale", 1)} · 이동 X ${v("offset_x", 0)}, Y ${v("offset_y", 0)}. 캔버스 밖은 잘립니다.`, `倍率 ×${v("scale", 1)}・移動 X ${v("offset_x", 0)}, Y ${v("offset_y", 0)}。外側は切り取ります。`);
            add("Guides prompt attention, not exact pose. MOSS native needs boxes; choose regional for masks.", "프롬프트 적용 영역이며 자세 고정은 아닙니다. MOSS 마스크는 regional을 선택하세요.", "プロンプト領域の指定で、ポーズ固定ではありません。MOSSのマスクはregionalを選んでください。");
            break;
        case "RSMultiCharacterPrompt": {
            const count = Number(v("character_count", 2));
            const ids = kind => Array.from({length: count}, (_, i) => i + 1)
                .filter(i => v(`character${i}_enable`, true) && v(`character${i}_kind`, "character") === kind).join(", ") || "—";
            add("Prompt slots · shared STRING input", "프롬프트 슬롯 · 같은 STRING 입력", "プロンプト枠 · 共通のSTRING入力");
            add(`Character: ${ids("character")} / Text: ${ids("text")}`, `캐릭터: ${ids("character")} / 텍스트: ${ids("text")}`, `キャラクター：${ids("character")} / テキスト：${ids("text")}`);
            add("Character uses STRING as its positive prompt; Text uses it as the words to draw. Switching kind keeps the connection.", "캐릭터는 연결한 STRING을 긍정 프롬프트로, 텍스트는 그릴 글자로 사용합니다. 종류를 바꿔도 연결은 유지됩니다.", "キャラクターはSTRINGを肯定プロンプト、テキストは描く文字として使います。種類を変えても接続は保持されます。");
            if (ids("text") !== "—") add("Text needs a box in Position. Remove text from the common negative. Short words work better; spelling is not guaranteed.", "텍스트는 위치 노드에서 박스로 지정하세요. 공통 네거티브의 text를 빼고 짧은 단어부터 시작하세요. 정확한 철자는 보장하지 않습니다.", "テキストは位置ノードでボックスに指定してください。共通ネガティブのtextを外し、短い単語から試してください。綴りは保証しません。");
            add("This node sets the active count. Disabled and out-of-count slots are excluded. Use the sampler for the common negative.", "이 노드가 최종 사용 수를 결정합니다. OFF·개수 밖 슬롯은 제외하며 공통 네거티브는 샘플러에 적습니다.", "このノードが使用数を決めます。OFFと範囲外の枠は除外されます。共通ネガティブはサンプラーに入力してください。");
            break;
        }
        case "RSMultiCharacterPosition": {
            const count = Number(v("character_count", 2));
            const boxes = Array.from({length: count}, (_, i) => i + 1).filter(i => v(`character${i}_geometry`, "point") === "box");
            add("Position · points, boxes and masks", "위치 · 포인트·박스·마스크", "位置 · 点・ボックス・マスク");
            add("Select a numbered region above the layout before dragging. Corner/−/+ resizes boxes and masks; mask scaling keeps its shape and number. Undo/reset restores placement.", "배치도 위에서 번호를 선택한 뒤 드래그하세요. 모서리·−/+로 박스·마스크 크기를 조절합니다. 마스크 모양·번호는 유지되고 되돌리기·배치 초기화를 지원합니다.", "配置図の上で番号を選びドラッグ。角・−/+でボックス・マスクを拡縮。マスクの形・番号は保持し、元に戻す・配置リセットも使えます。");
            add(`Rows: ${count}; boxes: ${boxes.join(", ") || "—"}. X/Y are normalized 0–1; (0,0) is top left.`, `표시 행: ${count}, 박스: ${boxes.join(", ") || "—"}. X/Y는 0–1이며 (0,0)은 왼쪽 위입니다.`, `表示行：${count}、ボックス：${boxes.join(", ") || "—"}。X/Yは0–1で、(0,0)は左上です。`);
            add("Point partitions use the nearest XY. Coincident points spread left to right by number. Box uses center XY and width/height; boxes take priority over points.", "XY는 가까운 좌표끼리 영역을 나눕니다. 같은 좌표는 번호순으로 왼쪽부터 분산합니다. 박스는 중심 XY와 폭·높이를 사용하며 XY 영역보다 우선합니다.", "XYは最寄りの点で領域を分割し、同じ座標は番号順に左から分散します。ボックスは中心XYと幅・高さを使い、XY領域より優先します。");
            add("Text requires a box. Match numbers with Prompt/LoRA. The diagram guides prompt regions; it does not guarantee body positions.", "텍스트는 박스가 필요합니다. 프롬프트·LoRA와 번호를 맞추세요. 배치도는 프롬프트 영역 안내이며 실제 인물 위치를 보장하지 않습니다.", "テキストにはボックスが必要です。プロンプト・LoRAと番号を合わせてください。図はプロンプト領域の目安であり、人物位置は保証しません。");
            break;
        }
        case "RSMultiCharacterFinalize":
            add("Finalize · connect to Sampler / Detailer", "최종 파이프 · 샘플러/디테일러로 연결", "最終パイプ · Sampler / Detailerへ接続");
            add("Prompt, LoRA and Position merge by slot number in any order. Prompt determines count; missing LoRA/Position default to None/center.", "프롬프트·LoRA·위치는 연결 순서와 무관하게 같은 번호끼리 합쳐집니다. 프롬프트가 사용 수를 결정하고 생략한 LoRA·위치는 없음·중앙이 됩니다.", "Prompt・LoRA・Positionは順序に関係なく同じ番号で統合します。Promptが使用数を決め、省略したLoRA・位置はNone・中央になります。");
            add("Up to 10 character/text slots. Missing prompts are reported at execution. More processed regions do not guarantee quality.", "캐릭터·텍스트 합계 최대 10개입니다. 누락 프롬프트는 실행 시 안내합니다. 처리수가 많을수록 품질을 보장하지 못합니다.", "キャラクター・テキスト合計10枠までです。欠落プロンプトは実行時に報告します。処理数が多いほど品質は保証できません。");
            break;
        case "RSMultiCharacterSampler":
            add("Sampling · current selections", "샘플링 · 현재 선택 안내", "サンプリング · 現在の選択");
            if (v("use_image_settings", false)) add("Image settings ON: the image pipe supplies dimensions, seed and sampling/routing settings as well as prompts. Select MODEL/CLIP/VAE and global LoRAs manually.", "이미지 설정 복원 ON: 이미지 파이프의 프롬프트뿐 아니라 해상도·시드·샘플링·영역 설정도 사용합니다. MODEL/CLIP/VAE와 전역 LoRA는 직접 연결하세요.", "画像設定復元ON：画像パイプのプロンプトに加え、解像度・シード・サンプリング・領域設定も使います。MODEL/CLIP/VAEと全体LoRAは手動接続してください。");
            else add("Image settings OFF: use this node's sampling controls. An image-loaded pipe still supplies its prompts and characters.", "이미지 설정 복원 OFF: 이 노드의 생성 설정을 사용합니다. 이미지에서 온 파이프는 프롬프트·캐릭터를 계속 전달합니다.", "画像設定復元OFF：このノードの生成設定を使います。画像由来のパイプのプロンプト・キャラクターは引き続き使用します。");
            if (v("layout_method", "regional") === "moss_native") add("MOSS native: requires MOSS and box regions. Regional strengths, boundary and feather controls are ignored. Experimental layout.", "MOSS 원본 레이아웃: MOSS 모델과 박스 영역이 필요합니다. 영역 강도·경계·페더 설정은 무시하는 실험 기능입니다.", "MOSSネイティブ：MOSSとボックス領域が必要です。領域強度・境界・フェザー設定は無視される実験機能です。");
            else add("Regional: controls prompt influence by region. Normal/Precision LoRA mode comes from the pipe. Presets apply only when you press Apply.", "영역 제어: 구역별 프롬프트 영향을 조절합니다. 일반/정밀 LoRA 방식은 파이프에서 받습니다. 프리셋은 적용 버튼을 눌러야 반영됩니다.", "領域制御：領域ごとのプロンプト影響を調整します。LoRAの通常/精密モードはパイプから受け取ります。プリセットは適用ボタンで反映します。");
            add(`Sampling pair: ${v("sampler_name", "euler_ancestral")} / ${v("scheduler", "sgm_uniform")}. Changing one does not reset the other.`, `샘플러 조합: ${v("sampler_name", "euler_ancestral")} / ${v("scheduler", "sgm_uniform")}. 한쪽을 바꿔도 다른 쪽은 유지됩니다.`, `組み合わせ：${v("sampler_name", "euler_ancestral")} / ${v("scheduler", "sgm_uniform")}。片方を変えても他方は変わりません。`);
            saving();
            break;
        case "RSMultiCharacterLoadImage":
            add("Image load · restore the character pipe", "이미지 로드 · 캐릭터 파이프 복원", "画像読込 · キャラクターパイプの復元");
            add("Reads supported PNG/WebP character metadata, including per-slot LoRAs and Normal/Precision mode. Use the generation info output to check what was restored.", "지원하는 PNG/WebP 메타데이터에서 캐릭터·슬롯별 LoRA·일반/정밀 방식을 복원합니다. 생성 정보 출력에서 복원 내용을 확인하세요.", "対応PNG/WebPのメタデータからキャラクター・枠別LoRA・通常/精密モードを復元します。生成情報出力で内容を確認してください。");
            add("Files are not embedded: base model and global LoRAs must be connected manually. Missing character LoRAs cause an error at sampling. Enable sampler use_image_settings to restore sampling too.", "모델 파일 자체는 포함되지 않습니다. 기본 모델·전역 LoRA는 직접 연결하고, 캐릭터 LoRA 파일이 없으면 생성 시 오류가 납니다. 생성 설정까지 쓰려면 샘플러의 이미지 설정 복원을 켜세요.", "モデルファイル自体は含まれません。基本モデル・全体LoRAは手動接続し、キャラクターLoRAがなければ生成時にエラーになります。生成設定も使う場合はサンプラーの画像設定復元をオンにしてください。");
            break;
        case "RSMultiCharacterDetailer":
            add("Detailer · one matched character per crop", "디테일러 · 매칭한 캐릭터별 보정", "Detailer · 一致したキャラクターごとに補正");
            add("Connect the image and pipe, matching MODEL/CLIP/VAE, and detectors. Multiple characters require a tagger. Uncertain matches are skipped; text slots are excluded.", "이미지·파이프와 같은 MODEL/CLIP/VAE, 감지 로더를 연결하세요. 여러 캐릭터는 태거가 필요합니다. 모호한 매칭은 건너뛰며 텍스트 슬롯은 제외합니다.", "画像・パイプと同じMODEL/CLIP/VAE、検出ローダーを接続してください。複数キャラクターにはタガーが必要です。曖昧な一致はスキップし、テキスト枠は除外します。");
            add("Each matched crop uses its character prompt and LoRA in Precision. Higher denoise permits larger changes. max_regions limits edits, not character count.", "매칭한 크롭은 해당 캐릭터 프롬프트·LoRA를 정밀 방식으로 사용합니다. denoise가 높을수록 크게 바뀝니다. max_regions는 캐릭터 수가 아닌 최대 보정 영역 수입니다.", "一致した切り抜きにキャラクタープロンプト・LoRAを精密方式で使います。denoiseが高いほど大きく変化します。max_regionsは人数ではなく最大補正領域数です。");
            add(v("show_advanced", false) ? "Advanced controls are visible: mask repair and matching thresholds affect which areas change." : "Advanced controls are folded; their saved values still apply.", v("show_advanced", false) ? "상세 설정 표시 중: 마스크 보정·매칭 임계값에 따라 수정할 영역이 달라집니다." : "상세 설정은 접혀 있어도 저장된 값이 계속 적용됩니다.", v("show_advanced", false) ? "詳細設定を表示中：マスク補正・一致閾値が修正領域に影響します。" : "詳細設定は折り畳んでいても保存値が適用されます。");
            saving();
            break;
        case "RSMultiCharacterTaggerLoader":
            add("Tagger · character matching only", "태거 · 캐릭터 매칭 전용", "タガー · キャラクター照合専用");
            add(`Selected model: ${v("model_name", "WD ViT v3")}. Downloads only the selected model at execution and reuses cached files.`, `선택 모델: ${v("model_name", "WD ViT v3")}. 실행할 때 선택 모델만 받고 캐시를 재사용합니다.`, `選択モデル：${v("model_name", "WD ViT v3")}。実行時に選んだモデルだけを取得し、キャッシュを再利用します。`);
            add("batch_size is the number of crops inferred together, not character count. Lower it if memory is tight. Tag scores choose your original prompt; tags never enter it.", "batch_size는 한 번에 추론할 크롭 수이며 인식 캐릭터 수가 아닙니다. 메모리가 부족하면 줄이세요. 태그 점수로 원래 프롬프트를 고르며 태그는 프롬프트에 추가하지 않습니다.", "batch_sizeは同時推論する切り抜き数であり、人数ではありません。メモリ不足なら下げてください。タグの点数で元のプロンプトを選び、タグ自体は追加しません。");
            if (v("device", "auto") === "cpu") add("CPU selected: runs tagging on CPU.", "CPU 선택: 태거 추론을 CPU에서 처리합니다.", "CPU選択：タガーをCPUで実行します。");
            else add("Auto device: follows ComfyUI's execution device; falls back to CUDA/CPU if ComfyUI management is unavailable.", "자동 장치: ComfyUI의 실행 장치를 따릅니다. 장치 관리 기능을 사용할 수 없으면 CUDA·CPU 중 선택합니다.", "自動デバイス：ComfyUIの実行デバイスに従います。デバイス管理を使えない場合はCUDA・CPUを選択します。");
            if (v("model_name", "WD ViT v3") === "PixAI Tagger v1.0") add("This selection needs additional tagger dependencies and more memory; start with batch_size=1.", "이 모델은 추가 태거 의존성과 더 많은 메모리가 필요합니다. batch_size=1부터 시작하세요.", "このモデルには追加依存関係と多くのメモリが必要です。batch_size=1から試してください。");
            break;
        case "RSMultiCharacterPrompts":
            add("Legacy prompt node · workflow compatibility", "이전 통합 프롬프트 노드 · 호환용", "旧統合プロンプトノード · 互換用");
            add("New workflows can use Prompt → LoRA → Position → Finalize in any role order. This legacy node stays available for existing graphs.", "새 워크플로는 프롬프트·LoRA·위치를 원하는 순서로 연결한 뒤 최종 파이프로 마무리하세요. 이 노드는 기존 워크플로 호환용입니다.", "新規ワークフローはPrompt・LoRA・Positionを任意順で接続し、Finalizeで仕上げてください。このノードは既存グラフの互換用です。");
            add(`Layout: ${v("layout_mode", "points")}. Text requires boxes/mixed and the literal-text field. Per-character negatives are unsupported; use the common negative.`, `배치 방식: ${v("layout_mode", "points")}. 텍스트는 boxes/mixed와 별도 글자 입력을 사용합니다. 캐릭터별 UC는 지원하지 않으니 공통 네거티브를 쓰세요.`, `配置：${v("layout_mode", "points")}。テキストはboxes/mixedと文字入力欄を使います。個別UCは未対応のため共通ネガティブを使ってください。`);
            break;
    }
    if (lines.length && node.inputs?.some(i => i.link != null && node.widgets?.some(w => w.name === i.name)))
        add("Connected control values are resolved at execution; this panel describes local widget selections.", "연결된 설정값은 실행 시 결정됩니다. 이 창은 노드의 입력칸에 선택한 값을 설명합니다.", "接続した設定値は実行時に決まります。この案内はローカルの選択値を説明します。");
    return lines;
}

export function helpLines(paragraphs, width) {
    const limit = Math.max(80, width - 32), lines = [];
    for (const paragraph of paragraphs) {
        let line = "", used = 0;
        // Character wrapping also bounds long filenames and sampler identifiers.
        for (const ch of paragraph) {
            const size = /[\u1100-\uffff]/u.test(ch) ? 13 : 8;
            if (line && used + size > limit) { lines.push(line.trimEnd()); line = ""; used = 0; }
            if (!line && !ch.trim()) continue;
            line += ch; used += size;
        }
        if (line) lines.push(line);
        lines.push("");
    }
    return lines;
}

app.registerExtension({
    name: "RS.MultiCharacter.NodeHelp",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (!targets.has(nodeData.name)) return; // LoRA and Detection already have panels.
        const refresh = node => {
            const help = node.widgets?.find(w => w.name === "rs_mc_node_help");
            if (!help) return;
            const signature = JSON.stringify([node.size?.[0], nodeHelp(node)]);
            if (signature === node.rsMcHelpSignature) return;
            node.rsMcHelpSignature = signature;
            const size = node.computeSize();
            node.setSize([Math.max(node.size[0], size[0]), size[1]]);
            node.setDirtyCanvas(true, true);
        };
        const created = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = created?.apply(this, arguments);
            if (this.widgets?.some(w => w.name === "rs_mc_node_help")) return result;
            this.addCustomWidget({
                name: "rs_mc_node_help", type: "rs_mc_display", serialize: false,
                options: {serialize: false}, serializeValue: () => undefined,
                computeSize: (width = this.size?.[0] ?? 340) => [300, helpLines(nodeHelp(this), width).length * 17 + 16],
                draw(ctx, node, width, y) {
                    const lines = helpLines(nodeHelp(node), width);
                    ctx.save();
                    ctx.fillStyle = "#171d27"; ctx.fillRect(8, y + 2, width - 16, lines.length * 17 + 10);
                    ctx.font = "12px sans-serif";
                    lines.forEach((line, i) => {
                        ctx.fillStyle = i === 0 ? "#d1e3ff" : "#b4bdcc";
                        ctx.fillText(line, 16, y + 19 + i * 17, width - 32);
                    });
                    ctx.restore();
                },
            });
            for (const widget of this.widgets ?? []) {
                if (widget.options?.serialize === false) continue;
                const callback = widget.callback;
                widget.callback = function (...args) {
                    const result = callback?.apply(this, args);
                    refresh(node);
                    return result;
                };
            }
            const node = this;
            refresh(node);
            return result;
        };
        for (const hook of ["onConfigure", "onConnectionsChange", "onResize", "onDrawForeground"]) {
            const previous = nodeType.prototype[hook];
            nodeType.prototype[hook] = function () {
                const result = previous?.apply(this, arguments);
                refresh(this); // Covers locale, linked controls, preset changes and undo.
                return result;
            };
        }
    },
});
