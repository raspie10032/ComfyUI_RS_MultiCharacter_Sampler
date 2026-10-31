# RS Workspace — local experimental app screen

Open ComfyUI and click **RS Workspace** at the bottom right. The app creates its
own workflow tab when opened from a normal user workflow. Existing workflows
are preserved. Click **노드 그래프** to return to the editable graph.

Select an installed model. The app inspects safetensors headers, selects the
matching checkpoint or split-model loaders, and connects existing public RS
nodes. Missing encoder/VAE files and unsupported feature combinations block
generation with an explanation. The app does not download a base checkpoint.

## Controls

- **캐릭터:** numbered STRING prompts, character/text choice, per-character
  LoRA and image references. Inactive slots remain saved but do not execute.
- **배치 / 마스크:** the existing point/box/mask editor and drawing canvas.
  Enable drawing and paint a numbered region before generating.
- **3D 포즈:** the existing image-to-3D/scene editor. Anima 2B uses LLLite;
  Krea2 and MOSS use the scene adapters. Other supported families, including
  Anima 2.9B, use the rendered region masks without a pose adapter. The status
  panel explicitly distinguishes these routes. The editor requires WebGL2.
- **카메라:** the existing shared camera editor and interaction controls.
- **생성 / 보정:** common prompts, sampling settings, progressive resolution,
  global LoRA, detection and face detail settings. Multiple characters
  automatically connect the WD tagger required for prompt matching.
- **결과:** execution previews, saved outputs and error messages.

Scene, masks and prompts stay in the workflow. Model-specific sampler, LoRA,
pose, detector, tagger and detail settings are remembered separately. Generation
uses the selected output's dependency graph; stale loaders and hidden reference
slots are excluded. Save with **워크플로 저장** and reopen through ComfyUI's
usual workflow loader. App metadata is stored in `extra.rs_workspace`; public
nodes and widgets remain the execution source of truth.

## Current boundaries

This is a development prototype, not a released replacement for ComfyUI App
Mode. The catalog currently recognizes installed safetensors models from the
supported Anima, SDXL, SD1.5, FLUX1/2/3, Krea2 and MOSS families. It does not
classify arbitrary renamed text encoders or expose a GGUF loader in this screen.

Krea2/MOSS scene adapters cannot currently run together with image references
or progressive resolution. FLUX1 checkpoints need a supported Kontext path for
image references; the app blocks an unsupported combination. Anima 2.9B does
not accept the 2B Role K/V weights. These boundaries come from the existing
generation paths and are displayed before execution.

Graph routing checks do not prove image quality or every combination. See the
local validation report for the tested files and actual execution evidence.
