# Krea 2 and MOSS experimental support

The sampler uses native ComfyUI `Krea2` and `MOSSImage` model classes. Use a ComfyUI build containing both model families and its matching dependencies. The test checkout is `a639f187a9f6abfecbda9673034f2045148b6d85` (reported version 0.41.0). Older builds without MOSS cannot load its model/encoder through this extension.

## Models and examples

| Model | Diffusion model | Text encoder and CLIPLoader type | VAE | Example settings |
| --- | --- | --- | --- | --- |
| Krea 2 Turbo | `krea2_turbo_fp8_scaled.safetensors` | `qwen3vl_4b_fp8_scaled.safetensors`, **krea2** | `qwen_image_vae.safetensors` | 8 steps, CFG 1, Euler / simple |
| MOSS-Image SFT | `moss_image_sft_bf16.safetensors` | `qwen3.5_9b_int8_convrot.safetensors`, **moss_image** | `flux2-vae.safetensors` | 50 steps, CFG 3, Euler / simple |

Place files in ComfyUI's existing `models/diffusion_models`, `models/text_encoders` and `models/vae` directories. The extension does not download these generation models or run a remote prompt enhancer. Load the matching [Krea 2 example](../examples/two-characters-krea2.json) or [MOSS example](../examples/two-characters-moss.json), select your filenames, and supply each character's own prompt and XY through the existing character pipe. The examples start at common prior 0.6, character gain 1.2 and boundary separation 0.35. These are experimental starting points, not tuned universal presets.

- [Comfy-Org Krea 2 files](https://huggingface.co/Comfy-Org/Krea-2/tree/1171f4dc7e325bf3734586942e737872506c73e1), [official ComfyUI Krea 2 guide](https://docs.comfy.org/tutorials/image/krea/krea-2).
- [Comfy-Org MOSS files](https://huggingface.co/Comfy-Org/MOSS-Image/tree/6c170adf6af419f9877872ae9c7d397fcb341b99), [original MOSS-Image SFT card](https://huggingface.co/OpenMOSS-Team/MOSS-Image-SFT).
- Generation weights have their own terms: [Krea 2 Community License](https://huggingface.co/krea/Krea-2-Turbo) and [MOSS Apache-2.0](https://huggingface.co/OpenMOSS-Team/MOSS-Image-SFT). The extension remains GPL-3.0-only and does not redistribute weights.

Krea's original library uses a different no-guidance convention; **CFG 1 in ComfyUI** matches its native no-negative-pass example. MOSS uses the native ComfyUI full negative branch. The original MOSS remote pipeline's optional negative-layer-22 skip is not added by this extension.

## Implementation and limits

Character captions are encoded independently. Positive image queries read their region's caption and the common caption; other character captions are excluded. Captions also stay separated through text-refiner attention. MOSS captions retain each standalone caption's native rotary distance to image tokens. The native negative branch remains unchanged. Model and sampler wrappers are installed on a clone and clear their transient state after exceptions. See [architecture](architecture.md).

The sampler accepts 2–100 steps; existing 30-step defaults remain. Common-prior increments and boundary holds follow actual scheduled steps, including short distilled schedules. Sampler/scheduler menus still reflect the installed ComfyUI inventory; this task does not repeat the Anima 405-combination sweep for either new model.

This is text-to-image support. Reference-image editing, ControlNet, extra attention overrides, per-character negative routing and new-model detailer quality are outside the validated paths. Raw/base variants and other weight quantizations are not validated by testing Turbo FP8 and SFT BF16. XY controls prompt regions; exact counts, anatomy, poses, interactions and stable identity are not guaranteed.

## Evidence

Krea 2 Turbo FP8 full-weight validation has completed five successful generations at 8 steps / CFG 1 / Euler + simple: the two-character example, a same-seed caption swap, three characters, four characters in a 2x2 XY layout, and replay from image metadata. Black-bob/red-jacket and blonde/white-blouse identities switched sides with the captions. The four-character image placed black/blonde hair above green/purple hair, retaining the specified eyes, clothing and cup colors in this sample. Replaying the first PNG through the image loader produced identical RGB pixels (maximum absolute channel difference 0).

MOSS-Image SFT BF16 full-weight validation has completed five successful generations at 50 steps / CFG 3 / Euler + simple: the two-character example, a same-seed caption swap, three characters, four characters in a 2x2 XY layout, and replay from image metadata. The two identities switched sides with their captions. The three-character image retained the requested black/blonde/green hair, red/blue/purple eyes, clothes and three colored cups. The four-character image placed black/blonde above green/purple and retained the main clothing colors, but omitted the blue cup and mixed eye colors in the lower row. The initial two-character image also omitted one requested cup. These are visual observations from individual samples, not a measured success rate. Replaying the first PNG through the image loader produced identical RGB pixels (maximum absolute channel difference 0).

The CPU suite currently passes 69 tests, including three integrations against real ComfyUI classes. It covers native Krea refiners and joint blocks, native MOSS rotary/joint blocks, bit-identical negative outputs, attention-layout variants, foreign-caption exclusion, failure cleanup, 8/50-step settings, and PNG/lossless-WebP/lossy-WebP metadata restoration. Small random native models establish interface behavior, not image quality.

Actual Anima and Illustrious SDXL two-character generation also passes on the new ComfyUI checkout. The Anima test exposed a changed native attention container/backend argument, now handled without replacing the native shared module. These two images are regression smoke tests, not quality-rate measurements.

Run the ordinary tests in the ComfyUI Python environment:

```sh
python -m unittest discover -s tests -q
node tests/test_ui.cjs
node tests/test_detailer_ui.cjs
```

Enable the three optional native CPU integrations against your checkout:

```sh
RS_MC_TEST_COMFYUI=/path/to/ComfyUI python -m unittest discover -s tests -q
```

Without that variable the three native integrations are skipped. They create small random CPU models and download no weights.
