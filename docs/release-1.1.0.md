# 1.1.0 Hangeul — RS Workspace app screen

RS Workspace adds an experimental app screen inside ComfyUI. Select an installed model, edit characters and placement, and generate through the existing RS nodes. The app selects the model's loaders, starting settings and supported feature routes; prompts, masks and 3D scenes survive model changes. Existing node workflows remain available.

## Install and open

1. Update **RS MultiCharacter Sampler** to **1.1.0** with ComfyUI-Manager, or run `git pull --ff-only` in its Git installation.
2. **Restart ComfyUI**, open its usual browser URL, and hard-refresh with **Ctrl+Shift+R** (macOS: **Cmd+Shift+R**).
3. Click **RS Workspace** at the **bottom right**. The alternative extension command is **Edit → RS Model Workspace (Experimental)** when exposed by the frontend.
4. Select an installed model, set characters and placement, then click **생성** (Generate). Use **노드 그래프** (Node graph) to return to the underlying workflow.

No separate app installation is required. Keep one installation of this extension. Base models, encoders and VAEs are installed separately. [English opening/troubleshooting guide](app-workspace.md) · [한국어 전체 사용 가이드](app-workspace.ko.md).

## Included controls

- Character/text slots, per-character and global LoRAs, and model-specific sampling settings.
- Existing point/box/mask editors, 3D pose editor and image-to-3D import, camera and interaction controls.
- Model-specific reference and pose routes; unsupported combinations are reported before queuing.
- Progressive sampling, face detailing with automatic multi-character tagger connection, progress and results.
- Wildcard TXT discovery, file search/insertion, seeded preview and prompt expansion. Saved PNGs retain resolved prompts and source templates for restoration.
- Separate workflow tabs, per-model settings recovery and editable workflow download.
- Reopening the app preserves a user-customized output filename prefix.

The release assets include a workflow PNG and **RS-Workspace-Wildcard-Example.zip**. The ZIP contains the PNG, a small background TXT and setup instructions; models and personal wildcard collections are not bundled.

## Validation and limits

[Validation details](app-workspace-validation.md) distinguish source checks, real ComfyUI generation and actual browser use. The screen currently uses Korean labels; the English guide maps the main controls. One Generate click queues one request. GGUF inventory and arbitrary encoder-name matching are not supported by the app catalog. SD1.5 remains unstable. Krea 2/MOSS pose plus references or progressive sampling remains unsupported; Anima 2.9B uses pose masks without the 2B pose adapter. This release does not claim every feature combination has been visually verified on every model.
