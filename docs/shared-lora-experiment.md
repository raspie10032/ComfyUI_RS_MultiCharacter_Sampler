# Shared-layer regional LoRA experiment

This clone-only experiment exposes **Normal / Precision** on **RS Character LoRA**. The selection travels through the dedicated pipe and is saved/restored with PNG/WebP metadata. Normal requests shared layer execution for supported Anima/SDXL linear LoRAs; Precision retains independent predictions and small-factor optimization. Existing workflows and images without a mode default to Precision. This document describes a candidate, not a released version.

The description panel below the LoRA controls changes immediately with the selection
and follows ComfyUI's English, Korean or Japanese locale. It explains the execution
method, speed/compatibility tradeoffs and scope. It is display only and never enters
workflow widgets or image metadata. The mode applies to all slots in that pipe.
Detailer corrects one matched character at a time using Precision in either mode.

Normal falls back to Precision when the model/adapter is unsupported, recording the
requested mode, effective mode and reason in generation information and image
metadata. Runtime failures still propagate as errors. No model-side LoRA means no
model execution difference. The private benchmarking option described in earlier
experiments remains separate from the product interface.

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

Anima's preceding experiment also compared independent and shared execution. The timing comparison above concerns two plain linear character LoRAs and one fixed seed. Other SDXL checkpoints, convolutional/extended adapters, larger casts and external patches remain outside this generation comparison. Existing installed and published extensions are unchanged.

## Additional character and UI validation, 2026-10-19

The clone's `validation/ilxl-leakage/manifest.json` contains 41 successful image
generations with Changli/Zani and Shorekeeper/Carlotta. Controls include three seeds
per pair with explicit appearance prompts, swapped LoRA assignments, one-sided and
disabled LoRAs, native weight hooks, and trigger-only prompts. Comparison sheets and
individual original images are in `validation/ilxl-leakage/index.html`.

Visual review with appearance prompts did not show obvious duplication of the main
hair colours, eye colours or signature ornaments in those three seeds. This is a
limited visual observation, not a leakage benchmark. Trigger-only prompts also
weakened identity in Precision; matching a hair colour alone does not establish
successful LoRA isolation. Shared hidden states continue to change pose, faces and
clothing details compared with independent evaluation.

Two further live ILXL generations used the actual split Prompt → LoRA → Position →
Finalize pipe with no benchmarking override of the selected mode. Normal recorded
`requested=normal, effective=normal`, 30 model forwards, and 9.59 seconds sampling;
Precision recorded `requested=precision, effective=precision`, 60 forwards, and
12.40 seconds. These are single local runs at 1024×768, 30 steps, CFG 5.5,
Euler ancestral / SGM uniform with Camellya/Phoebe LoRAs. Both restored runtime
forwards and released temporary factor copies after sampling. Original auto-saved
PNGs were then read by the real Load Image node: the mode and both LoRA filenames
returned in the character pipe. Evidence is `validation/lora-node-mode-*.json`.

Python checks: 157 passed. Five JavaScript check suites passed, including mode help
for all three locales, mode changes, width/height bounds, slot-count changes and
nonserialization. Firefox on the isolated ComfyUI server additionally confirmed
the actual Korean Normal/Precision panels below the LoRA controls; screenshots are
`validation/lora-mode-help-{normal,precision}-ko.png`. Source tests cover unsupported
mode fallback; the two live ILXL runs above did not require fallback.

## Selection panels and delayed field help

The candidate also adds nonserialized selection panels to Prompt, Position,
Finalize, Sampler, Load Image, Detailer and Tagger. LoRA retains its mode panel;
the Detection loader's existing precedence panel now explains model downloads,
OFF selections and optional controls. Panels follow local control values and warn
when connected values will instead be resolved at execution.

Individual controls have short English/Korean/Japanese hints after a 2000 ms hover.
The delay belongs to this extension only, respects ComfyUI's tooltip setting and
suppresses duplicate native tooltips while hovering its controls. Leaving a field,
dragging, scrolling, switching graphs or losing focus cancels the tooltip. Moving
within the same control does not keep restarting the wait. The catalogue covers
289 current schema controls, including legacy slots, plus client-side preset and
seed controls. Read-only panels do not receive control tooltips.

All seven JavaScript suites passed, including cancellation, field changes,
deleted nodes, native-title restoration, canvas/DOM/Vue row adapters, localization,
schema coverage and serialization. The earlier Python run remains 157 passed;
this addition changes JavaScript and documentation only. Firefox on the isolated
8201 server confirmed no tooltip at 1.9 s, a Korean tooltip after 2 s, no duplicate
native bubble, scroll/leave cancellation, real multiline DOM help and workflow
serialization without tooltip text. Vue row adapters have automated coverage;
the live browser checks used the canvas renderer and DOM textareas. Browser
evidence is `validation/widget-tooltips-live.txt` and
`validation/widget-tooltips-live-ko.png` in the experiment directory. The temporary
browser probe was removed after validation. No image generation was needed for
these help-only changes.
