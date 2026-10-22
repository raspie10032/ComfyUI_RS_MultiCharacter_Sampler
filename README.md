# ComfyUI_RS_MultiCharacter_Sampler

**1.0.0 Hangeul (한글):** adds editable person masks from OpenPose JSON, adjustable thickness, and overlap separation presets. Optional body-part name guidance is **very weak attention guidance using the names of skeleton parts**, OFF by default; it does not feed a skeleton into the model. [Usage and limits](docs/openpose-mask-guides.md) · [Release and validation](docs/release-1.0.0.md).

**0.2.6 Bieup (비읍) — LoRA bug fixes:** fixes character-LoRA `weight_scale` errors on Krea 2 FP8 and MOSS INT8; adds Krea2/Illustrious character-LoRA presets and reproduction examples. Full-precision MOSS retains its existing path. [Release notes](docs/release-0.2.6.md) · [Generation checks across nine model configurations and limits](docs/character-lora-matrix-20261021.md).

**0.2.5 Mieum (미음): experimental image references — supported, NOT RECOMMENDED.** Optional per-character IMAGE input reuses point/box/mask placement across Anima, SD1.5, SDXL/Illustrious, FLUX.1/2/3, Krea 2 and MOSS. Quality varies, with weak outfit fidelity/oversaturation in SDXL. Prefer a character LoRA when available. Disabled/strength 0 loads no reference weights. [Usage and limits](docs/image-reference.md) · [Release notes](docs/release-0.2.5.md) · [Experiment report (Release attachments; excluded from git clone)](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/releases/tag/v0.2.5).

**New in 0.2.4 Rieul (리을):** paint numbered character regions over a reference image with **RS Character Mask Drawing**, or connect external MASKs with **RS Character Mask**. Select a numbered point, box or mask above Position’s layout guide, then drag to move and resize boxes or masks. Includes uniform mask scaling, margin, undo, placement reset and PNG/WebP mask restoration. Canvas overflow is clipped while preserving the source shape. Reference images are display-only; masks guide regional attention and do not guarantee pose or people count. [Usage](docs/character-masks.md) · [Examples](examples/character-masks) · [Release notes and validation scope](docs/release-0.2.4.md).

**New in 0.2.3 Digeut (디귿):** choose Normal or Precision on the character LoRA node. Supported Anima/SDXL linear LoRAs share layer calculations in Normal; Precision retains independent predictions with low-rank optimization where supported. Adds localized selection panels and short tooltips after a two-second hover. [Release notes](docs/release-0.2.3.md) · [Comparisons and limits](docs/shared-lora-experiment.md).

**New in 0.2.2 Nieun (니은):** native FLUX.1/2/3 regional generation and local masked detailing. All eight tested variants completed two-person generation, same-seed caption swaps and detailing. Includes quantized regional LoRA fixes, embedded guidance, settings replay, eight FLUX presets and model-specific examples. [Release notes](docs/release-0.2.2.md) · [Evidence and limits](docs/flux-validation.md) · [FLUX examples](examples/flux).

**1.0.0 Hangeul (한글) · FLUX.1/2/3 · Anima · SDXL · Krea 2 · MOSS · SD1.5 (experimental, unstable)** — independent prompts with X/Y, box and mixed regions for local ComfyUI generation.

**Giyeok Fix:** fixes character and text inputs appearing together. Each slot now uses one shared STRING socket, preserving its connection when kind changes. Old workflows move their literal-text connection to that socket. [Fix and compatibility](docs/release-0.2.1.md).

**New in Giyeok:** separate Character Prompt, Character LoRA, Character Position and Finalize Character Pipe nodes. Each role shows all active rows together; connect the three roles in any order. Positive prompts use STRING connections, with no individual UC input. Position and Finalize show layout guides. [Changes and validation scope](docs/release-0.2.0.md) · [Usage](docs/modular-characters.md).

Each slot uses **one STRING**: a character prompt or the literal words to draw, selected by kind. Changing kind keeps the same connection.

**Zeta Fix:** fixes Anima character LoRAs silently missing the actual inference model with ComfyUI dynamic VRAM. Update and restart ComfyUI; existing LoRA selections and strengths can be reused. [Fix, controlled image comparisons and validation scope](docs/release-0.1.7.md).

**New in Zeta:** choose a LoRA and model/CLIP strengths for each character. The sampler blends masked predictions through native ComfyUI hooks; the detailer uses the matched character's LoRA. [Usage, cost and limits](docs/regional-lora.md).

**LoRA application mode:** `normal` shares layer calculations for supported Anima/SDXL linear adapters; `precision` keeps independent predictions per LoRA setting with low-rank optimization where supported. Precision is the compatibility default, not a guarantee of better artwork. Normal may change character details; unsupported models/adapters use precision and report the reason. [Modes, comparisons and limitations](docs/shared-lora-experiment.md).

[0.1.6 release notes and validation scope](docs/release-0.1.6.md).

**New in Epsilon:** mixed point/box layouts, literal text regions, eight editable model-family presets, MOSS native layout mode, and two-person object-box examples for Anima and Krea 2. See [release notes and validation scope](docs/release-0.1.5.md).

[한국어](README.ko.md) · [日本語](README.ja.md) · [Architecture](docs/architecture.md) · [Validation](docs/validation.md)

This extension registers twelve nodes, including the Mask and Mask Drawing nodes, four original modular character-building nodes and the legacy combined prompt node. It does not require the RS NovelAI extension, an API key, or a ControlNet model. It uses your supported local model and matching text encoder.

| Node | Purpose |
| --- | --- |
| **RS Character Prompt / LoRA / Position / Finalize Character Pipe** | Four role-based nodes; connect prompt, LoRA and position in any order, then finalize the dedicated pipe. |
| **RS Character Image Reference · Experimental** | Bind an IMAGE to one numbered character. Supported but not recommended; optional dependencies/models. |
| **RS Character Mask / Mask Drawing** | External MASK input or numbered painting over a reference; preview and edit shape placement. |
| **RS MultiCharacter Prompts** | 1–10 regions with original text, enable switch, normalized X/Y and optional boxes or literal text. One dedicated `RS_MC_CHARACTER_PIPE` output. |
| **RS MultiCharacter Sampler** | Common positive/negative prompts, local sampling, optional autosave, image/latent/pipe/info outputs. |
| **RS MultiCharacter Load Image** | PNG/WebP image and mask, restored character pipe and generation information. |
| **RS MultiCharacter Detailer** | Detect regions, match original character prompts and locally correct masked crops. |
| **RS Detection Combine Loader** | SEGM / BBOX / SAM selection in one detector connection; SEGM takes priority. |
| **RS Character Tagger Loader** | Local tagger selection for automatic character matching, with download progress. |

**Epsilon layouts:** optional boxes and mixed point/box layouts, text regions, and MOSS native layout comparison. [Setup and limitations](docs/regional-layout.md).

Mixed-layout examples now include **Anima, Illustrious XL, Krea 2 Turbo and experimental SD1.5**, with model-specific conditioning and prompts. Anima's initial example has been retuned for a shared campus background and an unclipped title. [Settings, comparisons and limits](docs/mixed-layout-tuning.md). Text spelling and person count remain model-dependent; these settings do not automatically replace existing workflow values.

The SD1.5 example checks **two distinguishable people and visible lettering in the requested area**. Natural image quality and exact spelling are outside that compatibility criterion.

To try **two people plus one word**, use region count `3`, `layout_mode=mixed`, point geometry for character slots 1–2, and `kind=text` with literal `HELLO` for slot 3. Set its X/Y and width/height, then select sampler `layout_method=regional`. [Runnable examples](examples/epsilon) · [Validation and visual limitations](docs/epsilon-validation.md). Up to 10 total character/text regions; MOSS native mode requires boxes for every region.

**Two people plus one object:** use the existing **Anima — mixed** or **Krea 2 Turbo** preset with the [20 object workflows](examples/epsilon/objects). Slot 3 uses `character` + `box` with an object description. The ten-object trial preserved two people and recognizable objects in all 20 images, but exact bounds and scene coherence varied. Object slots are not automatically excluded from face detailing. [Images, settings and limits](docs/object-layout-validation.md).

## Modular character input

Use separate **all-prompts, all-LoRAs, and all-positions** nodes. Each role shows **rows 1–N together**, with matching row numbers identifying characters. **Connect these roles in any order**, then finish with **Finalize Character Pipe** for Sampler or Detailer. Positive prompts use external **STRING connections** with no character UC field. Position and Finalize show a layout guide. [Usage in English / 한국어 / 日本語](docs/modular-characters.md) · [Two-character example](examples/modular/two-characters-anima.json). The old all-in-one node remains deprecated for saved workflows.

The main nodes include **inline help for the current selections**: character/text slots, XY/box placement, image setting restoration, save formats, tagging and detection. Panels follow ComfyUI's English, Korean or Japanese locale and are excluded from workflow inputs. Connected control values are resolved at execution; panels describe the node's local selections.

Hover over a control for **2 seconds** to see a short tooltip. Dragging or scrolling dismisses it. Other extensions keep their own tooltip timing, and disabling tooltips in ComfyUI also disables these hints.

## Install

Find **RS MultiCharacter Sampler** in ComfyUI-Manager, or open the [Comfy Registry page](https://registry.comfy.org/publishers/raspie10032/nodes/comfyui-rs-multicharacter-sampler). Package ID: `comfyui-rs-multicharacter-sampler`. Restart ComfyUI after installation. If the new listing is not yet visible in your Manager cache, refresh its node list or use the Git installation below.

For Git installation, clone this repository into your ComfyUI `custom_nodes` directory, then restart ComfyUI. Use one installation method; do not install a second copy alongside an existing Git checkout.

```sh
git clone https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler.git
```

Run the command **inside `ComfyUI/custom_nodes`**. The sampler uses ComfyUI's existing PyTorch, NumPy and Pillow. Python 3.11+ and a ComfyUI version supporting your chosen model are required; the tested environment is recorded in the validation report. Supply your own diffusion model, text encoder and VAE. The optional detector/tagger loaders download their selected missing catalog models when executed.

For detailing, install **ComfyUI-Impact-Pack** and **ComfyUI-Impact-Subpack** through Manager, then install `requirements-detailer.txt` using your **ComfyUI Python environment**. Restart ComfyUI. SAM is optional and must already be installed to select it. Additional tagger choices can require the optional dependencies listed in their error message.

## SD1.5 — experimental, unstable

Ordinary SD1.5 checkpoints can run through the existing sampler. **Character counts and attribute separation are unstable.** The base checkpoint completed four two-character requests; two images contained three people, with some hair/clothing attributes mixed or omitted. This is limited execution evidence, not a success-rate estimate or validation of SD1.5 fine-tunes. See the [trial settings and scope](docs/sd15-validation.md) and [workflow](examples/two-characters-sd15.json).

## Experimental SDXL generation

Load the [two-character SDXL workflow](examples/two-characters-sdxl.json), then select your checkpoint in **Load Checkpoint**. Branch its MODEL / CLIP / VAE outputs into the existing sampler. Illustrious XL v1.0 and NoobAI XL epsilon-pred 1.1 were tested with real generation and prompt-position swaps. This does not establish compatibility across all SDXL derivatives or sampler combinations.

The example starts at **30 steps, CFG 5.5, Euler ancestral + normal**, initial common prior **0.3**, character gain **1.3**, spatial separation **0.5**. Existing Anima defaults stay unchanged. Its 0.05 / 1.7 / 0.9 settings can cause visible panel boundaries on SDXL.

XY routes prompts, not exact body positions or guaranteed counts. Multiple characters and grid layouts can duplicate people, mix attributes or create panels. SDXL Refiner, inpainting models, ControlNet and other attention patches are unsupported. PNG/WebP metadata identifies the SDXL engine and restores through Load Image. See [method and live results](docs/sdxl-validation.md).


## Experimental Krea 2 / MOSS-Image support

Use a current ComfyUI with native support for both models. If `Load CLIP` lacks `krea2` or `moss_image`, update ComfyUI and its environment dependencies first. Choosing a model does not automatically change sampling settings.

| Model | Example | Text encoder / VAE | Starting settings |
| --- | --- | --- | --- |
| Krea 2 Turbo | [Two characters](examples/two-characters-krea2.json) | Qwen3-VL 4B, `krea2` / Qwen Image VAE | 8 steps · CFG 1 · Euler + simple |
| MOSS-Image SFT | [Two characters](examples/two-characters-moss.json) | Qwen3.5 9B, `moss_image` / Flux2 VAE | 50 steps · CFG 3 · Euler + simple |

Connect MODEL, CLIP, VAE and the existing character pipe. Write the scene in the common prompt and each character's appearance and action in natural-language sentences. At Krea 2 Turbo's CFG 1, the common negative has no effect. The MOSS example uses ordinary ComfyUI CFG; it does not apply the official pipeline's negative-branch layer-22 skipping.

The sampler accepts **2–100 steps**; Anima/SDXL retain their 30-step defaults. XY selects prompt regions and does not guarantee exact counts, poses or complex interactions. This support covers T2I. Reference-image editing and detailer quality on these new models have not been validated. See [model files, terms and validation scope](docs/krea-moss-validation.md).


## MOSS 8-step LoRA

Use the [two-character](examples/moss-8step/two-cfg3.json) or [four-character XY](examples/moss-8step/four-xy-cfg3.json) workflow with **LoRA 0.7 · 8 steps · CFG 3 · Euler / simple**. Download `lora_latest.safetensors` from [lodestones/MOSS-Image-SFT-8-steps-dmd](https://huggingface.co/lodestones/MOSS-Image-SFT-8-steps-dmd) into `ComfyUI/models/loras/`, refresh the model list, then select the downloaded filename in **Load LoRA (Model Only)**. Connect `Load Diffusion Model → Load LoRA (Model Only) → RS MultiCharacter Sampler`; CLIP and VAE keep their normal connections.

Use MOSS-Image SFT, a Qwen3.5 9B encoder (`Load CLIP` type `moss_image`), and Flux2 VAE. **Updating this extension alone does not add MOSS to an older ComfyUI core.** Update the core and its Python dependencies, then restart. ComfyUI 0.41.0 was used for the LoRA trial.

CFG 3 gave clearer character attributes in the two tested scenes; CFG 1 was faster but weakened some colors. Eight steps at CFG 3 used 16 model evaluations; CFG 1 used 8. Neither setting guarantees counts or props. [CFG 1 workflows, exact assets, comparisons and limits](docs/moss-8step.md).

## Local multi-character detailing

Load [the generation + detailer example](examples/two-characters-detailer-anima.json). Branch the same MODEL / CLIP / VAE (including your LoRA) to the sampler and **RS MultiCharacter Detailer**. Connect the sampler's `image` and `character_pipe` outputs to the detailer, then connect **RS Detection Combine Loader** and **RS Character Tagger Loader**. An existing image can instead supply `image` and `character_pipe` from **RS MultiCharacter Load Image**.

Start with the default face SEGM, WD ViT v3 and **denoise 0.25**. The basic view contains denoise, seed and autosave; expand the options for crop size, mask settings, matching thresholds and sampling. SEGM skips BBOX and SAM entirely. With SEGM OFF, choose BBOX alone or BBOX + SAM. OFF models are not loaded. Existing models in `ultralytics/segm`, `ultralytics/bbox` and `sams` appear when you refresh the model list.

The tagger only selects an original character prompt; inferred tags never enter the correction prompt. Hole filling and notch closing are enabled by default. Crops use the original image, with separate ownership masks and feathering inside those masks. Ambiguous regions are preserved and the report explains the reason. High-confidence misidentification is still possible; inspect the reported character assignments, especially when several characters look alike. The pipe has up to **10 characters**; the detailer processes up to **10 regions by default, 64 maximum**. More processed regions do not guarantee quality.

Detailer autosave keeps the original generation settings and adds a separate correction history in PNG/WebP metadata. It does not embed a workflow. PNG/lossless WebP preserve pixels outside the applied mask; lossy WebP can change pixels through compression. Anima has the broader validation set. SDXL (Illustrious XL v1.0), Krea 2 Turbo and MOSS-Image SFT each also completed one two-face detailer run; these are basic execution checks, not quality or success-rate comparisons. See [detailer validation](docs/detailer-validation.md).


## First workflow

Drop the original [workflow PNG](examples/two-characters-workflow.png) onto the ComfyUI canvas, or load [examples/two-characters-anima.json](examples/two-characters-anima.json). The shared PNG contains ComfyUI `workflow` and `prompt` metadata; the sampler's normal autosave behavior is unchanged. The separate `-api.json` file is for API clients.

1. Select your Anima diffusion model in **Load Diffusion Model**, its text encoder in **Load CLIP**, and its VAE in **Load VAE**. The example uses `anima-base-v1.0.safetensors`, `qwen_3_06b_base.safetensors` and `qwen_image_vae.safetensors`. Select the names actually installed on your machine. Use the example's CLIP type `stable_diffusion`.
2. Write the overall scene/style and total person count in the sampler's common prompt. Write one character's appearance/action in each character slot; the tested prompts use `1girl` or `1boy` per slot.
3. Set X/Y from 0 to 1. `(0, 0)` is the upper left. Equal centers spread in slot order from left to right. Lower `character_count` excludes hidden slots even if their old text remains saved.
4. Select **Model family preset → Apply preset** on the sampler to copy the tested starting values for Anima, SDXL/Illustrious, Krea 2 Turbo, MOSS base/8-step LoRA or experimental SD1.5. Anima and SDXL have separate XY and mixed choices. You can edit every value afterward. Models, prompts, layout, dimensions and seed remain your choices. [Preset values and usage](docs/model-presets.md)
5. Run. Autosave writes to `output/RS_MultiCharacter/`. Choose PNG, lossless WebP or lossy WebP. Standard model LoRAs can be connected before the sampler with ComfyUI's LoRA loader.

The `IMAGE` output can also go to ComfyUI's ordinary Save Image node. The sampler's own autosave stores generation metadata, **not a ComfyUI workflow**. Use ordinary Save Image if you need workflow embedding.

![Two-character example without LoRA](examples/two-characters-result.png)

Actual output from the bundled API example, without the private style LoRA.

## Sampler and scheduler choices

**Every sampler and scheduler registered in your ComfyUI installation is selectable.** Start with the default pair below, or try the two alternatives. The dropdown tooltips also list these starting points.

| Starting point | Sampler | Scheduler | Observation in this trial |
| --- | --- | --- | --- |
| Default | `euler_ancestral` | `sgm_uniform` | Clear character features and shared background |
| Alternative composition | `euler` | `linear_quadratic` | Preserved features and followed the requested face-to-face seating |
| Clear alternative | `dpmpp_2m_sde_gpu` | `beta` | Distinct hair, outfits and cups; seated side by side instead of opposite |

These observations come from **Anima Base v1.0, one two-character cafe scene and seed, 1536×768, 30 steps, CFG 4, no LoRA**. All 45×9=405 combinations completed generation; several produced severely degraded images. These are starting points, not a ranking or success rate across prompts.

Select both fields yourself. Other combinations remain available, and the node never substitutes a recommended choice. Native option names are preserved for workflows and image metadata. Defaults remain `euler_ancestral + sgm_uniform`; the available inventory depends on your ComfyUI version.

Some CFG++ variants degraded at the fixed test settings. Lower-CFG/fewer-step retests have **not** been performed, so this does not establish incompatibility. The sampler accepts **2–100 steps and CFG 1–20**. The Anima recommendations still refer to the original 30-step comparison; lower-CFG/fewer-step CFG++ recovery is untested. See [matrix results and recommendation evidence](docs/sampler-combinations.md).

## Restore from an image

Select an original saved image in **RS MultiCharacter Load Image** and connect its `character_pipe` to the sampler. Image prompts and characters replace the sampler's common prompt fields. Enable **use_image_settings** to also restore seed, dimensions, CFG, sampling and region settings; leave it disabled to use the sampler widgets for those values.

**Model/LoRA/CLIP/VAE connections remain explicit.** File names and strengths are recorded in `generation_info` and metadata, but the loader does not load or download them. Reproduction requires the same assets and compatible runtime. This path regenerates from text and seed; it is not img2img.

The loader also accepts NAI V4-style character captions with one center per character. Select NovelAI prompt syntax for text typed in that syntax; imported NAI images select it automatically. NAI settings cannot be replayed as local settings: keep `use_image_settings` off for those images.

## Current limits

- **Anima, SDXL, Krea 2, MOSS and unstable experimental SD1.5 support**, plus native FLUX.1/2/3, one image per execution. The sampler is text-to-image; the detailer runs masked img2img crops. SD1.5 has only been tested for generation, not detailing. SD2, FLUX Fill/Control/reference-image editing, inpainting/refiner checkpoints, ControlNet and other attention patches are not supported by the regional sampler.
- **1–10 input slots.** Actual image tests cover Anima 1–6, SDXL 2–6, Krea 2 / MOSS 2–4, and SD1.5 two-character requests. More characters do not guarantee quality. Horizontal layouts are the strongest tested use case; successful new-model 2x2 examples do not establish a general success rate.
- Coordinates choose prompt regions; they do **not** lock a head/body to a point or enforce exactly one person per region. A single character owns the whole image, so moving that one center does not move the person.
- Multiple rows, dense interactions and crossing props can duplicate or omit people. Four requested people in a 2×2 experiment became 12 and 10. Six people in two rows became 7 and 11. Do not treat count or identity as guaranteed.
- Per-character negative captions are preserved in metadata but **rejected by the regional sampler** in this release. Use its common negative prompt. The detailer can use the matched character's negative caption. Scheduled text conditioning is not supported.
- The regional sampler accepts **2–100 steps**, with 30 as the Anima/SDXL default. The detailer has its own adjustable step count. Initial common weight, character gain and boundary release are advanced experimental controls, not universal quality settings.
- Autosave does not preserve an uploaded image's unrelated EXIF/GPS/camera data. Social platforms may strip generation metadata; use the original file for restoration.

See [validation](docs/validation.md) for real generation, metadata replay and the limits of the evidence. This release retains the documented count, identity and interaction limits.

## Development

From this directory, using an environment containing Torch, NumPy and Pillow:

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_ui.cjs
node tests/test_detailer_ui.cjs
node tests/test_boxes_ui.cjs
node tests/test_presets_ui.cjs
```

License: GPL-3.0-only. See [COPYING](COPYING), [third-party notices](THIRD_PARTY_NOTICES.md) and [source lineage](docs/source-lineage.json).

## ComfyUI compatibility

SDXL does not require Anima, Krea 2 or MOSS to exist in ComfyUI. Each newer architecture still requires a ComfyUI checkout with native support for that model. SD1.5 also passed native CPU integration at all three snapshots below; see [its limited real-generation results](docs/sd15-validation.md). The earlier compatibility audit’s CPU API integration tests cover ComfyUI `v0.3.76` (SDXL), `15eb748` (Anima/SDXL/Krea 2) and `5cc4b87` (all four families). These are tested snapshots, not a guarantee for every intervening version or third-party model patch. The [compatibility report](docs/compatibility.md) separates real generation, small native model tests and Windows CPU CI.
