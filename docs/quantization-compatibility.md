# Quantized diffusion models

Connect a compatible loader's **MODEL** output to the existing RS sampler or
RS detailer. Keep the model family's matching text encoder, VAE and LoRAs.
Quantization does not translate adapters between model architectures.

## Native ComfyUI packed weights

Regional adapters retain ComfyUI's packed weight storage and run the original
layer operation before adding the character's low-rank output. Detection now
checks the actual packed tensor instead of restricting this path to a small
list of model classes. This covers packed layers in Anima, SDXL/Illustrious,
SD1.5, FLUX.1, FLUX.2, FLUX 3, Krea2 and MOSS when their loaders and native
ComfyUI operators support them.

FP8 and INT8 are storage/operation families, not a guarantee that every file
uses the same loader or arithmetic. Native formats in the inspected ComfyUI
installation include:

| Format | Notes |
| --- | --- |
| FP8 E4M3 | Native scaled FP8 and ordinary loader-managed FP8 are distinct paths |
| FP8 E5M2 | Weight-only/full-precision multiplication may be required; E5M2 × E5M2 is unsupported by the tested CUDA backend |
| MXFP8 | Block-scaled FP8; hardware-dependent kernel selection |
| NVFP4 | Hardware-dependent kernel selection |
| INT8 | Tensor-wise, per-channel and ConvRot configurations differ |
| ConvRot W4A4 | Rotated INT4 weights/activations; requires compatible layer dimensions |
| Asymmetric W4A8 INT8 | Grouped low-bit weights with INT8 activation arithmetic |
| W6A8 INT8 | Grouped reduced-precision weights with INT8 activation arithmetic |

Supported storage does not imply accelerated arithmetic on every GPU. Native
operators can dequantize individual layers when the installed GPU/backend cannot
run the compressed matrix operation. The RS bridge leaves that decision to the
loader and ComfyUI; it does not replace the whole model with dense weights.

Normal/Precision selection keeps its existing family and adapter restrictions.
A Normal selection can fall back to Precision; inspect the effective mode and
fallback reason in saved metadata. Strength zero bypasses the adapter. Original
storage and temporary dispatch must survive successful and failed executions.

## GGUF and external engines

See [GGUF compatibility](gguf-compatibility.md) for the separate ComfyUI-GGUF
loader, packed GGML tensors and its measured scope. The native packed-tensor path
is not an implementation of Nunchaku, Quanto, bitsandbytes or another custom
execution engine. Those engines remain unverified and are not enabled by this
change. A shared bit width does not establish execution compatibility.

## Validation and quality

The optional native tests compare real INT8, FP8 E4M3 and FP8 E5M2 layer
operations and regional LoRA output against an independent dense low-rank delta
for eight model classes. They also verify positive/negative strength, exact zero,
removal, packed bytes and dispatch restoration. GPU probes additionally exercise
the nine available native quantization configurations, including ConvRot INT8.
Layer probes are numerical tests rather than full-image quality evaluations.

Full-image generation and full-graph smoke tests are recorded separately in the
local validation report. Converted checkpoints are technical compatibility
probes. They are not calibrated release models: indiscriminate INT8 conversion
of Anima produced visibly degraded results even when inference succeeded.
Prefer a model author's validated quantized release over converting all layers
or repeatedly requantizing a previously quantized checkpoint.

The loader/quantizer retains responsibility for sensitive layers, group sizes,
activation scales, precision settings and architecture recognition. This
extension supplies no checkpoint quantizer.

### Live audit: 2026-10-23

| Model family | Full-step native / scaled FP8 / INT8 | Additional full-step probe |
| --- | --- | --- |
| Anima | Native, FP8 E4M3, INT8 tensor-wise and per-channel | Loader-managed FP8, GGUF Q4_0 |
| SDXL / Illustrious | Same four configurations | Loader-managed FP8, GGUF Q4_0 |
| SD1.5 | Same four configurations | Loader-managed FP8, GGUF Q4_0; quality remains unstable |
| FLUX.1 | Same four configurations | Distributed GGUF Q4_K_S in the preceding audit |
| FLUX.2 Klein 4B | Same four configurations | — |
| FLUX 3 | Same four configurations | — |
| Krea2 | Same four configurations | — |
| MOSS | Same four configurations | — |

The full-step matrix exercises regional character adapters, exact zero strength,
adapter removal, Normal selection, masks, incoming global adapters and actual
face corrections. Detailer runs must select and use a character adapter on at
least one corrected face. Normal mode is checked through the real LoRA node,
including the requested/effective mode and existing family fallback reason.
Representative packed-byte hashes and layer dispatch are audited before/after;
this is not a hash of every parameter. Global adapters retain the incoming
loader's own patch/requantization behavior.

Each of the eight families additionally runs FP8 E5M2, NVFP4, MXFP8, ConvRot
W4A4, asymmetric W4A8, W6A8 and ConvRot INT8 through a two-step whole graph,
with no adapter, a character adapter and exact zero strength. These runs verify
execution and restoration; two steps do not establish finished-image quality.
Sensitive model-detection projections remain dense in the converted fixtures.
Anima's sensitive input/output and early layers also remain at their original
precision. Those fixtures are not quantized releases or a checkpoint converter
provided by this extension.

The sampler is Euler ancestral / SGM uniform, seed 346751 and two adult subjects.
Resolution is 768 × 512 (SD1.5: 512 × 512). Anima runs 30 steps;
SDXL/SD1.5/FLUX.1/MOSS run 20, and the remaining families run eight. Native
means the original loader format, which may itself already be quantized.
The three added Q4_0 files are locally converted probes; the earlier FLUX.1
Q4_K_S is a distributed model. Other families' GGUF full checkpoints remain
untested. Text encoders and VAE keep their matching model loaders and are not
part of the diffusion-weight conversion matrix.

Nine real native layer formats are also tested on both RTX 4070 Ti SUPER and
RTX 5060 Ti, across eight model classes, against an independent low-rank delta.
This is layer algebra on both devices, not the full image matrix on both GPUs.
Baselines and adapter calls use the same inference mode because kernel choices
can differ between inference and gradient-enabled execution, notably NVFP4.

Some SDXL/SD1.5 controls differed between their first and repeated no-adapter
calls. Zero/removal comparisons therefore use the repeated control, whose graph
and receipt are also retained. Timings and process memory peaks include different
loading/cache states and are not a controlled performance benchmark.
The plain SD1.5 FP8 sample lost subject separation; successful execution alone
does not make that conversion recommendable.

The local `RS_MC_quantization_validation_20261023` evidence bundle contains
submitted graphs, receipts, ComfyUI histories, outputs, mode/routing metadata,
storage audits, numerical probes, regression logs and archived failed fixtures.
`EVIDENCE-AUDIT.json` independently checks those artifacts. They are not bundled
with a normal extension installation.

## Sources

- [ComfyUI native quantization layouts](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy/quant_ops.py)
- [ComfyUI native layer operations](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy/ops.py)
- [Comfy Kitchen](https://github.com/Comfy-Org/comfy-kitchen)
- [ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF)
