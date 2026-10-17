// SPDX-License-Identifier: GPL-3.0-only
import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

const words = {
    en: {
        select: "Model family preset", choose: "Choose a preset", apply: "Apply preset", info: "Preset guidance",
        idle: "Choose a starting point, then Apply preset. Sampling and regional controls remain editable.",
        ready: "Selected; press Apply preset to copy the values.", match: "Current controls match this preset.",
        edited: "Current controls differ from this preset. Your manual settings will be used.",
        restore: "Turn off use_image_settings first. Image settings take priority over these controls.",
        native: "Choose regional layout first. These presets tune regional sampling, not MOSS native layout.",
        linked: "Disconnect or convert these inputs back to widgets before applying: ",
        missing: "This installation cannot apply the preset. Unavailable control or value: ",
        unchanged: "No values were changed.",
    },
    ko: {
        select: "모델 계열 프리셋", choose: "프리셋 선택", apply: "프리셋 적용", info: "프리셋 안내",
        idle: "시작 설정을 선택한 뒤 프리셋 적용을 누르세요. 적용 후에도 생성·영역 설정을 직접 조절할 수 있습니다.",
        ready: "선택한 설정을 쓰려면 프리셋 적용을 누르세요.", match: "현재 설정이 이 프리셋과 일치합니다.",
        edited: "현재 설정은 프리셋과 다릅니다. 직접 조절한 값으로 실행합니다.",
        restore: "먼저 이미지 설정 복원을 꺼 주세요. 복원 모드에서는 이미지 속 설정이 우선 적용됩니다.",
        native: "먼저 레이아웃 방식을 regional로 바꿔 주세요. 이 프리셋은 MOSS 원본 레이아웃이 아닌 영역 제어용입니다.",
        linked: "적용 전에 다음 입력의 연결을 해제하고 위젯으로 되돌려 주세요: ",
        missing: "이 설치본에 없는 설정 또는 값이라 적용할 수 없습니다: ", unchanged: "설정값은 변경되지 않았습니다.",
    },
    ja: {
        select: "モデル系統プリセット", choose: "プリセットを選択", apply: "プリセットを適用", info: "プリセットの案内",
        idle: "開始設定を選び、適用ボタンを押してください。適用後も生成・領域設定を手動で調整できます。",
        ready: "選択済みです。適用ボタンを押すと設定が反映されます。", match: "現在の設定はこのプリセットと一致しています。",
        edited: "現在の設定はプリセットと異なります。手動で調整した値で実行します。",
        restore: "先に画像設定の復元をオフにしてください。復元モードでは画像内の設定が優先されます。",
        native: "先にレイアウト方式をregionalにしてください。このプリセットはMOSSのネイティブレイアウト用ではありません。",
        linked: "適用前に接続を解除し、次の入力をウィジェットに戻してください: ",
        missing: "この環境では適用できません。利用できない設定または値: ", unchanged: "設定値は変更していません。",
    },
};
const locale = () => {
    const value = String(app.ui?.settings?.getSettingValue("Comfy.Locale") ?? "en").slice(0, 2);
    return words[value] ? value : "en";
};
const widget = (node, name) => node.widgets?.find(w => w.name === name);
const external = (node, name) => node.inputs?.some(i => i.name === name && i.link != null)
    || widget(node, name)?.type?.startsWith("converted-widget");
const transient = w => {
    w.serialize = false;
    w.options = { ...w.options, serialize: false };
    w.serializeValue = () => undefined;
    return w;
};

let catalog;
app.registerExtension({
    name: "RS.MultiCharacter.Presets",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "RSMultiCharacterSampler") return;
        // Fetch once from this extension's static assets. No model auto-detection or execution override.
        try {
            catalog ??= fetch(new URL("./model_presets.json", import.meta.url)).then(r => {
                if (!r.ok) throw new Error(`Preset catalog: HTTP ${r.status}`);
                return r.json();
            });
            const presets = await catalog;
            install(nodeType, presets);
        } catch (error) {
            console.error("RS MultiCharacter presets could not be loaded; manual sampling is available.", error);
        }
    },
});

function install(nodeType, presets) {
    const selected = node => presets.find(p => p.id === node.properties?.rs_mc_preset);
    function refresh(node) {
        const control = widget(node, "rs_mc_preset");
        if (!control) return;
        const lang = locale(), t = words[lang], preset = selected(node);
        control.label = t.select;
        control.options.values = [t.choose, ...presets.map(p => p.label[lang])];
        control.value = preset?.label[lang] ?? t.choose;
        widget(node, "rs_mc_apply_preset").label = t.apply;
        const status = widget(node, "rs_mc_preset_info");
        status.label = t.info;
        const matches = preset && Object.entries(preset.settings).every(([key, value]) => widget(node, key)?.value === value);
        let message = !preset ? t.idle : matches ? t.match : node.rsMcPresetApplied ? t.edited : t.ready;
        if (widget(node, "use_image_settings")?.value) message = t.restore;
        else if (widget(node, "layout_method")?.value === "moss_native") message = t.native;
        status.value = [node.rsMcPresetError || message, preset?.note[lang]].filter(Boolean).join("\n");
        node.setDirtyCanvas(true, true);
    }
    function apply(node) {
        const preset = selected(node), t = words[locale()];
        if (!preset) return;
        const fail = message => { node.rsMcPresetError = `${message} ${t.unchanged}`; refresh(node); };
        const keys = Object.keys(preset.settings);
        const linked = [...keys, "use_image_settings", "layout_method"].filter(key => external(node, key));
        if (linked.length) return fail(t.linked + linked.join(", "));
        if (widget(node, "use_image_settings")?.value) return fail(t.restore);
        if (widget(node, "layout_method")?.value === "moss_native") return fail(t.native);
        // Validate all targets before editing anything, including samplers supplied by the host.
        for (const [name, value] of Object.entries(preset.settings)) {
            const w = widget(node, name), choices = w?.options?.values;
            if (!w || (Array.isArray(choices) && !choices.includes(value)) ||
                (typeof value === "number" && (value < (w.options?.min ?? -Infinity) || value > (w.options?.max ?? Infinity)))) {
                return fail(t.missing + `${name} = ${value}`);
            }
        }
        node.graph?.beforeChange?.();
        node.rsMcPresetApplying = true;
        try {
            for (const [name, value] of Object.entries(preset.settings)) {
                const w = widget(node, name);
                w.value = value;
                w.callback?.call(w, value, app.canvas, node);
            }
            node.rsMcPresetApplied = true;
            node.rsMcPresetError = "";
        } finally {
            node.rsMcPresetApplying = false;
            node.graph?.afterChange?.();
            refresh(node);
        }
    }
    const created = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
        const result = created?.apply(this, arguments), node = this;
        if (widget(node, "rs_mc_preset")) return result;
        node.properties ??= {};
        // Append only: old positional widget values keep their original indexes.
        transient(node.addWidget("combo", "rs_mc_preset", words[locale()].choose, value => {
            const preset = presets.find(p => Object.values(p.label).includes(value));
            node.graph?.beforeChange?.();
            node.properties.rs_mc_preset = preset?.id ?? "";
            node.rsMcPresetApplied = false;
            node.rsMcPresetError = "";
            node.graph?.afterChange?.();
            refresh(node);
        }, { values: [] }));
        transient(node.addWidget("button", "rs_mc_apply_preset", null, () => apply(node)));
        const status = transient(ComfyWidgets.STRING(node, "rs_mc_preset_info", ["STRING", { multiline: true }], app).widget);
        status.inputEl.readOnly = true;
        status.computeSize = () => [320, 110];
        const names = new Set([...presets.flatMap(p => Object.keys(p.settings)), "use_image_settings", "layout_method"]);
        for (const w of node.widgets.filter(w => names.has(w.name))) {
            const callback = w.callback;
            w.callback = function () {
                const result = callback?.apply(this, arguments);
                if (!node.rsMcPresetApplying) {
                    node.rsMcPresetApplied = true;
                    node.rsMcPresetError = "";
                    refresh(node);
                }
                return result;
            };
        }
        refresh(node);
        return result;
    };
    for (const hook of ["onConfigure", "onConnectionsChange"]) {
        const previous = nodeType.prototype[hook];
        nodeType.prototype[hook] = function () {
            const result = previous?.apply(this, arguments);
            this.rsMcPresetApplied = true;
            this.rsMcPresetError = "";
            refresh(this); // Never reapply a preset on load, undo, or reconnection.
            return result;
        };
    }
}
