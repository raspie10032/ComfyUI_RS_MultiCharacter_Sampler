# 1.0.8 Hangeul

2026-10-29. Optimize Anima reference predictions while retaining independent
character-region references, strengths, correction and configured duration.

When reference guidance exactly equals CFG and no custom CFG callbacks intervene,
the referenced negative prediction cancels algebraically and is skipped. With
unit strengths and exact full-canvas coverage, the redundant base positive can
also be skipped. Unequal guidance, custom pre/CFG/post/batch callbacks and
`disable_cfg1_optimization` keep the previous calculation. No new user setting
is required. Existing workflows and adapter selection remain compatible.

## Measured generation

RTX 5060 Ti, Anima Base 1.0 BF16, global RSCV5 0.9, 1152×896, 30 steps,
Euler ancestral / SGM uniform, CFG and reference guidance 4.5, APG, reference
scale 0.8. Reference remains active for all 30 steps. Model load and PNG saving
are excluded; text/reference preparation, sampling and decoding are included.
Each condition was measured once after model warmup.

| Paired condition | 1.0.7 | Optimized | Reduction |
| --- | ---: | ---: | ---: |
| Two independent numbered regional v2 references | 148.93 s | 94.40 s | 36.62% |
| One global v2 reference, no assigned character area | 71.95 s | 45.24 s | 37.13% |

Regional PyTorch peak allocated memory: 7.381 → 7.030 GiB. Single/global and
regional scenes have different prompts and subject counts; compare before/after
within each row, not the two rows as a controlled region-overhead comparison.
These measurements are not universal speed or memory guarantees.

## Quality and validation scope

Reduced-precision evaluation order and batching can change pixels despite
algebraic equivalence. Hair colors and broad left/right assignment survived the
paired comparison, but clothing reproduction, sleeve contamination and background
errors remain. Reference-off cleanup was pixel-identical. The optimization is
not an identity or clothing quality improvement.

The release checkout passed 387 Python tests with 7 conditional skips and all
15 UI test files. The implementation also passed four Linux/Windows compatibility
jobs before release preparation. Tests cover global
and independent banks, overlap/background/strength, exact versus unequal guidance,
APG/rescale/none, custom CFG fallbacks and full-coverage prediction skipping.
The existing real-GPU paired results are retained in the
[experiment report](anima-reference-prediction-optimization.md).

Restart ComfyUI and refresh its browser after updating. The experimental features
and restrictions documented for [1.0.7](release-1.0.7.md) still apply.

**한국어:** 참조 가이던스와 CFG가 같을 때 수식상 상쇄되는 예측만 생략합니다.
영역별 참조와 적용 구간은 유지하며 16스텝 조기 종료를 기본값으로 바꾸지 않습니다.
v2 실측 조건에서 약 37% 빨라졌지만 결과 픽셀과 의상이 달라질 수 있습니다.

Upstream reference: https://arca.live/b/aiart/187407631
