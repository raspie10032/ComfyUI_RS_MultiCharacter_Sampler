# Shared-layer regional LoRA experiment

This clone-only experiment adds an explicit `model_options['rs_mc_lora_execution'] = 'shared_layers'` path for Anima and SDXL. It also enables ordinary linear LoRA bypass on SDXL, retaining independent predictions in the default path. This document describes a candidate, not a released version.

The shared path evaluates the base model once and adds the appropriate LoRA contribution inside each linear layer. Image features receive spatially weighted deltas. Cross-attention K/V receive their own character-caption deltas; common and negative captions use spatially averaged strengths. Layer roles are identified by model paths rather than matching tensor dimensions. Unsupported patch shapes are rejected in the explicit shared path; ordinary automatic execution retains native weight-hook fallback.

Hidden states are shared, so this algorithm is not equivalent to evaluating separate LoRA-modified models and blending their final predictions. LoRA effects may propagate between regions through later attention and, for SDXL, convolution. These timings do not prove equal character fidelity or absence of leakage.

## ILXL real-generation comparison

Local evidence directory: `/var/home/raspie/Documents/Codex/RS_MC_lora_optimization_20261019/validation`.

- Checkpoint: `Illustrious-XL-v1.0.safetensors`.
- Character A: `ChamCamellyaIllustriousXL.safetensors`; character B: `Character_Phoebe-000015.safetensors`.
- Model strengths 1.0, CLIP strengths 0.0. Thus the comparison isolates diffusion-model LoRA execution.
- Canvas 1024 × 768; seed 250917; 30 steps; CFG 5.5; Euler ancestral / SGM uniform. Full requests and summaries are saved per case.
- Ten initial comparisons and four warm-model controls all completed with actual images.

| Two different character LoRAs | Sampling seconds | Diffusion-model forwards |
|---|---:|---:|
| Existing native weight-hook execution | 83.466 | 60 |
| Independent predictions with low-rank bypass | 13.619 | 60 |
| Shared layers with regional deltas | 8.364 | 30 |

These are individual measurements on the same machine, not repeated timing statistics. Sharing reduced sampling time by 38.6% relative to independent bypass in this run. Much of the improvement over native hooks already comes from avoiding repeated weight synthesis. Reported times exclude text encoding, VAE decoding and saving; end-to-end timings are in the benchmark records.

Peak allocated GPU memory was approximately 6.74 GiB for native hooks and 6.88 GiB for shared layers. This experiment demonstrates no VRAM reduction.

Control results:

- Same LoRA on both sides: independent bypass and shared layers generated identical RGB pixels. Sampling was 6.238 versus 6.648 seconds: there is no sharing speed benefit when the original path already groups an identical LoRA setting.
- Swapping only LoRA assignments changes the result in both independent and shared execution. Prompt strings, coordinate slots and seed remain fixed. This demonstrates response to assignment, not a quantitative character-leakage score.
- Camellya and Phoebe features appear in the shared output. Different facial details and framing compared with independent execution are visible, as expected from the changed algorithm.
- All captured runtime forward replacements were restored and all tracked prepared factors released after generation.
- In warm-model controls, strength-zero and post-LoRA disabled outputs match the pre-LoRA disabled RGB pixels exactly.

The initial cold-model disabled control differed from subsequent disabled output. A separate native `ModelSamplingDiscrete` CPU/GPU probe reproduced the recorded schedules exactly: the first schedule matched CPU computation, later schedules matched GPU computation, with maximum absolute sigma difference `9.5367431640625e-07`. Warm controls hold the device state fixed and resolve the apparent restoration failure.

## Reproduction and checks

The local experiment harness uses a private `RSBypassBenchmarkSampler` in a separate server on port 8201. It is not an extension node shipped in this candidate. `run_ilxl_comparison.py` records requests, history, node summaries and timing counters; `scripts/summarize_ilxl.py` builds the comparison images and metrics. Four controls can be repeated with `RS_MC_ILXL_PREFIX=ilxl-warm- RS_MC_ILXL_CASES=none-before,shared-ab,shared-zero,none-after`.

Native ComfyUI CPU tests: 151 passed with no skips, using `RS_MC_TEST_COMFYUI` and setting `comfy.cli_args.args.cpu = True` before discovery. The ordinary GPU-installed interpreter without early CPU setup produced mixed-device test-fixture failures; `ilxl-tests-cpu.log` records the successful complete run. All five JavaScript UI suites passed.

Anima's preceding experiment also compared independent and shared execution. The present ILXL evidence concerns two plain linear character LoRAs and one fixed seed. Other SDXL checkpoints, convolutional/extended adapters, larger casts, external patches and image-quality consistency across seeds remain outside this generation comparison. Existing installed and published extensions are unchanged.
