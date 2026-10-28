# Numbered image-reference backend replacement — 2026-10-28

Scope: replace Anima / Krea 2 / FLUX 1–3 backends behind the existing numbered
`RSMultiCharacterReference` input. MOSS and SD1.5/SDXL keep their previous reference
path and weights. Existing node class IDs and input names remain compatible.

- Anima: optimized reference-frame adapter; automatic numbered-input preparation;
  no separate adapter node required. Compact spatial attention, cache OFF by default.
- Krea 2: Identity Edit v2, native text–reference–target ordering, reference RoPE
  beside the generated target, no square white padding, compact shared bias rows.
- FLUX.1: native reference latents require a Kontext checkpoint. Dev and Schnell
  do not become Kontext through this node; there is no automatic model substitution.
- FLUX.2/3: native reference latents with numbered regional attention routing.
- MOSS and SD1.5/SDXL: excluded from replacement. Their assets are unchanged;
  their family-specific source paths remain active.

## Validation

All direct runs used seed 2026102802, Euler ancestral + SGM uniform, two original
reference images at longest edge 768, independent left/right regions, and the same
cafe prompt without character names or detailed appearance descriptions. Normal
size was 1280×800. Anima/Krea progressive cases finished at 1728×1152. Anima ran on
RTX 4070 Ti SUPER; other families ran on RTX 5060 Ti. Times include condition
preparation and decode but exclude initial checkpoint loading; cache state varies.
These are functional timings, not a controlled performance comparison.

| Family | Steps | CFG | Completed cases | Normal run |
|---|---:|---:|---|---:|
| anima | 30 | 4.5 | normal, swap, one-off, overlap, progressive, lora | 110.2s |
| krea2 | 8 | 1.0 | normal, swap, one-off, overlap, progressive, lora | 61.7s |
| flux1 | 28 | 1.0 | normal, swap, one-off | 198.2s |
| flux2 | 4 | 1.0 | normal, swap, one-off, progressive | 21.6s |
| flux3 | 4 | 1.0 | normal, swap, one-off, progressive | 18.8s |

- Direct GPU generations: **23**. Every output has the requested dimensions,
  finite image/latent values, metadata and a latent hash. Each result JSON records
  actual adapter and routing state, including restored temporary forwards.
- Python regression suite: **306 run, 297 passed, 9 skipped**. The skipped tests
  are optional integration gates; actual model generation above is separate evidence.
- JavaScript tests: **16 passed**.
- New numerical routing tests compare Anima compact/dense attention and prove that
  changing a non-owned reference does not directly enter another region's reference
  calculation in FLUX 1–3 / Krea 2. This does not imply final pixels cannot mix.
- Real resident ComfyUI 8188: restarted with the installed files; existing
  LoadImage → Character Prompt/Position → Image Reference ×2 → Finalize → Sampler
  → SaveImage graph finished successfully. History ID
  `f4755449-7b44-46d2-ae24-b63985185631`; 1280×800 PNG saved. Queue empty afterward.

## Quality limits

- Krea 2 and FLUX.2/3: large hair/clothing/accessory features visibly follow the
  swapped reference numbers. Fine identity, clothing details and exact pose vary.
- FLUX.1 Kontext can transfer hair and accessory features, but clothing fidelity
  is weaker in the normal sample; this is not exact identity replication.
- Anima: transfer and per-character LoRA coexist, but the overlap case collapsed
  to a single character. Overlap remains a documented failure, not a passing
  separation example. Progressive output can also change clothing details.
- One-side OFF cases execute and produce a non-referenced person, but global scene
  attention may still spread style or color. No guarantee of perfect isolation.
- Only one seed and one original reference pair were used in this integration
  batch. Functional coverage is broader than quality coverage.

## Artifacts

Images, complete per-run logs and reproduction scripts are kept as external
experiment artifacts and are not bundled with git installations. This summary
records the verified scope and failures without distributing reference pictures.
