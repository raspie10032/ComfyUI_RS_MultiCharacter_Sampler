# ComfyUI_RS_MultiCharacter_Sampler

**0.1.0-alpha1 · Anima alpha** — independent character prompts and X/Y prompt regions for local ComfyUI generation.

[한국어](README.ko.md) · [日本語](README.ja.md) · [Architecture](docs/architecture.md) · [Validation](docs/validation.md)

This extension contains three nodes. It does not require the RS NovelAI extension, an API key, or a ControlNet model. It uses your local Anima model and text encoder.

| Node | Purpose |
| --- | --- |
| **RS MultiCharacter Prompts** | 1–10 character slots, each with original text, enable switch and normalized X/Y. One dedicated `RS_MC_CHARACTER_PIPE` output. |
| **RS MultiCharacter Sampler** | Common positive/negative prompts, local sampling, optional autosave, image/latent/pipe/info outputs. |
| **RS MultiCharacter Load Image** | PNG/WebP image and mask, restored character pipe and generation information. |

## Install

Find **RS MultiCharacter Sampler (Anima Alpha)** in ComfyUI-Manager, or open the [Comfy Registry page](https://registry.comfy.org/publishers/raspie10032/nodes/comfyui-rs-multicharacter-sampler). Package ID: `comfyui-rs-multicharacter-sampler`. Restart ComfyUI after installation. If the new listing is not yet visible in your Manager cache, refresh its node list or use the Git installation below.

For Git installation, clone this repository into your ComfyUI `custom_nodes` directory, then restart ComfyUI. Use one installation method; do not install a second copy alongside an existing Git checkout.

```sh
git clone https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler.git
```

Run the command **inside `ComfyUI/custom_nodes`**. The extension uses ComfyUI's existing PyTorch, NumPy and Pillow. Python 3.11+ and a ComfyUI version with Anima support are required; the tested environment is recorded in the validation report. No weights are bundled or downloaded automatically.

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

## Restore from an image

Select an original saved image in **RS MultiCharacter Load Image** and connect its `character_pipe` to the sampler. Image prompts and characters replace the sampler's common prompt fields. Enable **use_image_settings** to also restore seed, dimensions, CFG, sampling and region settings; leave it disabled to use the sampler widgets for those values.

**Model/LoRA/CLIP/VAE connections remain explicit.** File names and strengths are recorded in `generation_info` and metadata, but the loader does not load or download them. Reproduction requires the same assets and compatible runtime. This path regenerates from text and seed; it is not img2img.

The loader also accepts NAI V4-style character captions with one center per character. Select NovelAI prompt syntax for text typed in that syntax; imported NAI images select it automatically. NAI settings cannot be replayed as local settings: keep `use_image_settings` off for those images.

## Alpha limits

- **Anima only**, single image, text-to-image. SDXL/Flux/SD1.5, ControlNet and other attention patches are not supported.
- **1–10 input slots; actual image tests cover 1–6.** More characters do not guarantee quality. Horizontal layouts are the strongest tested use case.
- Coordinates choose prompt regions; they do **not** lock a head/body to a point or enforce exactly one person per region. A single character owns the whole image, so moving that one center does not move the person.
- Multiple rows, dense interactions and crossing props can duplicate or omit people. Four requested people in a 2×2 experiment became 12 and 10. Six people in two rows became 7 and 11. Do not treat count or identity as guaranteed.
- Per-character negative captions are preserved in metadata but **rejected by sampling** in this alpha. Use the common negative prompt. Scheduled text conditioning is not supported.
- The schedule is currently fixed to **30 steps**. Initial common weight, character gain and boundary release are advanced experimental controls, not universal quality settings.
- Autosave does not preserve an uploaded image's unrelated EXIF/GPS/camera data. Social platforms may strip generation metadata; use the original file for restoration.

See [validation](docs/validation.md) for real generation, metadata replay and the limits of the evidence. This is an alpha, not a claim of NovelAI-equivalent performance.

## Development

From this directory, using an environment containing Torch, NumPy and Pillow:

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_ui.cjs
```

License: GPL-3.0-only. See [COPYING](COPYING), [third-party notices](THIRD_PARTY_NOTICES.md) and [source lineage](docs/source-lineage.json).
