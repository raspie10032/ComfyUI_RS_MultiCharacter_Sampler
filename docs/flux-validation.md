# FLUX development validation — 2026-10-19

This is a development candidate, not a published FLUX release. Keep the installed
0.2.1 package until the remaining full-weight tests have been reviewed.

## Architecture

FLUX.1 and FLUX.2 use native joint attention with independently encoded regional
captions. Caption position indices restart for each region. FLUX.1 retains its
native zero-valued text positions and pooled common-prompt embedding. FLUX.2
preserves its native 512-token padding. Image positions and model weights are not
rewritten.

FLUX 3 has a separate path. Its early text blocks process each caption separately
before joint image/text attention. Caption RoPE offsets are corrected only on the
text-position axis. Base models can reuse those text states; distilled flow-map
models recompute them using the next sigma. Regional LoRA hooks disable the
Base text cache because the active weights can change between region evaluations.
Full-weight regional LoRA validation is still pending.

`flux_guidance` controls the embedded guidance of FLUX.1 Dev / FLUX.2 Dev. It is
separate from CFG and is saved/restored in generation metadata. Schnell, Klein,
and FLUX 3 do not use this embedded-guidance value. FLUX 3 Base uses ordinary CFG.

The candidate supports native text-to-image model routing. FLUX Fill/Control,
reference-image editing, and GGUF/custom model implementations are not verified
by this work. Fill/Control and reference inputs are explicitly rejected rather
than silently routed as ordinary text-to-image models. Update ComfyUI for the
current FLUX attention hooks and model loaders.

## Small-model / source verification

ComfyUI revision: `5cc4b870094c89090db54bd8d12649dcaf89f2ba`.

The native CPU tests build small random-weight models, not downloaded checkpoints.
They cover FLUX.1, FLUX.2, FLUX 3 Base, FLUX 3 flow maps, intersecting boxes,
independent text positions, cached/raw text paths, and combined positive/negative
CFG batches. The negative branch matches unmodified native attention. These tests
verify execution and caption routing, not image quality.

```sh
RS_MC_TEST_COMFYUI=/path/to/ComfyUI python -m unittest discover -s tests -v
node --test tests/*.cjs
```

Current local results: 131 Python tests and five JavaScript test files pass. Old
ComfyUI integrations skip native model tests for architectures they do not contain.
No public CI run or release is claimed by these local results.

## Full-weight status

| Model | Actual weights | Current evidence |
|---|---|---|
| FLUX.2 Klein 4B FP8 | Downloaded, SHA-256 verified | Seven real generations; see below |
| FLUX.2 Klein Base 4B FP8 | Downloading | Small native model only; real generation pending |
| FLUX.2 Klein 9B FP8 | Access approved; downloading | Small native model only; real generation pending |
| FLUX.2 Dev FP8 mixed | Downloading | Small native model only; real generation pending |
| FLUX.1 Schnell FP8 | Queued download | Small native model only; real generation pending |
| FLUX.1 Dev FP8 | Queued download | Small native model only; real generation pending |
| FLUX 3 Klein INT8 | Access approved; downloading | Small native model only; real generation pending |
| FLUX 3 Klein Base INT8 | Access approved; downloading | Small native model only; real generation pending |

The remaining campaign waits for verified model files and runs a two-person scene
and its same-seed caption swap per model. Execution and visual acceptance are
recorded separately. It does not cover every seed, sampler, quantization or
third-party FLUX variant.

## Klein 4B observations

Native FP8, Qwen 3 4B, FLUX.2 VAE; 768×512 (four-person XY: 768×768),
Euler / simple, four steps, CFG 1, seed 20261019. The candidate example and
preset use initial common weight 0.6, common boost 0.1, character gain 1.7,
spatial separation 0.9, three-step boundary hold and boundary decrement 0.2.
Mixed text uses character gain 1.2 / separation 0.35; four-person XY uses
character gain 1.2 / separation 0.6.

- Baseline two-person generation produced distinct red/blue hair, matching clothes,
  a white cup and a yellow book. Its shared scene/style was weak.
- Raising initial common weight to 0.6 made the campus setting visible.
- Swapping only the two captions at the same seed moved the corresponding
  appearance and props to opposite sides. Coordinates stayed fixed.
- A mixed layout produced two characters and `HELLO` inside the upper text box.
- A four-point XY layout placed four characters in the corresponding quadrants.
  The green-haired character's requested camera was omitted; object completeness
  and success rates are not established.
- Identical character coordinates resolved to the documented ordered layout.
- Loading the saved image into RS Load Image and regenerating with image settings
  produced exactly the same RGB pixels as the common-0.6 source image.

These are one scene/seed and diagnostic variants, not a multi-seed quality survey.
The native CPU tests, actual generation, metadata replay and resident installation
are distinct evidence. FLUX support is not installed into the everyday runtime yet.
Local detailer, per-character LoRA and prior-model full-weight regression tests
remain to be run for the FLUX candidate.

## Sources and starting settings

- [Official Klein 4B FP8](https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-fp8)
- [Official FLUX 3 ComfyUI distribution](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy)
- [Native ComfyUI model implementation](https://github.com/Comfy-Org/ComfyUI/tree/5cc4b870094c89090db54bd8d12649dcaf89f2ba/comfy/ldm)

FLUX 3 expects detailed scene captions. Its official defaults are 16 steps with
no CFG for distilled Klein and 50 steps / CFG 3.5 for Base. The validation runner
uses a written-out scene caption; it does not require downloading an additional
prompt-expansion model. The four-step Klein 4B preset is not a universal FLUX preset.
