# ComfyUI_RS_MultiCharacter_Sampler

**0.1.0-alpha1 · Anima alpha** — independent character prompts and X/Y prompt regions for local ComfyUI generation.

[한국어](README.ko.md) · [日本語](README.ja.md) · [Architecture](docs/architecture.md) · [Validation](docs/validation.md)

This extension contains six nodes. It does not require the RS NovelAI extension, an API key, or a ControlNet model. It uses your local Anima model and text encoder.

| Node | Purpose |
| --- | --- |
| **RS MultiCharacter Prompts** | 1–10 character slots, each with original text, enable switch and normalized X/Y. One dedicated `RS_MC_CHARACTER_PIPE` output. |
| **RS MultiCharacter Sampler** | Common positive/negative prompts, local sampling, optional autosave, image/latent/pipe/info outputs. |
| **RS MultiCharacter Load Image** | PNG/WebP image and mask, restored character pipe and generation information. |
| **RS MultiCharacter Detailer** | Detect regions, match original character prompts and locally correct masked crops. |
| **RS Detection Combine Loader** | SEGM / BBOX / SAM selection in one detector connection; SEGM takes priority. |
| **RS Character Tagger Loader** | Local tagger selection for automatic character matching, with download progress. |

## Install

Find **RS MultiCharacter Sampler (Anima Alpha)** in ComfyUI-Manager, or open the [Comfy Registry page](https://registry.comfy.org/publishers/raspie10032/nodes/comfyui-rs-multicharacter-sampler). Package ID: `comfyui-rs-multicharacter-sampler`. Restart ComfyUI after installation. If the new listing is not yet visible in your Manager cache, refresh its node list or use the Git installation below.

For Git installation, clone this repository into your ComfyUI `custom_nodes` directory, then restart ComfyUI. Use one installation method; do not install a second copy alongside an existing Git checkout.

```sh
git clone https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler.git
```

Run the command **inside `ComfyUI/custom_nodes`**. The sampler uses ComfyUI's existing PyTorch, NumPy and Pillow. Python 3.11+ and a ComfyUI version with Anima support are required; the tested environment is recorded in the validation report. Supply your own diffusion model, text encoder and VAE. The optional detector/tagger loaders download their selected missing catalog models when executed.

For detailing, install **ComfyUI-Impact-Pack** and **ComfyUI-Impact-Subpack** through Manager, then install `requirements-detailer.txt` using your **ComfyUI Python environment**. Restart ComfyUI. SAM is optional and must already be installed to select it. Additional tagger choices can require the optional dependencies listed in their error message.

## Local multi-character detailing

Load [the generation + detailer example](examples/two-characters-detailer-anima.json). Branch the same MODEL / CLIP / VAE (including your LoRA) to the sampler and **RS MultiCharacter Detailer**. Connect the sampler's `image` and `character_pipe` outputs to the detailer, then connect **RS Detection Combine Loader** and **RS Character Tagger Loader**. An existing image can instead supply `image` and `character_pipe` from **RS MultiCharacter Load Image**.

Start with the default face SEGM, WD ViT v3 and **denoise 0.25**. The basic view contains denoise, seed and autosave; expand the options for crop size, mask settings, matching thresholds and sampling. SEGM skips BBOX and SAM entirely. With SEGM OFF, choose BBOX alone or BBOX + SAM. OFF models are not loaded. Existing models in `ultralytics/segm`, `ultralytics/bbox` and `sams` appear when you refresh the model list.

The tagger only selects an original character prompt; inferred tags never enter the correction prompt. Hole filling and notch closing are enabled by default. Crops use the original image, with separate ownership masks and feathering inside those masks. Ambiguous regions are preserved and the report explains the reason. High-confidence misidentification is still possible; inspect the reported character assignments, especially when several characters look alike. The pipe has up to **10 characters**; the detailer processes up to **10 regions by default, 64 maximum**. More processed regions do not guarantee quality.

Detailer autosave keeps the original generation settings and adds a separate correction history in PNG/WebP metadata. It does not embed a workflow. PNG/lossless WebP preserve pixels outside the applied mask; lossy WebP can change pixels through compression. Current live validation is Anima; support for other model families is not established. See [detailer validation](docs/detailer-validation.md).


## First workflow

Drop the original [workflow PNG](examples/two-characters-workflow.png) onto the ComfyUI canvas, or load [examples/two-characters-anima.json](examples/two-characters-anima.json). The shared PNG contains ComfyUI `workflow` and `prompt` metadata; the sampler's normal autosave behavior is unchanged. The separate `-api.json` file is for API clients.

1. Select your Anima diffusion model in **Load Diffusion Model**, its text encoder in **Load CLIP**, and its VAE in **Load VAE**. The example uses `anima-base-v1.0.safetensors`, `qwen_3_06b_base.safetensors` and `qwen_image_vae.safetensors`. Select the names actually installed on your machine. Use the example's CLIP type `stable_diffusion`.
2. Write the overall scene/style and total person count in the sampler's common prompt. Write one character's appearance/action in each character slot; the tested prompts use `1girl` or `1boy` per slot.
3. Set X/Y from 0 to 1. `(0, 0)` is the upper left. Equal centers spread in slot order from left to right. Lower `character_count` excludes hidden slots even if their old text remains saved.
4. Keep the alpha defaults for a first run: **30 steps, CFG 4, Euler ancestral, SGM uniform, 1536×768**. The seed's ComfyUI control can randomize between runs.
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

Some CFG++ variants degraded at the fixed test settings. Lower-CFG/fewer-step retests have **not** been performed, so this does not establish incompatibility. The regional sampler still uses **30 fixed steps and CFG 1–20**; it does not yet provide recommendations below that CFG range or at other step counts. See [matrix results and recommendation evidence](docs/sampler-combinations.md).

## Restore from an image

Select an original saved image in **RS MultiCharacter Load Image** and connect its `character_pipe` to the sampler. Image prompts and characters replace the sampler's common prompt fields. Enable **use_image_settings** to also restore seed, dimensions, CFG, sampling and region settings; leave it disabled to use the sampler widgets for those values.

**Model/LoRA/CLIP/VAE connections remain explicit.** File names and strengths are recorded in `generation_info` and metadata, but the loader does not load or download them. Reproduction requires the same assets and compatible runtime. This path regenerates from text and seed; it is not img2img.

The loader also accepts NAI V4-style character captions with one center per character. Select NovelAI prompt syntax for text typed in that syntax; imported NAI images select it automatically. NAI settings cannot be replayed as local settings: keep `use_image_settings` off for those images.

## Alpha limits

- **Anima only**, one image per execution. The sampler is text-to-image; the detailer runs masked img2img crops. SDXL/Flux/SD1.5, ControlNet and other attention patches are not supported.
- **1–10 input slots; actual image tests cover 1–6.** More characters do not guarantee quality. Horizontal layouts are the strongest tested use case.
- Coordinates choose prompt regions; they do **not** lock a head/body to a point or enforce exactly one person per region. A single character owns the whole image, so moving that one center does not move the person.
- Multiple rows, dense interactions and crossing props can duplicate or omit people. Four requested people in a 2×2 experiment became 12 and 10. Six people in two rows became 7 and 11. Do not treat count or identity as guaranteed.
- Per-character negative captions are preserved in metadata but **rejected by the regional sampler** in this alpha. Use its common negative prompt. The detailer can use the matched character's negative caption. Scheduled text conditioning is not supported.
- The regional sampler schedule is currently fixed to **30 steps**. The detailer has its own adjustable step count. Initial common weight, character gain and boundary release are advanced experimental controls, not universal quality settings.
- Autosave does not preserve an uploaded image's unrelated EXIF/GPS/camera data. Social platforms may strip generation metadata; use the original file for restoration.

See [validation](docs/validation.md) for real generation, metadata replay and the limits of the evidence. This is an alpha, not a claim of NovelAI-equivalent performance.

## Development

From this directory, using an environment containing Torch, NumPy and Pillow:

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_ui.cjs
```

License: GPL-3.0-only. See [COPYING](COPYING), [third-party notices](THIRD_PARTY_NOTICES.md) and [source lineage](docs/source-lineage.json).
