// SPDX-License-Identifier: GPL-3.0-only
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "RS.MultiCharacter.MetadataNotice",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "RSMultiCharacterLoadImage") return;
        const refresh = async node => {
            const file = node.widgets?.find(w => w.name === "image")?.value;
            const request = node._rsMetadataRequest = (node._rsMetadataRequest ?? 0) + 1;
            node._rsMetadataNotice = null;
            if (typeof file !== "string" || !file) return;
            try {
                const response = await api.fetchApi(`/rs_mc/metadata_notice?image=${encodeURIComponent(file)}`);
                const data = response.ok ? await response.json() : null;
                if (node._rsMetadataRequest !== request) return;
                node._rsMetadataNotice = data?.truncated ? data : null;
            } catch {
                if (node._rsMetadataRequest !== request) return;
                node._rsMetadataNotice = null;
            }
            if (node.computeSize && node.setSize) {
                const size = node.computeSize();
                node.setSize([Math.max(node.size?.[0] ?? 0, size[0]), size[1]]);
            }
            node.setDirtyCanvas?.(true, true);
        };
        const created = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function (...args) {
            const result = created?.apply(this, args);
            const widget = this.widgets?.find(w => w.name === "image");
            if (widget) {
                const callback = widget.callback;
                const node = this;
                widget.callback = function (...args) {
                    const result = callback?.apply(this, args);
                    void refresh(node);
                    return result;
                };
            }
            void refresh(this);
            return result;
        };
        const configured = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (...args) {
            const result = configured?.apply(this, args);
            void refresh(this);
            return result;
        };
        const removed = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function (...args) {
            this._rsMetadataRequest = (this._rsMetadataRequest ?? 0) + 1;
            return removed?.apply(this, args);
        };
    },
});
