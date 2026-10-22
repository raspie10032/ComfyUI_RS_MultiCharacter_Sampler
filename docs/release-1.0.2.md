# 1.0.2 Hangeul: regional adapter compatibility

MOSS INT8/FP8 checkpoints now accept ordinary LoRA targeting slices of fused
Q/K/V layers. Previously, those valid patches could fail with `patch_type` before
sampling. This release also extends character-specific execution to DoRA,
LoCon/Tucker convolution, LoHa/DoHa, LoKr/DoKr, GLoRA, OFT/BOFT, IA3 and static
diff/set patches. Package metadata and Python runtime both report `1.0.2`.

Plain linear LoRA retains its factor-only execution path. Complex adapters use
native core weight calculations and automatically select independent Precision
predictions. They may use more temporary memory and run more slowly. Errors
include the target key, adapter type and whether the patch targets a slice.

## Validation and limits

Before the version bump, 225 Python tests ran against each of ComfyUI 0.41.0 and
0.42.0: 224 passed and one existing core-dependent test skipped. All 10 JavaScript
UI suites passed. The compatibility workflow additionally pins ComfyUI 0.42.0
alongside its existing older Linux and Windows snapshots.

The supplied reproduction adapter passed full-model MOSS GPU forwards using
directly quantized INT8 and FP8 checkpoints on both cores. Thirteen synthetic
adapter variants exercised a real quantized layer inside that graph; IA3 also
passed the safetensors file-loading path. Outputs were finite and changed at
nonzero strength; zero strength and adapter removal restored the base output.
These checks did not sample or decode images and do not establish image quality.
Private reproduction files and model weights are excluded from this package.

T-LoRA, GLoKr, shape-changing patches, custom/GGUF tensor types and custom forward
dispatch remain outside this path. Model and adapter architectures must match.
See [supported formats, validation and limits](adapter-formats.md) for details.
