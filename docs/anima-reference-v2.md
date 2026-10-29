# Asymmetric Anima reference v2 — development experiment

This experiment tests **regional reference attention**, not a single global
image prompt. Each numbered reference is encoded independently and its guided
prediction is blended only into that slot's point/box/mask region. Shared target
denoising can still cause identity changes or mixing after this routing.

## Use

Connect the MODEL through `RS Anima Reference Adapter (Experimental)` and select
`Auto: Anima v2 (2B)`. The first active use prepares the pinned 175 MiB adapter,
shows download/verification progress and checks its SHA-256. Existing matching
files in ordinary or extra LoRA folders are reused. Disabled/zero-strength use
does not download. Keep the adapter's IMAGE disconnected when using numbered
Character Reference inputs through the building pipe; each number must match
its Prompt/Position slot.

The common Image Reference node's automatic `reference_frame` choice continues
to select the existing pilot adapter. This development experiment requires the
explicit MODEL adapter selection above. No existing workflow is silently moved
to v2.

## What changes

The upstream v2 weights were trained for asymmetric reference attention. A
reference branch is computed at zero reference timestep, without text cross
attention or target features. Its per-block image K/V banks are reused while
target features continue to update. This is different from caching a pilot
adapter's evolving reference features or from the separate Role K/V adapter.

Our integration keeps regional target text/self-attention and independent
numbered predictions, with target-only queries and extra cached reference keys.
Banks belong to one generation and are discarded after success, exception or
interruption. Target grid changes discard old banks before a progressive stage;
changed source content or model parameter/hook state cannot reuse old features.

## Scope and limits

- Anima **2B / 28 blocks only**. The existing pilot 2.9B conversion remains
  separate; v2 2.9B is rejected before automatic download.
- Numbered references use precision predictions. Per-character LoRA combination
  is deliberately rejected in this experiment pending its own cache/quality
  validation. A global style LoRA applied before this adapter is supported.
- Other model attention patches are rejected instead of bypassed silently.
- Progressive sampling, swapped numbered references and overlapping masks have
  been generated. This does not establish accurate identity/contact control.
- More references and larger grids need more K/V memory. Faster execution is
  not a claim of lower peak memory or identical quality.
- **Reference remains enabled through the final step by default.** Cutting it
  at step 16 is an experimental quality tradeoff, not an optimization preset.
  Later unreferenced denoising can alter reference-dependent features. Compare
  final hair, accessories and clothing as well as time; speed alone cannot
  justify turning it off. No new cutoff default was added.

## Reproduction and attribution

Upstream implementation: ElectronGirl/ComfyUI-Anima-Ref-Adapter at
`bd1e094a` (Apache-2.0; see `ANIMA-REF-ADAPTER-LICENSE`).
Weights: `ElectronGirl/anima-ref-adapter` revision
`e05a8d21ad3f3aeb68875c5ed0e85787cfba79b0`,
`anima_ref_adapter_v2_r64.safetensors`, SHA-256
`71dda6079e18d354e16e3347bc49a9b710afd9495c378efbb833d30cac9cb81b`.
Weights retain their own terms and are not bundled.

CPU/native tests compare v2 math against pinned upstream functions, rectangular
regional attention against a dense calculation, prefill independence from target
text, cache invalidation/reuse, error cleanup and automatic asset selection.
Real generation conditions and image comparisons are recorded separately in the
2026-10-29 experiment report; unit tests are not evidence of image quality.

## Observed results (2026-10-29)

In a single-seed, two-character regional test on a 4070 Ti SUPER, with a global
RSCV5 style LoRA 0.9, 30 steps, Euler ancestral / SGM uniform, CFG 4.5 and
reference scale 0.8, full-duration pilot/v2 took 75.19/49.67 seconds at
1152×896 and 193.51/136.74 seconds at 1664×1280. Torch peak allocated increased
by about 486/891 MiB respectively. These measurements exclude model loading
and include reference/text preparation, sampling and VAE decoding.

Numbered source exchange changes the result, but identity fidelity is not
solved: the right short-haired source became long-haired at 1MP, and both
shirts became green at 2MP. Reference guidance 6 and 8 did not fix the hair
problem. This is not a quality-equivalent replacement for the pilot path.
Cutting the pilot reference at step 16 was faster but changes later appearance;
it is a comparison condition, not a recommended default.

No-reference generations before/after reference use matched pixel-for-pixel;
automatic weight selection matched manual selection's latent hash. These are
cleanup/asset-selection checks, not evidence of character-reference accuracy.
