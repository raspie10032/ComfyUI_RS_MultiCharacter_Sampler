# RS MultiCharacter Sampler

Regional generation and local detailing for ComfyUI. Give each character a prompt, an optional LoRA, and a point, box or mask to guide where their attributes appear.

[한국어](README.ko.md) · [日本語](README.ja.md) · [Documentation](docs/README.md) · [Changelog](CHANGELOG.md) · [Releases](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/releases) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md)

**Current release: [1.0.4 Hangeul](docs/release-1.0.4.md).** Runs with local models; no RS NovelAI extension or API key is required.

![Two-character Anima example without LoRA](examples/two-characters-result.png)

## What you can do

- Write a shared scene and separate character prompts, with up to **10 character/text regions**.
- Assign character LoRAs and edit placement with points, boxes, external masks or a numbered mask-painting canvas.
- Turn colored OpenPose PNG, JSON or `POSE_KEYPOINT` data into editable person masks.
- Detect and locally detail characters using their original prompts and matching LoRAs.
- Save PNG/WebP generation settings and restore them through the image loader.

Coordinates and masks guide prompt regions. Exact people counts, identity, poses and text spelling remain model-dependent. [Character image references](docs/image-reference.md) are also available as an **experimental, not recommended** option; prefer a matching character LoRA when available.

## Install or update

Find **RS MultiCharacter Sampler** in ComfyUI-Manager, or use the [Comfy Registry listing](https://registry.comfy.org/publishers/raspie10032/nodes/comfyui-rs-multicharacter-sampler). Package ID: `comfyui-rs-multicharacter-sampler`.

For Git installation, run this **inside `ComfyUI/custom_nodes`**:

```sh
git clone https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler.git
```

Update through Manager, or run `git pull --ff-only` inside an existing Git installation. **Restart ComfyUI and refresh the browser** after installing or updating. Keep one installation of this extension.

Python **3.11+**, Torch, NumPy and Pillow are required. Your ComfyUI core must natively support the selected model family. Supply the diffusion model, matching text encoder and VAE yourself. Missing `krea2` or `moss_image` choices in Load CLIP require a core/environment update. See [compatibility and tested versions](docs/compatibility.md).

Optional features have separate setup:

| Feature | Setup |
| --- | --- |
| Local detailer | Install **ComfyUI-Impact-Pack** and **ComfyUI-Impact-Subpack** through Manager, then install `requirements-detailer.txt` with ComfyUI's Python. SAM is optional. Selected missing detector/tagger catalog models download when executed. |
| Image references · experimental | Install `requirements-reference.txt` with ComfyUI's Python. Active references can download additional models; OFF/strength 0 loads none. [Backends and limits](docs/image-reference.md) |

## Start with a workflow

Load the [modular two-character Anima workflow](examples/modular/two-characters-anima.json), or choose your model in the table below. Use the UI JSON; files ending in `-api.json` are for API clients. The original [workflow PNG](examples/two-characters-workflow.png) can also be dropped onto the canvas.

1. Select the installed **MODEL, CLIP and VAE** in the loader nodes. For the Anima example, keep Load CLIP type `stable_diffusion`.
2. Connect STRING text nodes to **RS Character Prompt**, one character's appearance and action per numbered row. Write the scene, style and total person count in the sampler's common prompt; use its common negative prompt for exclusions.
3. Set **RS Character Position**. X/Y range from 0 to 1, with `(0, 0)` at the upper left. Match the same row numbers in Prompt, LoRA and Position.
4. Connect the building nodes to **RS Finalize Character Pipe**, then its `character_pipe` output to **RS MultiCharacter Sampler**. LoRA and Position are optional; the role nodes can be connected in any order before Finalize.
5. Choose **Model family preset → Apply preset**, check resolution and model-specific settings, then run. Presets copy sampling/regional values; choose models, LoRAs, prompts, layout, dimensions and seed separately.

Autosave writes to `output/RS_MultiCharacter/` as PNG, lossless WebP or lossy WebP. It stores generation information; use ComfyUI's ordinary **Save Image** if you also want the editing workflow embedded.

[Character building guide](docs/modular-characters.md) · [Preset values](docs/model-presets.md) · [Sampler/scheduler comparisons for Anima](docs/sampler-combinations.md)

## Models and examples

These are example starting points, not universal quality settings. FLUX variants have separate workflows and sampling requirements.

| Model family | Workflow | Starting point and scope |
| --- | --- | --- |
| **Anima** | [Two characters](examples/modular/two-characters-anima.json) | Main example; matching encoder and Qwen Image VAE. Default sampler pair: Euler ancestral / SGM uniform. |
| **SDXL / Illustrious** | [Two characters](examples/two-characters-sdxl.json) · [Character LoRA](examples/character-lora/illustrious.json) | Load Checkpoint supplies MODEL/CLIP/VAE. Basic example: 30 steps, CFG 5.5, Euler ancestral / normal. [Tested derivatives and limits](docs/sdxl-validation.md) |
| **FLUX.1 / 2 / 3** | [Model-specific workflows](examples/flux) | Includes Dev, Schnell and Klein variants. [Variant matrix and validation](docs/flux-validation.md) |
| **Krea 2 Turbo** | [Two characters](examples/two-characters-krea2.json) · [Character LoRA](examples/character-lora/krea2.json) | 8 steps, CFG 1, Euler / simple; Qwen3-VL 4B (`krea2`) + Qwen Image VAE. Common negative has no effect at CFG 1. |
| **MOSS-Image SFT** | [Base](examples/two-characters-moss.json) · [8-step LoRA](examples/moss-8step/two-cfg3.json) | Base: 50 steps, CFG 3, Euler / simple; Qwen3.5 9B (`moss_image`) + Flux2 VAE. [8-step setup](docs/moss-8step.md) requires a separate acceleration LoRA. |
| **SD1.5 · experimental, unstable** | [Two characters](examples/two-characters-sd15.json) | Execution tested; people count and attribute separation are unstable. [Trial and limits](docs/sd15-validation.md) |

Krea 2 and MOSS regional support is experimental. MOSS uses ordinary ComfyUI CFG, without the official pipeline's negative-branch layer-22 skipping. [Assets and validation](docs/krea-moss-validation.md)

## Character LoRAs and adapters

Choose each character's file and model/CLIP strengths in **RS Character LoRA**. A standard ComfyUI LoRA loader before the sampler applies a global LoRA. The checkpoint, adapter architecture and dimensions must match.

- **Precision** is the default: independent predictions for each LoRA setting, with factor-only optimization where supported.
- **Normal** shares layer calculations for supported Anima/SDXL linear LoRAs. Unsupported models/adapters automatically use Precision and report the reason. The modes can produce different character details.
- Supported static formats include **LoRA, LoCon/Tucker, DoRA, LoHa/DoHa, LoKr/DoKr, GLoRA, OFT/BOFT, IA³ and matching diff/set patches**. Packed INT8/FP8 paths include partial Q/K/V LoRA on MOSS. Complex adapters can cost more time and temporary memory.

**GGUF:** connect the MODEL output of the separately installed **ComfyUI-GGUF** loader. Regional LoRAs preserve packed weights; FLUX uses Precision, including automatic fallback from Normal. See [setup and verified scope](docs/gguf-compatibility.md).

**Native quantization:** packed FP8/INT8 regional LoRAs use the connected loader’s native operations across supported model families. Kernel availability and image quality depend on the quantized release, ComfyUI and GPU. See [formats, tests and limits](docs/quantization-compatibility.md).

**T-LoRA, GLoKr, other custom tensor types and shape-changing patches are outside the adapter path's supported scope.** Model/CLIP restrictions and numerical checks are documented in the [adapter format guide](docs/adapter-formats.md). See also [LoRA setup](docs/regional-lora.md), [mode comparisons](docs/shared-lora-experiment.md) and [tested character-LoRA combinations](docs/character-lora-matrix-20261021.md).

## Placement, masks and local detailing

Use **RS Character Position** to drag numbered points, boxes and masks. Use **RS Character Mask** for external MASK inputs, or **RS Character Mask Drawing** to paint over a display-only reference image. [Mask guide and examples](docs/character-masks.md)

For **two people plus a word**, use three slots: two `character` point regions and one `text` box region. Connect the literal word to the text row's STRING input and leave its LoRA at None. For an object, use a `character` box slot with an object description. Use `layout_method=regional`; MOSS native layout requires boxes for every region. [Mixed-layout examples](examples/epsilon) · [Object examples](examples/epsilon/objects) · [Layout guide](docs/regional-layout.md)

**RS OpenPose Masks (Experimental)** builds approximate person masks; it does not send a skeleton into the model. Optional body-part name guidance defaults OFF and supports Anima/SDXL. **RS Character Interaction** can delay separation decay outside overlapping regions on Anima/SDXL and experimental SD1.5. Exact joints and contact are not guaranteed. [Pose inputs, previews and limits](docs/openpose-mask-guides.md) · [Pose example](examples/openpose)

For local detailing, load the [generation + detailer workflow](examples/two-characters-detailer-anima.json). Connect the image, character pipe and same MODEL/CLIP/VAE to **RS MultiCharacter Detailer**, plus **RS Detection Combine Loader** and **RS Character Tagger Loader**. Start with face SEGM, WD ViT v3 and denoise **0.25**. Tagging selects an original character prompt; it does not append inferred tags. Check the reported character assignments. [Execution checks and limits](docs/detailer-validation.md)

## Restore generation settings

Open an original saved PNG/WebP in **RS MultiCharacter Load Image** and connect its character pipe to the sampler. Image prompts and characters replace the common prompt fields. Enable **use_image_settings** to also restore seed, dimensions and sampling/regional controls; disable it when applying a preset or using current widgets.

Model, LoRA, CLIP and VAE connections must be supplied explicitly. Metadata does not download or load those assets. Reference images must be reconnected. This is text-and-seed regeneration; the detailer separately performs masked img2img. NAI V4-style character captions can be imported, but their sampling settings cannot be replayed locally. [Metadata and restoration boundaries](docs/architecture.md)

## Node reference

The extension registers **15 nodes**. UI labels and contextual help follow ComfyUI's English, Korean, Japanese, Simplified Chinese or Traditional Chinese locale.

| Nodes | Purpose |
| --- | --- |
| RS Character Prompt / LoRA / Position / Finalize Character Pipe | Build numbered character settings and the final sampler/detailer pipe. |
| RS Character Mask / Mask Drawing | Connect external masks or paint numbered regions. |
| RS OpenPose Masks (Experimental) / Character Interaction | Build pose-derived masks and adjust overlap separation. |
| RS Image Reference (Experimental · Not Recommended) | Associate an image reference with a character number. |
| RS MultiCharacter Sampler / Load Image | Generate and restore saved settings. |
| RS MultiCharacter Detailer / Detection Combine Loader / Character Tagger Loader | Detect, match and locally correct characters. |
| RS MultiCharacter Prompts · legacy | Combined input retained for existing workflows. Use the modular nodes for new workflows. |

## Limits and troubleshooting

- One image per execution, up to 10 input slots. Dense layouts and crossing props can duplicate or omit people, mix attributes or form panels. A single character owns the full canvas; moving its only point does not move the person.
- The regional sampler uses a common negative prompt. Per-character negative captions and scheduled text conditioning are unsupported by the sampler.
- SD2, inpainting/refiner checkpoints, FLUX Fill/Control and external ControlNet/attention patches are unsupported by the regional sampler. The optional image-reference feature has its own documented backends and limits.
- The sampler accepts **2–100 steps and CFG 1–20**. Presets do not identify the connected model or guarantee quality. Model-specific workflows are the best starting point.
- Restoration requires the original image metadata and matching assets/runtime. Social platforms can strip metadata. Autosave does not retain unrelated EXIF/GPS/camera data.
- For errors, include the extension/core versions, exact checkpoint and LoRA versions, workflow JSON and full traceback in an [issue](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/issues).

[Documentation and validation index](docs/README.md) separates generation trials, numerical adapter tests and CPU/CI compatibility checks.

## Development and license

With Torch, NumPy and Pillow installed, run from the repository root:

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_ui.cjs
```

Set `RS_MC_TEST_COMFYUI` to a ComfyUI checkout for native integrations. The [CI workflow](.github/workflows/tests.yml) lists all twelve JavaScript UI suites and the core/OS matrix.

GPL-3.0-only. See [COPYING](COPYING), [third-party notices](THIRD_PARTY_NOTICES.md) and [source lineage](docs/source-lineage.json).
