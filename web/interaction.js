// SPDX-License-Identifier: GPL-3.0-only
import { app } from "../../scripts/app.js";

// Preserve serialized values, sockets and widget order while hiding controls
// unused by fixed presets. A linked preset is resolved only by the backend.
function update(node) {
    const linked = node.inputs?.some(input => input.name === "preset" && input.link != null);
    const custom = linked || node.widgets?.find(w => w.name === "preset")?.value === "custom";
    for (const widget of node.widgets ?? []) {
        if (!["delay_steps", "decrement"].includes(widget.name)) continue;
        if (widget.type?.startsWith("converted-widget")) continue;
        if (!custom && !widget.rsMcInteractionVisible) {
            widget.rsMcInteractionVisible = {type: widget.type, hidden: widget.hidden, computeSize: widget.computeSize};
            widget.type = "rs-mc-interaction-hidden";
            widget.hidden = true;
            widget.computeSize = () => [0, -4];
            if (widget.inputEl) widget.inputEl.hidden = true;
        } else if (custom && widget.rsMcInteractionVisible) {
            if (widget.type === "rs-mc-interaction-hidden") Object.assign(widget, widget.rsMcInteractionVisible);
            delete widget.rsMcInteractionVisible;
            if (widget.inputEl) widget.inputEl.hidden = false;
        }
    }
    const size = node.computeSize();
    node.setSize([Math.max(node.size[0], size[0]), size[1]]);
    node.setDirtyCanvas(true, true);
}

app.registerExtension({
    name: "RS.MultiCharacter.Interaction",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "RSMultiCharacterInteraction") return;
        for (const hook of ["onNodeCreated", "onConfigure", "onConnectionsChange"]) {
            const previous = nodeType.prototype[hook];
            nodeType.prototype[hook] = function () {
                const result = previous?.apply(this, arguments);
                if (hook === "onNodeCreated") {
                    const widget = this.widgets?.find(w => w.name === "preset");
                    if (widget && !widget.rsMcInteractionCallback) {
                        widget.rsMcInteractionCallback = true;
                        const callback = widget.callback, node = this;
                        widget.callback = function (...args) {
                            const result = callback?.apply(this, args);
                            update(node);
                            return result;
                        };
                    }
                }
                update(this);
                return result;
            };
        }
    },
});
