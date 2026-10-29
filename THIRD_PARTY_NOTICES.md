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

## Camera control references

- **Article:** [Anima camera-tag helper](https://arca.live/b/aiart/179423561), supplied by the user as the camera-control reference.
- **Inspected package:** `ComfyUI-KR-Camera-Control`. Its README and source headers attribute its camera prompt algorithm and interaction design to `ComfyUI_bsk_UI`, Copyright © 2026 灰暗x, and identify the inspected package as `AGPL-3.0-or-later`. This records the inspected package's attribution; it does not establish the current licensing of every upstream version.
- **Reference scope:** camera-direction/framing tags, interactive camera controls, default weights and boundary behavior were studied and compared. The RS/NAI implementation uses its own continuous caption-weight formulas, seeded random views, shared-context integration and flat-plane region transforms. See the [camera guide](docs/camera-control.md) for formulas and limitations.
- **Distribution:** the inspected package's source, archive and assets are not bundled. Its license is not a grant for model weights or external services. The two RS extensions share their own camera implementation under their existing GPL-3.0-only license.

### Features incorporated from the camera reference

| Studied feature in `ComfyUI-KR-Camera-Control` | Integration in RS Camera Control and NAI Camera Control |
| --- | --- |
| Horizontal direction converted into front/side/rear prompt tags | Azimuth controls generate weighted front, left/right-side and rear captions for the common scene and, optionally, each character. |
| Vertical direction converted into above/below view tags | Elevation controls blend above/below captions, including overhead and worm's-eye endpoints. |
| Distance converted into five framing categories | The same framing vocabulary—extreme close-up, close-up, medium shot, full body and wide shot—is exposed on a 0…1 distance control. |
| Roll expressed through `dutch angle` | Roll generates a weighted tilt caption; optional RS layout sync also rotates character regions. |
| In-node drag/wheel interaction and prompt preview | Drag changes the view, wheel changes distance, Shift+wheel changes roll, and the panel displays caption weights and the executed camera prompt. |
| Weighted/plain prompt output, presets and random-view controls | RS provides weighted/plain captions, view preset buttons and reproducible seeded random views with balanced/full ranges. Its randomization is independent of the generation seed. |

The reference's per-axis default weight of 5, dead zones, discrete category transitions, editable preset library and extra lens/DoF/movement settings were inspected; these are not reproduced as an identical settings system. RS uses its own continuous blend formulas, degree-based axes and default strength 1.2. It does not reproduce the reference's separate draggable 3D preview camera.

**RS/NAI additions:** shared character-pipe/context input and output; ComfyUI/NovelAI caption syntax selection; scene/character caption routing; preservation of prompts, LoRAs and local region records; synchronized point/box/silhouette/body-part zoom, roll and flat-plane perspective; and transformed-region previews. Native NAI requests receive captions and character centers, while local silhouettes remain in the context for round trips. These additions are not attributed to the reference as existing features. Neither caption control nor flat-plane projection reconstructs a 3D person or guarantees a pose.


## Progressive resolution references

[SPEED](https://howardxiao.ca/speed/), its [research code](https://github.com/howardhx/speed) and [ComfyUI-SPEED](https://github.com/ruwwww/ComfyUI-SPEED) were studied and compared for frequency-preserving expansion, noise/time correction and expansion timing. RS Lanczos expansion and resolution-aware character separation predate that comparison. The shipped progressive sampler uses the preceding RS Lanczos design and native ComfyUI noise scaling, not the external DCT expansion implementation. No SPEED source is bundled in this node. See [the feature guide](docs/progressive-resolution.md).

## Anima clean reference-frame adapter (experimental)

`anima_ref_frame.py` adapts reference-frame RoPE offsets, conditional adapter application and reference/APG guidance from [ElectronGirl/ComfyUI-Anima-Ref-Adapter](https://github.com/ElectronGirl/ComfyUI-Anima-Ref-Adapter) at `af9a438d` (Apache-2.0). The full license is preserved in `ANIMA-REF-ADAPTER-LICENSE`. RS integration adds generation-scoped lifecycle, bounded text K/V reuse, regional target-token routing and LoRA isolation. Weights are not redistributed and retain their own license.

## Regional reference backend update

The common numbered Image Reference input now uses ElectronGirl reference frames
for Anima, conradlocke Identity Edit v2 for Krea 2, and ComfyUI native reference
latents for FLUX (Kontext for FLUX.1). RS adds slot-specific captions, region
ownership and repeated-prior sharing. The SD1.5/SDXL IP-Adapter and MOSS PoC
paths are retained. The earlier Anima IP-Adapter and Redux source notices remain
for retained historical helper modules; these are not the new default paths.
The linked model repositories and pinned revisions are in `reference_assets.json`.


## Anima Role Ref K/V (experimental)

`anima_role_native.py` adapts `comfyui/native.py` from
https://huggingface.co/AnticPan/Anima-Role-Ref-KV at
`259a0dce876ed70fc8835b888139756e23fb8a9f` (Apache-2.0). The original license
is preserved in `ANIMA-ROLE-KV-CODE-LICENSE` and `ANIMA-ROLE-KV-MODEL-LICENSE`; the pinned weight revision is also in
`reference_assets.json`. The adapter weights are downloaded by the user, not
redistributed. RS adds separate numbered reference banks, point/box/mask
ownership, overlapping-reference selection, conditional-only reference access,
invocation-scoped cleanup and progressive-grid cache rebuilding.
Original discussion: https://arca.live/b/aiart/187357665 .


## Anima asymmetric reference v2

The experimental `anima_ref_v2.py` implementation additionally adapts asymmetric
reference block/frame math from ElectronGirl/ComfyUI-Anima-Ref-Adapter at
`bd1e094a` under Apache-2.0 (preserved in `ANIMA-REF-ADAPTER-LICENSE`). RS adds
independent numbered regional predictions, rectangular target attention and
sample-scoped K/V cache invalidation/cleanup. The separately downloaded v2
weights retain their upstream terms. See `docs/anima-reference-v2.md`.

## Anima 2.9B converted reference adapter

The expanded-model reference path uses [Gazingstars123/Anima-2.9B](https://huggingface.co/Gazingstars123/Anima-2.9B) insertion positions and [pamparamm/anima-ref-adapter-2.9B-converted](https://huggingface.co/pamparamm/anima-ref-adapter-2.9B-converted). RS selects the matching adapter by architecture, validates its exact mapped modules and leaves the 12 inserted blocks without reference-adapter hooks. These blocks still execute normally. No weights are redistributed. Adapter revision and SHA256 are pinned in `reference_assets.json`; model and weight licenses remain separate from this code.

## 3D pose editor

- Three.js 0.170.0 (MIT), including OrbitControls and TransformControls, is included in the offline editor bundle. Copyright and permission text: [THREE-LICENSE.txt](web/pose3d/THREE-LICENSE.txt).
- Design references: [ZhUyU1997/open-pose-editor](https://github.com/ZhUyU1997/open-pose-editor), revision 8e659f1f1995715621ac3f50d9c34d55faf5296d; [hinablue/ComfyUI_3dPoseEditor](https://github.com/hinablue/ComfyUI_3dPoseEditor), revision 582c5b1410d5bd5a91465f05796f4e99a690cc52. Both MIT. Their source, mannequin assets and capture pipeline are not bundled; our scene/geometry/projection and RS integration are implemented separately.


## Native 3D human rig

New v2 scenes use the adult LOD1 MHR body baked and distributed by [toyxyz/ComfyUI_toyxyz_test_nodes](https://github.com/toyxyz/ComfyUI_toyxyz_test_nodes), revision `8291d9b65d56d65be55ee0f31df073d42b7d0eb6`. The underlying [Meta MHR](https://github.com/facebookresearch/MHR) asset is Apache-2.0. RS retains the native bind transforms and skinning, omits the SAM facial landmark mapping and learned pose correctives, and supplies independent browser/CPU skinning, numbered masks and pose shading. Attribution and terms accompany the gzip asset in `web/pose3d/MHR-NOTICE.txt` and `MHR-LICENSE.txt`. Legacy v1 scenes retain RS procedural ellipsoids. No inference weights are bundled.
