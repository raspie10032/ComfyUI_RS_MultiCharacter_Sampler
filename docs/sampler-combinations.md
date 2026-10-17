# Anima sampler and scheduler starting points

All samplers and schedulers registered by the installed ComfyUI are selectable. The node reads `KSampler.SAMPLERS` and `KSampler.SCHEDULERS` for both its dropdowns and restored-setting validation. Native names are stored in workflows and image metadata. New ComfyUI choices do not need an extension allowlist update. Choices absent from the current installation produce an error identifying the unavailable sampler or scheduler.

## Suggested pairs

| Sampler | Scheduler | Observation in the fixed comparison |
| --- | --- | --- |
| `euler_ancestral` | `sgm_uniform` | Default starting point. Clear character features and shared cafe background; adjacent seating. |
| `euler` | `linear_quadratic` | Alternative composition. Preserved the two characters' hair/outfits/cup colors and followed the face-to-face seating request. |
| `dpmpp_2m_sde_gpu` | `beta` | Clear alternative. Distinct hair/outfits/cups and a shared background, but adjacent instead of opposite seating. |

Select both dropdowns manually. These suggestions never change a workflow's values automatically and do not prevent choosing other combinations. New nodes retain `euler_ancestral + sgm_uniform` even when ComfyUI lists Euler/simple first.

## What was tested on 2026-10-17

- ComfyUI `15eb748b3ec5f8a0a2d470b7fb280e2d7579f916` (0.34.0), frontend 1.51.9.
- Anima Base v1.0, no LoRA; the bundled two-character cafe prompt.
- Seed `49227753394327`, 1536×768, 30 steps, CFG 4, default region settings.
- All **45 samplers × 9 schedulers = 405** installed combinations. Every request differed only in its sampler and scheduler.
- **405 executions completed, 0 execution errors.** Saved images, metadata, request histories and routing traces were cross-checked. Traces verified region assignment, configured weights and forward restoration, not solver correctness or visual quality.
- All 405 outputs were inspected in reduced-size contact sheets. Original images were inspected for selected cases, including all three pairs above. This was not a complete anatomy or prompt-compliance score.

The original comparison used baseline extension `5f0363a` with the inventory change from the `codex/anima-sampler-matrix` branch and optional trace output in the engine. The selectable-inventory implementation retains the baseline engine and region mathematics; the private trace writer is not included. The local evidence directory is `RS_MC_sampler_matrix/validation/20261017-all-combinations/` and contains the manifest, per-case requests/results/histories/traces, PNG originals and `completion-audit.json`. Those bulk artifacts are not bundled in the extension.

Original PNG SHA-256 values for the three suggestions:

| File | SHA-256 |
| --- | --- |
| `euler_ancestral--sgm_uniform.png` | `63ed579f5fe41217dc938748af8d03374fea3a6c019681cacd2ae7aaaae7f651` |
| `euler--linear_quadratic.png` | `42b68e29e89cbcdde7fcefb816764cdf07b26ed37e99011baddeb334cbc2f940` |
| `dpmpp_2m_sde_gpu--beta.png` | `cdd1c55e884d071f62e126bf7d902ef68ae7f1f01fa109420ef1c17df3c99a0a` |

## Quality limits and CFG++

At least 64 outputs showed severe degradation in this comparison: all nine schedulers for `dpmpp_2s_ancestral_cfg_pp`, `dpmpp_2m_cfg_pp`, `res_multistep_cfg_pp`, `res_multistep_ancestral_cfg_pp`, `gradient_estimation_cfg_pp`, `ddpm` and `res_multistep_ancestral`, plus `ipndm_v + linear_quadratic`. This is a lower bound on clear failures; the remaining 341 are not all quality passes. Several Karras/exponential cases showed ghosting. Euler CFG++ variants also produced coherent scenes, so CFG++ cannot be treated as uniformly incompatible.

The [original CFG++ research](https://cfgpp-diffusion.github.io/) uses lower guidance scales. That does not establish appropriate settings for every ComfyUI variant with Anima. This comparison used the same CFG 4 and 30 steps everywhere; it did not test lower-CFG/fewer-step settings or isolate model/sampler effects from region routing. Failure causes remain undetermined. All combinations remain selectable, with no new automatic CFG/step adjustments.

The alpha still accepts **30 steps only and CFG 1–20**. The three suggested pairs were observed at 30/4. Lower guidance or other step counts require separate implementation and validation; no recovery or quality claim is made for them here.

One scene and seed cannot establish a general ranking, success rate or guaranteed character count. Use these pairs as starting points and judge your own prompts and models.

## Selectable-inventory implementation checks

- `python -m unittest discover -s tests -p 'test_*.py' -v`: **44 tests passed**. New coverage includes host inventory changes, CFG++ choices, preserved defaults, missing-choice errors, and a nondefault sampler/scheduler restored through PNG and both WebP formats.
- `node tests/test_ui.cjs`: existing slot visibility, restoration and serialization checks passed.
- An isolated ComfyUI process registered all three extension nodes. Its sampler schema exactly matched the core KSampler's **45 sampler and 9 scheduler names**, with defaults `euler_ancestral` and `sgm_uniform`.
- A fresh node in Firefox showed those defaults. The schema check verifies the complete inventory; the screenshot verifies the rendered defaults, not an interaction with every dropdown item.
- Engine, routing, metadata and example workflows are unchanged. No extra images were generated for this inventory/documentation change; the visual evidence is the earlier matrix.
