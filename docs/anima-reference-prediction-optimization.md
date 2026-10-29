# Anima reference prediction optimization — 2026-10-29

## Question and implementation

The target is **independent character-region reference control**, not one shared image reference. Reference A is bound to character 1 and reference B to character 2; source banks are independently encoded/cached, predicted, and spatially composed. A global solo condition without character boxes/masks is included separately. It has a different text prompt and number of subjects, so only before/after comparisons within that condition are controlled speed comparisons.

The released reference guide is:

`N + g * (Rneg - N) + cfg * (Rpos - Rneg)`.

When `g == cfg` exactly, `Rneg` cancels algebraically. Use `N + cfg * (Rpos - N)` and avoid one referenced negative prediction per bank at every step. Keep the independent banks, per-character strength, APG/rescale correction, mask composition and reference duration. When all reference strengths are exactly 1 and normalized masks exactly cover every pixel, the base positive prediction also cancels. This second condition uses a conservative exact test; fractional box boundaries can prevent it.

Custom pre-CFG, CFG, post-CFG or conditional-batch callbacks, `disable_cfg1_optimization`, and unequal guidance retain the old implementation. A developer comparison switch (`fold_reference_guidance`) permits paired benchmarks; no extra user control is required.

K/V caching already works: two reference prefills and 58 hits across the 30-step two-bank v2 run. It avoids re-encoding the source, not denoising the current image once per bank. With two regions the main test reduces logical predictions from six to four per step. Some predictions can be batched, so logical counts do not translate directly into a time ratio. Full, unit-strength point coverage reduces six to three in the separate 6-step execution test.

## Conditions

- Isolated checkout based on released `44721fb` (1.0.7), branch `codex/anima-reference-prediction-speed-20261029`.
- Physical RTX 5060 Ti, UUID `GPU-40a1aab0-3207-69c9-7030-228aa5caaa2a`.
- Anima Base 1.0 BF16; RSCV5 global style LoRA 0.9; no character LoRA.
- New original references: violet side braid/navy suit and mint bob/orange dress. Generated reference PNGs are in the adjacent fresh-reference experiment and were visually checked.
- 1152×896, 30 steps, Euler ancestral / SGM uniform, CFG 4.5, reference guidance 4.5, APG, reference scale 0.8, entire 30-step reference duration.
- Seed 202610291703. Both character prompts only specify an adult woman, relaxed smile and standing; no name, hair, eye or outfit tokens.
- Numbered half-canvas boxes, reference slot strength 0.8. Left/right swap uses the same seed/text with swapped reference assignments.
- Timing includes text/reference preparation, sampling and VAE decoding; excludes model first load and PNG serialization. Model is warmed first. A single pass per case, not a repeated statistical timing study.
- PyTorch peak allocated/reserved memory is reset per case. NVIDIA board memory sampled every 250ms includes other allocations and can miss shorter peaks; it is not the same as PyTorch allocated memory.

## Main measured results

| Condition | Released seconds | Optimized seconds | Reduction | PyTorch peak allocated before → after |
| --- | ---: | ---: | ---: | ---: |
| Two independent regional v2 references | 148.93 | 94.40 | 36.62% | 7.381 → 7.030 GiB |
| One global v2 reference, no character areas | 71.95 | 45.24 | 37.13% | 6.814 → 6.514 GiB |

Optimized regional v1: 124.94 seconds. Optimized regional v2 with A/B swapped: 94.97 seconds. Those are additional cases, not paired v1 speed measurements. The preceding fresh-reference experiment's v1/v2/first-16/global rows remain in their original report; different runs must not be substituted for this optimization pair.

Reference-off generation before and after the 30-step sequence is pixel-identical. No retained hooks, non-finite pixels/latents, or leaked reference state were observed.

## Quality and numerical differences

Algebraic equivalence does not guarantee pixel equality in reduced-precision GPU execution. Batching and floating point evaluation order change. Before/after mean absolute RGB differences (0–255): regional 5.489; global 3.174. Both pairs are **not** pixel-identical. These are output-difference measurements, not perceptual quality scores.

Visual review: regional hair colors and left/right assignment remain, while sleeves and background differ. The orange dress is not faithfully reproduced; green tint leaks into the other character's sleeve, and the greenhouse background is weak. Swapping banks swaps the broad character identities, not exact outfits. Optimization does not solve these existing reference-quality limitations. One scene and one seed cannot establish a success rate.

## Additional execution guards

- Six-step same-scene/unit-strength fractional boxes: 30.74 → 19.99 seconds; 12 referenced-negative predictions skipped, base positive retained because full exact coverage was not established.
- Six-step unit-strength point partitions with zero feather: 30.91 → 16.36 seconds; 12 referenced-negative and 6 base-positive predictions skipped. This is a path/execution smoke test, not a 30-step quality/timing claim.
- The second smoke script originally inspected the 30-step cleanup images; the filename was corrected and the actual 6-step before/after PNGs were independently checked pixel-identical. Point-coverage cleanup also passed with the proper filenames.

## Automated validation

Python: 394 collected, 380 passed, 14 conditional skips. Reference compatibility against the separate older ComfyUI checkout passed. New tests cover single/global and independent numbered banks; overlap, background and strengths; exact versus near-but-unequal guidance; APG/rescale/none; disabled/custom CFG paths; full-coverage skip and its fallbacks. Numeric comparisons use explicit tolerance, not bitwise identity.

## Reproduction and artifacts

`run.py` delegates the fixed experiment environment and imports to the adjacent fresh-reference experiment. `benchmark.py --phase compare` runs the main sequence; `benchmark_coverage.py --phase compare` and `benchmark_coverage_point.py --phase compare` exercise additional branches. Use the recorded physical GPU UUID and the existing ComfyUI virtual environment. All sources, paths, prompts, metadata and latent hashes are recorded in `results/*.json`. Keep the experiment folder alongside its adjacent source/reference folder to reproduce imports.

`measurements.csv`, `pixel-comparison.json`, original PNGs with experimental metadata, saved latent tensors, 250ms GPU samples, logs, publication figures and `index.html` are retained. PNGs are experimental outputs, not falsely advertised as complete drag-and-drop workflows.

Upstream reference: https://arca.live/b/aiart/187407631
