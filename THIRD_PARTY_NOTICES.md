# Third-party notices and lineage

The routing implementation was developed in the author's local research branch of `ComfyUI_RS_NAI_API_Request` and extracted into this independent repository. Original source hashes are recorded in `docs/source-lineage.json`. Copyright notices and GPL-3.0-only licensing are retained.

The runtime depends on ComfyUI, PyTorch, NumPy and Pillow under their respective licenses. Model and LoRA weights are not included; their licenses remain separate.

Local detailing adapts the author's existing mask repair, detector catalog, download progress and character matching from `ComfyUI_RS_NAI_API_Request`. Original file hashes and the source commit are recorded in [detailer lineage](docs/detailer-source-lineage.json). The local sampling adapter uses ComfyUI's `common_ksampler`; it does not call NovelAI. Detection providers come from separately installed [ComfyUI-Impact-Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack) and [ComfyUI-Impact-Subpack](https://github.com/ltdrdata/ComfyUI-Impact-Subpack). Their implementations and weights are not bundled. Optional tagger implementations and weights retain their own licenses; model download locations and reviewed revisions are recorded in the tagger loader source.

Research references, not copied implementations:

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI): Anima model, sampler wrappers and conditioning interfaces.
- [Comfyui-Anima-Regional-Conditioning](https://github.com/Sen-sou/Comfyui-Anima-Regional-Conditioning): regional conditioning concept reference.
- *Be Yourself: Bounded Attention for Multi-Subject Text-to-Image Generation* (ECCV 2024): bounded attention concept reference.
- NovelAI V4 image caption layout: interoperability field names (`v4_prompt`, `v4_negative_prompt`, `char_captions`, `centers`). This extension is independently developed and does not identify its local outputs as NovelAI-generated.
