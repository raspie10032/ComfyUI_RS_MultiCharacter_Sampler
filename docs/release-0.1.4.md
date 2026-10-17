# 0.1.4 Delta

This release packages MOSS-Image SFT 8-step LoRA examples and the retained real
generation comparison. It uses the existing MOSS sampler path and ComfyUI's
standard model-only LoRA loader. It does not introduce a new sampling algorithm.

## Changes

- Two-character and four-character XY workflows, each with CFG 3 and CFG 1
  variants, plus corresponding API graphs.
- [Asset sources, setup, measurements and comparison images](moss-8step.md).
- English, Korean and Japanese README instructions for the 8-step setup and the
  required MOSS-capable ComfyUI core.
- Package version and visible release labels updated to 0.1.4 Delta. The Python
  development classifier remains Beta because it has no Delta category.

The six node class IDs, input order/defaults, output types and metadata contract
are retained. Existing workflows keep their sampler settings. Experimental,
unstable SD1.5 support and the documented count/identity limitations remain.

## Validation scope

The original comparison consists of eight 0.1.3 generations and one replay with
measurement nodes removed, on ComfyUI 0.41.0. The [LoRA report](moss-8step.md)
records the precise revision, settings, timings and observed failures. It is not
a general quality or success-rate claim.

Checks against real ComfyUI source trees:

| ComfyUI | Python tests | Scope |
| --- | --- | --- |
| `v0.3.76` | 69 passed, 3 skipped | Older API; absent model architectures skipped |
| `5cc4b870094c89090db54bd8d12649dcaf89f2ba` | 72 passed | Native CPU integrations for Anima, SDXL, SD1.5, Krea 2 and MOSS |

Both JavaScript UI suites passed. The six installed node schemas retain the same
inputs, order, defaults and output types. CPU integrations use small models;
they do not constitute GPU image-quality tests. Per-commit remote Linux and
Windows results are available in
[Compatibility tests](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/actions/workflows/tests.yml).

## Installed Linux runtime

The resident ComfyUI was upgraded from 0.34.0 (`15eb748`) to the tested 0.41.0
revision (`5cc4b87`), with frontend 1.55.17 and matching core dependencies. Core,
package and dependency state were backed up; 27 existing workflow files retained
their original hashes. Four additional MOSS example workflows were installed.
The existing PyTorch/CUDA build was retained.

Real requests on the normal server, with an RTX 4070 Ti SUPER:

| Request | Outcome |
| --- | --- |
| MOSS two-character, 8 steps, CFG 3 | Image saved, 1024×768 |
| MOSS two-character, 8 steps, CFG 1 | Image saved, 1024×768 |
| MOSS four-character XY, 8 steps, CFG 3 | Image saved, 1024×1024 |
| MOSS four-character XY, 8 steps, CFG 1 | Image saved, 1024×1024 |
| Existing Anima generation → face detailer | Image saved, 1536×768; 2/2 regions corrected |
| MOSS output → extension image loader | Four captions, XY centers and generation settings restored |
| Anima detailer output → extension image loader | Two captions, centers and original generation settings restored |

The four MOSS requests used the published API examples without private nodes.
The two CFG 3 outputs were visually checked for count, layout and attributes;
the four-character blonde still omitted the blue cup. This is runtime acceptance
of these examples, not a repeat of the original performance benchmark. MOSS
8-step LoRA detailing and GPU generation on Windows were not tested.

The core upgrade removed the separate built-in `OpenAIVideoSora2` API node;
none of the 27 preserved workflows references it. No RS MultiCharacter node was
removed. All generations in this release check were local; no Anlas was spent.
