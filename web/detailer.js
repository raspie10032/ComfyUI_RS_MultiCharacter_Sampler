import { chineseLocale, chineseText } from "./i18n.js";
import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

const modelFields = ["face_segm_model", "face_bbox_model", "sam_model"];
const labels = {
    en: ["SEGM model", "BBOX model", "SAM model", "Next run", "SEGM only. BBOX / SAM are skipped.", "BBOX + SAM masks.", "BBOX rectangles (SAM OFF).", "Select SEGM or BBOX. SAM alone cannot detect regions.", "Connected model inputs are resolved when the workflow runs."],
    ko: ["SEGM 모델", "BBOX 모델", "SAM 모델", "현재 선택의 실행 방식", "SEGM만 사용합니다. BBOX·SAM은 건너뜁니다.", "BBOX로 감지하고 SAM으로 마스크를 만듭니다.", "BBOX 사각 영역을 사용합니다 (SAM OFF).", "SEGM 또는 BBOX를 선택하세요. SAM만으로는 영역을 감지할 수 없습니다.", "연결된 모델 입력은 실행할 때 결정됩니다."],
    ja: ["SEGM モデル", "BBOX モデル", "SAM モデル", "現在の選択での実行方法", "SEGMのみ使用。BBOX・SAMはスキップします。", "BBOXで検出し、SAMでマスクを作成します。", "BBOXの矩形領域を使用（SAM OFF）。", "SEGMまたはBBOXを選択してください。SAM単独では領域を検出できません。", "接続されたモデル入力は実行時に決まります。"],
};
const loaderNotes = {
    en: "Missing catalog SEGM/BBOX models download on execution; cached files are reused. SAM must already be installed. OFF does not load that model.\nChoose a detector for the area to edit: face, eyes, hands, clothes or person. Folding optional controls keeps their values active.",
    ko: "목록의 SEGM·BBOX 모델이 없으면 실행할 때 받고 캐시를 재사용합니다. SAM은 미리 설치해야 합니다. OFF 모델은 불러오지 않습니다.\n얼굴·눈·손·옷·인물 등 보정할 부위에 맞는 모델을 고르세요. 옵션을 접어도 선택값은 유지됩니다.",
    ja: "カタログのSEGM・BBOXモデルがなければ実行時に取得し、キャッシュを再利用します。SAMは事前インストールが必要です。OFFのモデルは読み込みません。\n顔・目・手・服・人物など修正対象に合うモデルを選んでください。折り畳んでも選択値は有効です。",
};

function updateLoader(node, clearProgress = false) {
    const locale = String(app.extensionManager?.setting?.get?.("Comfy.Locale") ?? app.ui?.settings?.getSettingValue("Comfy.Locale") ?? "en");
    const text = chineseLocale(locale) ? labels.en.map(line => chineseText(line, locale)) : labels[locale.slice(0, 2)] ?? labels.en;
    const enabled = name => {
        const value = node.widgets?.find(w => w.name === name)?.value;
        return value && !["OFF", "None"].includes(value);
    };
    for (const [index, name] of modelFields.entries()) {
        const widget = node.widgets?.find(w => w.name === name);
        if (widget) widget.label = text[index];
    }
    let plan = node.widgets?.find(w => w.name === "rs_detector_plan");
    if (!plan) {
        plan = ComfyWidgets.STRING(node, "rs_detector_plan", ["STRING", { multiline: true }], app).widget;
        plan.options.serialize = false;
        plan.serialize = false;
        plan.serializeValue = () => undefined;
        plan.inputEl.readOnly = true;
        plan.computeSize = () => [320, 180];
    }
    plan.label = text[3];
    const connected = node.inputs?.some(input => modelFields.includes(input.name) && input.link != null);
    plan.value = (connected ? text[8] : text[enabled("face_segm_model") ? 4 : enabled("face_bbox_model") ? (enabled("sam_model") ? 5 : 6) : 7])
        + "\n\n" + (chineseLocale(locale) ? chineseText(loaderNotes.en, locale) : loaderNotes[locale.slice(0, 2)] ?? loaderNotes.en);
    if (clearProgress) {
        const status = node.widgets?.find(w => w.name === "rs_tagger_status");
        if (status) {
            status.onRemove?.();
            node.widgets.splice(node.widgets.indexOf(status), 1);
        }
    }
}

const targets = {
    RSMultiCharacterDetectionLoader: ["show_optional_models", new Set(["face_segm_model", "show_optional_models"])],
    RSMultiCharacterDetailer: ["show_advanced", new Set(["denoise", "seed", "control_after_generate", "autosave", "show_advanced"])],
};

function update(node, toggle, basic) {
    const expanded = Boolean(node.widgets?.find(w => w.name === toggle)?.value);
    for (const widget of node.widgets ?? []) {
        if (widget.options?.serialize === false) continue;
        const hide = (!basic.has(widget.name) &&
            (!expanded || (widget.name === "webp_quality" &&
            node.widgets.find(w => w.name === "save_format")?.value !== "WebP lossy")));
        if (hide && !widget.rsMcDetailVisible && !widget.type?.startsWith("converted-widget")) {
            widget.rsMcDetailVisible = { type: widget.type, computeSize: widget.computeSize, hidden: widget.hidden };
            widget.type = "rs-mc-detail-hidden";
            widget.hidden = true;
            widget.computeSize = () => [0, -4];
            if (widget.inputEl) widget.inputEl.hidden = true;
        } else if (!hide && widget.rsMcDetailVisible) {
            if (widget.type === "rs-mc-detail-hidden") Object.assign(widget, widget.rsMcDetailVisible);
            delete widget.rsMcDetailVisible;
            if (widget.inputEl) widget.inputEl.hidden = false;
        }
    }
    const size = node.computeSize();
    node.setSize([Math.max(node.size[0], size[0]), size[1]]);
    node.setDirtyCanvas(true, true);
}

app.registerExtension({
    name: "RS.MultiCharacter.Detailer",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        const spec = targets[nodeData.name];
        if (!spec) return;
        const [toggle, basic] = spec;
        for (const hook of ["onNodeCreated", "onConfigure"]) {
            const previous = nodeType.prototype[hook];
            nodeType.prototype[hook] = function () {
                const result = previous?.apply(this, arguments);
                if (nodeData.name === "RSMultiCharacterDetectionLoader" && hook === "onConfigure") {
                    for (const widget of this.widgets ?? []) {
                        if (["face_segm_model", "face_bbox_model", "sam_model"].includes(widget.name) && widget.value === "None") {
                            widget.value = "OFF";
                        }
                    }
                }
                if (hook === "onNodeCreated") {
                    for (const name of [toggle, "save_format", ...(nodeData.name === "RSMultiCharacterDetectionLoader" ? modelFields : [])]) {
                        const widget = this.widgets?.find(w => w.name === name);
                        if (widget) {
                            const callback = widget.callback;
                            widget.callback = (...args) => {
                                callback?.apply(widget, args);
                                if (nodeData.name === "RSMultiCharacterDetectionLoader") updateLoader(this, modelFields.includes(name));
                                update(this, toggle, basic);
                            };
                        }
                    }
                }
                if (nodeData.name === "RSMultiCharacterDetectionLoader") updateLoader(this, hook === "onConfigure");
                update(this, toggle, basic);
                return result;
            };
        }
        {
            const previous = nodeType.prototype.onConnectionsChange;
            nodeType.prototype.onConnectionsChange = function () {
                const result = previous?.apply(this, arguments);
                if (nodeData.name === "RSMultiCharacterDetectionLoader") updateLoader(this, true);
                update(this, toggle, basic);
                return result;
            };
        }
    },
});
