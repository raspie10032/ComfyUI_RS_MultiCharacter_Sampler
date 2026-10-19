# FLUX development validation — 2026-10-19

This is a locally validated development candidate, not a published FLUX release.
The everyday 0.2.1 installation has not been replaced by this validation campaign.

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
Regional LoRA uses activation-side low-rank deltas for supported FP8/INT8 linear
layers. Original quantized weights and their metadata stay intact. This includes
ComfyUI's mixed-precision linear layers and sliced/fused QKV adapters. LoRA hooks
also surround FLUX 3's early text preprocessing; changing region weights must not
reuse the previous region's cached text states.
FLUX 3 diffusers `transformer.mode_blocks`, `txt_mode_blocks` and
`single_transformer_blocks` attention names are mapped onto native ComfyUI
targets, preserving native fused-QKV slice offsets. Existing ComfyUI mappings
take precedence over these compatibility aliases.

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

Current local results: 141 Python tests and five JavaScript test files pass. These
include real ComfyUI FP8/INT8 linear layers, expected low-rank residuals, sliced
adapters, cleanup, native regional routing and FLUX 3 flow-map timesteps. Old
ComfyUI integrations skip native model tests for architectures they do not contain.
No public CI run or release is claimed by these local results.

Image-settings replay was also tested on Klein 4B, FLUX.1 Dev, FLUX.2 Dev,
FLUX 3 Klein and FLUX 3 Base. Each restored image matched its source RGB pixels
and saved generation metadata exactly, despite different seed, step, CFG and
guidance values supplied on the replay node.

## Full-weight status

| Model | Actual weights | Current evidence |
|---|---|---|
| FLUX.2 Klein 4B FP8 | Downloaded, SHA-256 verified | Two people, same-seed swap, local masked detailer; XY/text/replay diagnostics below |
| FLUX.2 Klein Base 4B FP8 | Downloaded, SHA-256 verified | Two people, same-seed swap, local masked detailer |
| FLUX.2 Klein 9B FP8 | Downloaded, SHA-256 verified | Two people, same-seed swap, local masked detailer |
| FLUX.2 Dev FP8 mixed | Downloaded, SHA-256 verified | Two people, same-seed swap, local masked detailer |
| FLUX.1 Schnell FP8 | Downloaded, SHA-256 verified | Two people, same-seed swap, local masked detailer |
| FLUX.1 Dev FP8 | Downloaded, SHA-256 verified | Two people, same-seed swap, local masked detailer |
| FLUX 3 Klein INT8 | Downloaded, SHA-256 verified | Two people, same-seed swap, local masked detailer |
| FLUX 3 Klein Base INT8 | Downloaded, SHA-256 verified | Two people, same-seed swap, local masked detailer |

Each model generated the two-person scene and its same-seed caption swap. Visual
review found two separate people and the red/blue hair, corresponding jackets and
cup/book moving to the opposite side. Eye colors and detailed clothing were not
consistently correct. This one scene/seed per model establishes a working path,
not a success rate across prompts, seeds, samplers or third-party quantizations.

All eight models completed the local masked detailer. Face detection found two
faces in every source. FLUX.1 Schnell/Dev edited both faces; the other six edited
one and retained one because the tagger did not meet the matching threshold.
Across all eight outputs, the number of changed pixels outside the returned mask
was exactly zero. A retained face is a matching skip, not proof that it was edited.

## Trained regional LoRA and prior-model regression

Three downloaded, SHA-256-verified trained adapters were tested in four cases:

| Model | Trained adapter | Actual trials |
|---|---|---|
| Klein 4B FP8 | [Limbicnation pixel art](https://huggingface.co/Limbicnation/pixel-art-lora) | No adapter, character 1, character 2, strength zero |
| FLUX.1 Dev FP8 | [UmeAiRT modern pixel art](https://huggingface.co/UmeAiRT/FLUX.1-dev-LoRA-Modern_Pixel_art) | No adapter, character 1, character 2, strength zero |
| FLUX 3 Klein INT8 | [SimpleTuner photo aesthetics](https://huggingface.co/SimpleTuner/flux-3-klein-image-photo-aesthetics-distilled-assisted-512) | No adapter, character 1, character 2, strength zero |
| FLUX 3 Base INT8 | Same FLUX 3 adapter, also exercised on Base | No adapter, character 1, character 2, strength zero |

All sixteen executions succeeded after fixing packed-weight application and the
FLUX 3 adapter names. In all four cases, strength zero matched the no-adapter RGB
pixels exactly and strength one changed the image. These checks establish actual
weight application; they do not establish a requested artistic effect or character
identity for every adapter.

Regional influence is not completely isolated. Seven of the eight active trials
changed the selected half more than the opposite half. In the FLUX 3 Base
character-1 trial, the opposite half changed more (mean absolute RGB change 18.06
versus 14.01). Treat Base regional LoRA separation as provisional, particularly
with global style/lighting adapters. Full-checkpoint LoRA coverage for Schnell,
Klein Base 4B, Klein 9B and FLUX.2 Dev is not established by these four cases.
Packed checkpoints reject unsupported adapter formats with an explicit error;
they do not fall through to incompatible native weight hooks.

The two-person-plus-`HELLO` box layout was visually checked on Klein 4B,
FLUX.1 Dev, FLUX 3 Klein and FLUX 3 Base. Both people and the upper `HELLO` sign
were present in each trial. Existing Anima and SDXL examples also completed
actual full-checkpoint generation under the final candidate. These are smoke
tests, not claims of pixel-identical old output or complete sampler coverage.

Machine-readable case results, pixel measurements and trained-adapter revisions
are saved in [flux-validation-results.json](flux-validation-results.json).

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
Additional trained-LoRA, metadata replay, mixed-layout and prior-model regression
results are recorded in the local campaign report. Only the exact cases listed
there are covered; architecture support does not establish compatibility with
every community LoRA.

## Sources and starting settings

- [Official Klein 4B FP8](https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-fp8)
- [Official FLUX 3 ComfyUI distribution](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy)
- [Native ComfyUI model implementation](https://github.com/Comfy-Org/ComfyUI/tree/5cc4b870094c89090db54bd8d12649dcaf89f2ba/comfy/ldm)

FLUX 3 expects detailed scene captions. Its official defaults are 16 steps with
no CFG for distilled Klein and 50 steps / CFG 3.5 for Base. The validation runner
uses a written-out scene caption; it does not require downloading an additional
prompt-expansion model. The four-step Klein 4B preset is not a universal FLUX preset.
