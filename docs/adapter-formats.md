# Regional adapter formats

This patch fixes ordinary MOSS Q/K/V slice LoRA on packed INT8/FP8 checkpoints and
extends regional execution to the following static adapters. Package and runtime
versions are both 1.0.2. See the [release notes](release-1.0.2.md).

GGUF support was subsequently added through ComfyUI-GGUF's native layer
operations. See [GGUF compatibility](gguf-compatibility.md) for setup, measured
scope and remaining limits; the historical 1.0.2 validation below does not prove
GGUF execution.

| Format | Regional application |
| --- | --- |
| Plain linear LoRA, exported DyLoRA using ordinary factors | Existing factor-only path, including fused Q/K/V input/output slices |
| LoCon, LoRA mid/Tucker convolution | Core weight algebra, current-layer output correction |
| LoHa / DoHa, LoKr / DoKr | Core weight algebra, including decomposed factors and Tucker convolution |
| DoRA | Core magnitude/direction weight algebra |
| GLoRA | Core old/new tensor conventions |
| OFT / BOFT | Core orthogonal/butterfly weight algebra |
| LyCORIS IA3 `(IA)^3` | Additional `.weight` + scalar `.on_input` loader and static channel scaling |
| Full/diff, bias/norm differences, set | Core diff/set semantics, with matching shapes |

The core is the compatibility reference for its registered adapter classes. The
additional IA3 implementation follows the upstream weight-merge formula
`W + strength * W * channel_vector`. Input/output scaling, partial keys and native
prefetch reconstruction are covered by independent tensor comparisons. The
LoKr Tucker path materializes contiguous factors to avoid a native noncontiguous
`torch.kron` failure; it preserves core alpha/rank and DoRA semantics.

Complex adapters use independent regional predictions. Normal mode automatically
falls back to Precision for them. Only one layer's FP32 delta is retained during
its call, but several full-size intermediate tensors can exist for that layer.
This is a correctness path, not a claim of equal speed or memory to plain LoRA.
The checkpoint tensor and quantization scale storage are not replaced. Strength
zero bypasses all adapter calculations; temporary forward dispatch is restored
on completion, failure and cancellation.

## Validation

The 225-test Python suite passes against local ComfyUI 0.41.0 and isolated 0.42.0
(224 passed, one existing core-dependent skip, each). All 10 JavaScript UI suites
pass. CPU comparisons cover INT8, FP8 and ordinary floating-point weights,
positive/negative strengths, Q/K/V slices, bias, convolution and normalization,
incoming global cast functions, native file conventions, malformed input,
prefetch reconstruction, cancellation and restoration. These are numerical and
integration tests, not image-quality evaluations.

The supplied reproduction file loads as 246 ordinary LoRAAdapter patches: 123
whole keys and 123 partial keys. The pre-patch packed-MOSS rejection is fixed.
Full-model MOSS GPU forwards with random inputs passed for directly quantized
INT8 and FP8 checkpoints on both cores. Additional synthetic adapters exercised
one real quantized layer inside the full MOSS graph, with finite changed outputs,
strength-zero equality and removal equality. This verifies execution, not every
layer of every downloadable adapter. No sampler, VAE decode or images were used.
Private files, tensor data, prompts and checkpoints are not included in the repo.

## Boundaries

- Model family, checkpoint and adapter must still match. This does not convert
  adapters between model architectures or bridge incompatible dimensions.
- T-LoRA requires timestep masks and initial-state subtraction; its unique
  `lambda_layer` marker raises an explicit unsupported-format error.
- GLoKr is mentioned in upstream algorithm documentation but is absent from the
  inspected current module registry and ComfyUI adapter registry. No GLoKr file
  convention or execution support is claimed.
- Multi-GPU model clones, other custom tensor subclasses, custom forward dispatch,
  shape-changing patches and function patches remain outside this new path.
- Existing per-model CLIP and Anima precomputed-text-adapter restrictions remain.
- Native `set` patches replace a weight at nonzero strength according to the core
  semantics; they do not behave like an additive LoRA strength interpolation.

## Sources

- [ComfyUI weight adapter implementations](https://github.com/Comfy-Org/ComfyUI/tree/master/comfy/weight_adapter)
- [LyCORIS algorithm list](https://github.com/KohakuBlueleaf/LyCORIS/blob/main/docs/algorithms/README.md)
- [LyCORIS module registry](https://github.com/KohakuBlueleaf/LyCORIS/blob/main/lycoris/modules/__init__.py)
- [LyCORIS IA3](https://github.com/KohakuBlueleaf/LyCORIS/blob/main/lycoris/modules/ia3.py)
- [LyCORIS T-LoRA](https://github.com/KohakuBlueleaf/LyCORIS/blob/main/lycoris/modules/tlora.py)
