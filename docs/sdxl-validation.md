# Experimental SDXL generation

This report records SDXL U-Net attention-routing validation before the 0.1.2 Beta release. The implementation was branched from `1bb8c79`, including sampler recommendations and the local detailer, and is included in 0.1.2 Beta. These tests used an isolated ComfyUI installation.

## What changes

The checkpoint's MODEL, dual CLIP and VAE connect to the existing sampler and character pipe. Every character is encoded separately. Clone-local `attn2` replacements allow each image region to read the common prompt and its own character sequence, excluding other character sequences. `attn1` replacements initially reduce attention between regions and relax the boundary over the denoising schedule.

The common prompt supplies SDXL's native pooled ADM and image-size conditioning. Per-character pooled embeddings are not mixed into that global vector. This is regional text control, not a trained ControlNet, exact body placement, or a person-count constraint. The common pooled vector remains active even if the common cross-attention prior is zero.

The implementation supports separate and batched CFG branches, different text lengths, and the U-Net's ceil-divided attention grids. It uses model-clone patches rather than globally replacing model functions. Unsupported model/attention layouts are rejected; exceptions clear routing state. Character negatives remain unsupported for generation, as in the Anima path.

## Live test scope

- ComfyUI commit: `15eb748b3ec5f8a0a2d470b7fb280e2d7579f916`.
- Isolated server on port 8198, physical GPU 1: NVIDIA GeForce RTX 5060 Ti, 16 GB.
- `Illustrious-XL-v1.0.safetensors` and `noobaiXLNAIXL_epsilonPred11Version.safetensors`.
- No LoRA, ControlNet, detailer, or paid API calls in these tests.
- 30 steps, CFG 5.5, Euler ancestral + normal; one additional SGM uniform comparison.
- 1024×768 for 1–3 characters, 1536×768 for 5–6, 1536×1024 for four-character XY layouts, and one 784×528 long-text test.
- Thirty-five completed SDXL generations and one completed Anima regression. Two early wrapper-integration failures were fixed; the same two SDXL cases were rerun successfully. The historical errors remain recorded in the [machine-readable evidence](sdxl-validation.json).

Two parameter sets were compared at the same randomly selected seed for each model/count case, with an additional same-seed two-character prompt swap. This is a development comparison, not a multi-seed success-rate estimate.

| Parameter | Existing Anima defaults | SDXL example |
| --- | --- | --- |
| Initial common prior | 0.05 | 0.30 |
| Initial character gain | 1.7 | 1.3 |
| Initial spatial separation | 0.9 | 0.5 |
| Boundary hold / decrement | 3 / 0.2 | 3 / 0.2 |
| Common boost after step 3 | 0.1 | 0.1 |

These are initial values in the existing schedule, not constant weights for all 30 steps. The node's Anima defaults are unchanged. Load the SDXL example to get the trial SDXL settings.

## Observed image quality

The original Anima settings produced visible panels and large differences in character scale on SDXL. The example's softer settings often improved scene continuity, but did not enforce exact identity or count.

| Case with SDXL example settings | Observed result |
| --- | --- |
| Two-character prompt swaps, both models | Black short hair and blonde long hair moved to the requested side. Some trials still mixed clothing colors. |
| Three characters, both models | Three visible characters, with distinguishable black/blonde/green hair; small attribute errors remain. |
| Four characters in a 2×2 XY arrangement, Illustrious | Three visible figures, black hair duplicated, green/pink identities lost. |
| Four characters in a 2×2 XY arrangement, NoobAI | Five visible figures, repeated black/blonde identities and mixed clothing. |
| Five requested, both models | Six visible figures in the reviewed balanced trials. |
| Six requested, Illustrious | Five visible figures; the black-haired character was missing. |
| Six requested, NoobAI | Six visible figures with the requested hair/eye and major clothing-color separation. This single result does not establish reliable six-character generation. |
| One requested, NoobAI | The intended woman is present, but campus bystanders also appear. A single character slot does not forbid background people. |

The full local gallery includes failures as well as selected good results. Count and identity review was visual; no automatic detector count is used as ground truth. The manifest records requested slot count, not the number of people in the output.

## Functional verification

- All 36 completed runs have their request, execution history, image and generation audit saved. Metadata agrees with the generation report. SDXL token ownership covers each tested attention grid, and all model-forward routing scopes exited cleanly.
- The long-text test exercised a 154-token character against 77-token common/other-character sequences at 784×528, including 33×49 and 17×25 attention grids.
- A lossless WebP carrying the generated metadata was loaded through `RS MultiCharacter Load Image`. With `use_image_settings` enabled, deliberately different node prompts, seed, size and CFG were replaced by the image settings. Every saved record field matched the original. Pixels were **not bit-identical**: mean absolute 8-bit channel difference was 1.2894. Bit-exact regeneration is not claimed.
- PNG, lossless WebP and lossy WebP metadata round trips are covered by CPU tests. SDXL is marked `sdxl-spatial-alpha-1`; PNG Source identifies `SDXL (local)`. Automatic saves omit workflow JSON.
- The pre-existing Anima example generated successfully through the unchanged Anima routing path after SDXL runs. No pixel-identical comparison to a pre-change Anima baseline was performed.
- All 61 Python tests and both JavaScript UI suites passed. New tests cover CFG ordering, exclusion of foreign character text, unconditioned text preservation, native ADM passthrough, exception cleanup, odd grids and metadata restoration.
- The [UI workflow](../examples/two-characters-sdxl.json) has the same widget values and four connections as the [successfully executed API example](../examples/two-characters-sdxl-api.json). Browser-rendered import of this new example was not established; source/UI serialization checks are separate evidence.

## Limits and reproduction

Use Load Checkpoint, select either tested checkpoint, and connect MODEL/CLIP/VAE to the sampler. Connect RS MultiCharacter Prompts to `character_pipe`, or load the included SDXL workflow. The checkpoint filename must match your local installation. Set seed control to fixed to repeat a request or randomize to explore compositions.

SDXL Refiner, inpainting checkpoints, SD1.5, Flux, ControlNet and other attention patches are excluded. Other SDXL derivatives, all sampler/scheduler combinations, SDXL LoRAs, and SDXL generation→detailer chaining were not verified in this batch. Existing Anima combination recommendations do not establish SDXL recommendations.

Run source checks using your ComfyUI Python environment:

```bash
python -m unittest discover -s tests -v
node tests/test_ui.cjs
node tests/test_detailer_ui.cjs
```

The local run directory `RS_MC_sdxl/validation` contains the full requests, execution histories, per-evaluation audits, images, test logs, `summarize.py`, and `index.html`. The committed [manifest](sdxl-validation.json) contains image hashes, actual settings, prompt IDs and audit counts; the full generated image collection is kept out of the source repository.
