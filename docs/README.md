# Documentation / 문서 모음 / ドキュメント

[English README](../README.md) · [한국어 README](../README.ko.md) · [日本語 README](../README.ja.md) · [Changelog](../CHANGELOG.md)

Start with your language's README for installation and a first workflow. This
index groups detailed guides and evidence by task. Release notes describe changes
at a particular version; current usage belongs in the feature guides below.

## Usage guides

| Task | Guide | Examples |
| --- | --- | --- |
| Build character settings | [Modular Prompt / LoRA / Position / Finalize](modular-characters.md) | [Two-character Anima](../examples/modular/two-characters-anima.json) |
| Choose starting settings | [Model presets](model-presets.md) · [Anima sampler/scheduler comparisons](sampler-combinations.md) | [Model preset catalog](../web/model_presets.json) |
| Apply character LoRAs | [LoRA setup and cost](regional-lora.md) · [Normal/Precision modes](shared-lora-experiment.md) · [Adapter formats and limits](adapter-formats.md) | [Character LoRA](../examples/character-lora/README.md) |
| Place points, boxes, words or objects | [Regional layouts](regional-layout.md) · [Model-specific mixed settings](mixed-layout-tuning.md) | [Mixed layouts](../examples/epsilon/README.md) · [Objects](../examples/epsilon/objects/README.md) |
| Draw or import masks | [Character masks and placement](character-masks.md) | [Mask examples](../examples/character-masks/README.md) |
| Use pose-derived masks | [OpenPose inputs, previews and overlap controls](openpose-mask-guides.md) | [Pose examples](../examples/openpose/README.md) |
| Use MOSS acceleration | [MOSS 8-step LoRA setup](moss-8step.md) | [Two characters, CFG 3](../examples/moss-8step/two-cfg3.json) |
| Detail detected characters | [Behavior, execution and limits](detailer-validation.md) | [Generation + detailer](../examples/two-characters-detailer-anima.json) |
| Try image references · not recommended | [Backends, optional dependencies and limits](image-reference.md) | [Experiment report assets](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/releases/tag/v0.2.5) |
| Restore image settings or inspect implementation | [Architecture and metadata](architecture.md) · [Source lineage](source-lineage.json) | [Workflow PNG](../examples/two-characters-workflow.png) |

## Validation reports

These reports have different scopes. A CPU integration or finite GPU forward does
not establish image quality; a small image trial does not establish a success
rate across prompts, seeds, checkpoints or adapters. See each report's settings
and limits before generalizing its result.

| Scope | Reports |
| --- | --- |
| Core/API compatibility and CI | [Compatibility snapshots](compatibility.md) · [CI workflow](../.github/workflows/tests.yml) |
| Initial Anima generation and metadata | [Original validation](validation.md) |
| SDXL and SD1.5 generation | [SDXL](sdxl-validation.md) · [SD1.5: unstable](sd15-validation.md) |
| Krea 2, MOSS and FLUX generation | [Krea 2 / MOSS](krea-moss-validation.md) · [MOSS acceleration](moss-8step.md) · [FLUX variant matrix](flux-validation.md) |
| Character-LoRA generation | [Initial per-character checks](regional-lora-validation.md) · [Anima factor-only path](regional-lora-bypass-validation.md) · [Cross-model combinations](character-lora-matrix-20261021.md) |
| Adapter algebra and quantized MOSS forwards | [Formats, numerical checks and boundaries](adapter-formats.md) |
| Normal/Precision comparison | [Shared LoRA experiment](shared-lora-experiment.md) |
| Mixed layouts and presets | [Epsilon trial](epsilon-validation.md) · [Mixed-layout tuning](mixed-layout-tuning.md) · [Objects](object-layout-validation.md) · [Preset UI checks](model-presets-validation.md) |
| Masks and pose controls | [Mask drawing/placement checks](release-0.2.4.md) · [Pose and metadata checks](release-1.0.0.md) · [OpenPose PNG correction](openpose-png-validation.md) |
| Local detailing | [Execution, matching and pixel boundaries](detailer-validation.md) |

## Release history

Use the [changelog index](../CHANGELOG.md) for versioned changes and the detailed
notes retained in this directory. [GitHub Releases](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/releases)
holds published packages and report attachments.
