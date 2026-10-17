# 0.1.5 Epsilon

Epsilon adds boxes alongside the existing X/Y character regions. Two characters
can use points while a word or prop uses a box in the same generation. Eight
editable model-family presets copy tested sampler and regional settings into the
existing controls.

## Included changes

- Point, box and mixed layouts, with center/size controls and an on-node preview.
  Explicit boxes take priority over point regions; overlap and common-only
  background are handled by regional attention.
- Literal text regions, separate from character captions and face matching.
  Up to ten active regions in total. MOSS also has an experimental native layout
  mode requiring boxes for every region.
- Eight presets covering Anima XY/mixed, SDXL/Illustrious XY/mixed, Krea 2 Turbo,
  MOSS base/8-step LoRA and experimental SD1.5. Applying a preset is explicit;
  manual edits survive saving and reopening a workflow.
- PNG/WebP restoration of boxes, mixed geometry and text, while preserving old
  point workflows. Normal autosave retains generation metadata without embedding
  a ComfyUI workflow.
- Tuned model examples, English/Korean/Japanese README and UI guidance, and
  [20 two-person object examples](../examples/epsilon/objects) using the existing
  Anima mixed and Krea presets.

The package version is **0.1.5** and the visible release name is **Epsilon**.
The standard Python maturity classifier remains Beta. Model files and optional
detector dependencies are obtained separately; this release does not bundle them.

## Validation scope

The [initial implementation record](epsilon-validation.md) contains 27 actual
generation runs covering box swaps, sizes, overlaps, mixed text, MOSS native mode,
metadata replay and browser execution. The later [model tuning](mixed-layout-tuning.md)
records 49 runs, including three final seeds per tuned model. The [preset checks](model-presets-validation.md)
cover eight choices and 95 browser assertions; an Anima preset generation matched
the earlier tuned image pixel for pixel. The [object trial](object-layout-validation.md)
adds ten objects on each of Anima and Krea 2. These evidence sets have distinct
purposes and are not a combined image-quality success-rate measurement.

Release regression checks use real ComfyUI source trees with small CPU models:

| ComfyUI | Python result | Scope |
|---|---|---|
| `5cc4b870094c89090db54bd8d12649dcaf89f2ba` | 95 passed | Current model integrations and package tests |
| `v0.3.76` | 88 passed, 7 skipped | Older API; unavailable architectures skipped |

Four JavaScript suites cover character controls, boxes, detailer controls and
presets. The object workflow/API exports preserve the executed generation inputs;
only the terminal test logger is removed from public API graphs. Original trial
image and request hashes were verified before packaging.

Per-commit Linux/Windows results are available in
[Compatibility tests](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/actions/workflows/tests.yml).
Registry publishing uses the existing
[publish workflow](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/actions/workflows/publish.yml);
a successful upload is distinct from Registry activation and Manager cache refresh.
This source release does not itself replace an already running local installation.

## Limits

Boxes influence prompt regions, not exact object silhouettes. Text can be
misspelled or extend beyond its rectangle. Anima/Krea object trials recognized
all requested objects, but whole-object containment was 1/10 for each model;
Anima had more disconnected scenes and Krea often ignored the anime style.
SD1.5 remains experimental and unstable: its acceptance criterion is distinguishable
people and visible lettering, not natural anatomy or accurate spelling.

Object examples use generic character slots and are not automatically excluded
from face matching. Live detailing with the new text-containing pipe was not
revalidated; unit tests cover text exclusion and metadata retention. MOSS native
mode ignores the regional strength schedule and requires a MOSS-capable core.
Exact counts, character identity and complex interactions remain model-dependent.
