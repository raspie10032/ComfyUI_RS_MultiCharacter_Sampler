# Third-party notices and lineage

The routing implementation was developed in the author's local research branch of `ComfyUI_RS_NAI_API_Request` and extracted into this independent repository. Original source hashes are recorded in `docs/source-lineage.json`. Copyright notices and GPL-3.0-only licensing are retained.

The runtime depends on ComfyUI, PyTorch, NumPy and Pillow under their respective licenses. Model and LoRA weights are not included; their licenses remain separate.

Research references, not copied implementations:

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI): Anima model, sampler wrappers and conditioning interfaces.
- [Comfyui-Anima-Regional-Conditioning](https://github.com/Sen-sou/Comfyui-Anima-Regional-Conditioning): regional conditioning concept reference.
- *Be Yourself: Bounded Attention for Multi-Subject Text-to-Image Generation* (ECCV 2024): bounded attention concept reference.
- NovelAI V4 image caption layout: interoperability field names (`v4_prompt`, `v4_negative_prompt`, `char_captions`, `centers`). This extension is independently developed and does not identify its local outputs as NovelAI-generated.
