# 3D pose: feature isolation and known failures

2026-10-29. The editor makes two inputs from one camera: numbered silhouettes
for regional prompt ownership, and a shaded anatomical image for a learned pose
adapter. The generation model does not read the rig or joint coordinates.

## Controlled component comparison

Three scenes × two seeds × four conditions = **24 generated images**.

| Condition | Sampling and prompts | Pose input |
| --- | --- | --- |
| Baseline | Standard KSampler; common caption plus both appearance descriptions | None |
| Regional only | RS sampler; independent character encodings, silhouettes and default separation schedule | None |
| Pose only | Same standard KSampler text as baseline | Shaded body render + native Anima LLLite |
| Both | Same RS configuration as regional only | Same learned pose input as pose only |

Anima Base v1.0 2B, Qwen 0.6B encoder, Qwen Image VAE; 30 steps, CFG 4.5,
Euler ancestral / SGM uniform. Two people: 768×1024; one person: 768×1152.
Seeds 2026102901 and 2026102902 are paired within each scene.
`anima_3dpose_outline_7000.safetensors`, strength 1, start 0 / end 1.
No style/character LoRA, image reference or action caption was used.

Appearance descriptions: long pink hair/white blouse/red skirt and short blue
hair/yellow blouse/blue skirt; both explicitly adult women. The common caption
describes a sunlit university garden, anime illustration and full bodies.
Regional-only is a complete regional configuration, not a mask-only mathematical
ablation; global and separate character text encodings are not identical tensors.

## Observations

| Scene | Baseline / regional only | Pose only / both |
| --- | --- | --- |
| First person raises arm | Neither seed raises that arm above the head | Both seeds raise it; elbow/hand angles differ |
| Oblique single-person sitting | Both seeds stand | Both seeds become seated; feet/support/contact differ |
| Frontal seated person beside standing person | Seating weak | Still fails: raised feet/floating or standing-like bodies |

The white/yellow blouse assignment survives in both regional conditions, whereas
global conditions can exchange them. Hair color still changes in some regional
outputs. This does not establish general identity fidelity or a pose success rate.
The multi-person seating failure persists without regional control, so it cannot
be attributed solely to RS attention separation.

| Condition | Mean seconds over six outputs |
| --- | ---: |
| Baseline | 7.20 |
| Regional only | 8.94 |
| Pose only | 7.98 |
| Both | 9.90 |

Physical RTX 4070 Ti SUPER; after model loading, text preparation through
sampling and VAE decode, excluding CPU 3D rendering. Fixed condition order,
single measurement per case and two mixed resolutions: reference timings, not
a randomized repeated speed benchmark. Earlier editor integration renders took
about 3.2 seconds for one body and 6.4 seconds for two at these sizes.

## Separate editor integration evidence

The integrated editor also produced 12 paired images (three scenes × two seeds
× adapter off/on) and one successful complete 14-node workflow. That earlier
comparison used global RSCV5 style LoRA 0.9; it must not be conflated with the
LoRA-free component comparison above. Its real generated PNG includes the
workflow and v2 rig scene: [example](../examples/pose3d/anima-native-pose.png).

Additional strength 1/1.5/2 and optional action-caption comparisons induced more
leg bending but did not reliably fix frontal seating. Strength alone is not a
verified fix. Exact joints, hand contact, clothing and character identity remain
limitations. Anima 2.9B pose weights, other model-family pose adapters, character
LoRA combinations and progressive pose sampling are not validated here.

Full-resolution comparison images, scenes, per-case settings and timings are
distributed as optional [1.0.7 Release assets](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/releases/tag/v1.0.7),
so they do not enlarge a Git installation. Code/integration tests are evidence of
execution and serialization, not pose quality. [Setup](pose3d.md) ·
[Asset and implementation references](../THIRD_PARTY_NOTICES.md).
