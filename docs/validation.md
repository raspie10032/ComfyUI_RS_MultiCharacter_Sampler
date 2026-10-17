# Alpha validation — 2026-10-16

For the current **0.1.2 Beta**, see [release notes](release-0.1.2.md), [detailer validation](detailer-validation.md), [SDXL validation](sdxl-validation.md), and [Krea 2 / MOSS validation](krea-moss-validation.md). The original alpha evidence below is retained with its original scope.

This report separates inherited research evidence, standalone runtime checks, source tests and UI checks. It does not claim universal success rates or equivalence to NovelAI.

The subsequent **2026-10-17 sampler/scheduler matrix** covered all 405 combinations in the installed ComfyUI inventory. See [sampler combinations](sampler-combinations.md) for settings, observed quality failures and three suggested starting points. All installed choices are now exposed; execution success does not guarantee image quality.

## Environment and isolation

Linux ComfyUI 0.34.0 (`15eb748b3ec5f8a0a2d470b7fb280e2d7579f916`), Python 3.12.14, frontend 1.51.9. A separate runtime on port 8194 loaded only this extension plus ComfyUI core nodes. The RS NAI package was not present in that custom-node directory. All three new node classes registered successfully.

The regular installation and research source branch were kept separate. No NAI requests or Anlas were used. Model and private LoRA files are not included in this repository.

## Existing research trial

Before extraction: 12 predeclared scenes × 2 random seeds, with target counts from 1 through 6; 24 images total. Three additional controls kept the prompt and seed fixed and changed only X or Y. Anima Base v1.0 + RSC/MyMy 80:20 LoRA at 1.0, Euler ancestral/SGM uniform, 30 steps, CFG 4, and the default schedule described in architecture.md.

| Target count | Images | Main-person count correct | No extra background people either | Major hair identity and relative layout all correct |
| --- | --- | --- | --- | --- |
| 1 | 4 | 4 | 2 | 4 |
| 2 | 4 | 4 | 4 | 4 |
| 3 | 4 | 2 | 2 | 2 |
| 4 | 4 | 2 | 2 | 2 |
| 5 | 4 | 2 | 2 | 2 |
| 6 | 4 | 2 | 2 | 2 |

Counts and identity/layout are manual image readings, not an automated accuracy metric. Passing these columns does not imply correct eyes, clothing, props, actions or interactions. Samples were retained rather than rerolled after failure. Dense 2×2 layouts (4 requested) produced 12 and 10 people; 6-person two-row layouts produced 7 and 11. The two 6-person horizontal scenes retained six people. The five-person center/corners camp scene omitted its center subject in one sample. These failures define important alpha limits.

All 27 completed histories matched the submitted requests. Actual runtime traces showed the requested number of regions, 30 sampler evaluations, 840 cross/self attention calls, restored forwards and the same configured schedule. LoRA application was checked against the research baseline.

Coordinate controls: swapping X exchanged the two cafe characters; swapping Y exchanged the two balcony characters even with conflicting location words. Clothing could still transfer between characters. Moving the center of a single-character image produced exactly identical pixels and intermediate latents, consistent with the one-region implementation.

## Standalone generation and metadata replay

A two-person cafe request was repeated using the independent package with the same local assets, seed, dimensions and sampling settings. Its PNG pixels matched the pre-extraction result exactly.

That PNG was then loaded through **RS MultiCharacter Load Image**, with deliberately wrong sampler prompt/seed/size widgets and `use_image_settings=true`. Generation restored the saved settings and produced exactly the baseline pixels, saved as lossless WebP. A further actual generation read that WebP through the same node and completed successfully, saving lossy WebP. The bundled example API workflow also completed an actual generation without the private LoRA; its output is included as `examples/two-characters-result.png`. Four standalone generations completed in total. Lossy compression is not expected to preserve original pixels.

The native PNG and both WebP forms preserve common/character text, XY and local sampling settings in tests, including Korean/Japanese text and an integer seed larger than 2^53. No workflow graph is present in autosaved metadata. The tests also cover plain NAI-shaped captions, mismatched rows, malformed/oversized/nonfinite metadata, unsupported versions and missing metadata.

## Source and UI checks

42 Python tests cover routing arithmetic, token ownership, duplicate-coordinate fallback, active-slot filtering, validation, model-loader metadata whitelisting, serialization and error paths. A JavaScript check covers dynamic character slot visibility, restoring hidden widget values and stable serialization order. These are source-level checks, not replacements for actual generation.

Firefox loaded the provided workflow without missing nodes and showed exactly two character slots; a five-slot variant showed five. The JavaScript test additionally covers reducing/restoring the count in place. Installation on the user's ordinary resident server and Windows execution are separate from this isolated alpha validation.

## Reproducibility artifacts

The repository includes the implementation, source-lineage hashes, tests, example UI/API workflows, the two-character example output and this report. Full 27-image research outputs, intermediate latent traces and actual API histories remain in the original local research artifacts; they are not redistributed with this package. Model and private LoRA weights are not bundled.

[Compact runtime evidence](runtime-evidence.json) records prompt IDs and file hashes without machine paths.
