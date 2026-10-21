# Third-party notices and lineage

The routing implementation was developed in the author's local research branch of `ComfyUI_RS_NAI_API_Request` and extracted into this independent repository. Original source hashes are recorded in `docs/source-lineage.json`. Copyright notices and GPL-3.0-only licensing are retained.

The runtime depends on ComfyUI, PyTorch, NumPy and Pillow under their respective licenses. Model and LoRA weights are not included; their licenses remain separate.

Local detailing adapts the author's existing mask repair, detector catalog, download progress and character matching from `ComfyUI_RS_NAI_API_Request`. Original file hashes and the source commit are recorded in [detailer lineage](docs/detailer-source-lineage.json). The local sampling adapter uses ComfyUI's `common_ksampler`; it does not call NovelAI. Detection providers come from separately installed [ComfyUI-Impact-Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack) and [ComfyUI-Impact-Subpack](https://github.com/ltdrdata/ComfyUI-Impact-Subpack). Their implementations and weights are not bundled. Optional tagger implementations and weights retain their own licenses; model download locations and reviewed revisions are recorded in the tagger loader source.

Research references, not copied implementations:

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI): Anima model, sampler wrappers and conditioning interfaces.
- [Comfyui-Anima-Regional-Conditioning](https://github.com/Sen-sou/Comfyui-Anima-Regional-Conditioning): regional conditioning concept reference.
- *Be Yourself: Bounded Attention for Multi-Subject Text-to-Image Generation* (ECCV 2024): bounded attention concept reference.
- NovelAI V4 image caption layout: interoperability field names (`v4_prompt`, `v4_negative_prompt`, `char_captions`, `centers`). This extension is independently developed and does not identify its local outputs as NovelAI-generated.

## Experimental image references (0.2.5 Mieum)

- `sd_resampler.py` adapts Tencent AI Lab's [IP-Adapter resampler](https://github.com/tencent-ailab/IP-Adapter/blob/62e4af9d0c1ac7d5f8dd386a0ccf2211346af1a2/ip_adapter/resampler.py). Original headers retained; Apache-2.0 text in `IP-ADAPTER-LICENSE`. Its headers cite OpenFlamingo and imagen-pytorch. Regional routing and lifecycle integration were modified for this extension.
- `anima_reference.py` adapts the learned residual and helper-LoRA application in [ComfyUI-Anima_IP-Adapter](https://github.com/LuciferTC9527/ComfyUI-Anima_IP-Adapter/tree/6b77cd0c367d76402174ace2be50d3cb6aa77855). Apache-2.0 text is in `ANIMA-IP-ADAPTER-LICENSE`. CFG handling, per-character regions, shared-model restoration and resolution handling are modified.
- `krea_reference_backend.py` adapts [lbouaraba/comfyui-krea2edit](https://github.com/lbouaraba/comfyui-krea2edit). Its original header and Apache-2.0 license are preserved in `KREA2EDIT-LICENSE`; reference ordering, regional positions and wrapper lifecycle are modified.
- SD attention, Redux conditioning and FLUX native reference paths use ComfyUI's installed runtime. MOSS/Krea edit weights are downloaded separately; no third-party custom-node runtime import is required.

Weight repositories, pinned revisions and download hashes are in `reference_assets.json`. Weight licenses are separate from extension code, are not granted by this repository's GPL-3.0 license, and must be checked at the linked model repositories. No weights or reference pictures are distributed with the extension.
