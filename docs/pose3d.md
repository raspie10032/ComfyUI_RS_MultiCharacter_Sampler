# Experimental 3D Pose Masks

Arrange native skinned MHR bodies in a local 3D editor, then use their camera-projected silhouettes as numbered character regions. Editing and masks need no inference weights, external service or runtime CDN. Pose conditioning uses a separately trained compatible adapter. Three.js is bundled with the extension.

1. Add **RS 3D Pose Masks (Experimental)**. Drop a one-person PNG/JPEG/WebP (under 20 MB) onto the **Image → 3D** panel, or click to select it. Estimation runs automatically in the ordinary ComfyUI queue, saves the source camera/crop and opens the 3D editor; no separate Load Image/estimator connection or extra Queue/Apply is needed. This replaces the node's current scene with one estimated person. For manual posing, use **Open 3D editor** instead.
2. Choose a character number matching the Prompt/LoRA slot. Add or copy up to ten people. Numbers stay fixed when people cross; renumber explicitly to change the assignment.
3. Click a joint and drag its colored rings, or select a joint and use the XYZ sliders. Choose **Move person** to drag the whole person. Height and body-width controls change that person's silhouette.
4. Drag empty space to orbit the output camera; right-drag pans, the wheel zooms. Use Front/Side/Back to reset the view and set canvas dimensions (64–2048 pixels per side).
5. Choose **Full silhouettes** to keep overlapping character regions, or **Visible silhouettes** to subtract regions hidden behind other people. The small preview shows the actual CPU mask projection.
6. Click **Apply to node**. Connect its `building_pipe` anywhere before **Finalize**, along with the Prompt, LoRA and Position nodes. Finalize still determines the active prompt slots. Set the sampler to the same aspect ratio as the editor; other aspect ratios stretch the normalized masks.

The node outputs its mask preview and two MASK batches (full/visible), sorted by character number. The chosen mode only selects which masks enter the building pipe. `scene_info` lists the batch's character IDs. Scene JSON is stored in the node's workflow widget. Save/load scene buttons also allow an independent JSON backup.

[Drop-in workflow PNG](../examples/pose3d/anima-native-pose.png) · [Example requirements](../examples/pose3d/README.md)

## Experimental pose-adapter path

The `pose_image` output renders shaded colored bodies on black using the same scene, camera, depth ordering and aspect ratio as the masks. It excludes editor handles and grids. Existing output indices are unchanged. A final `scene_json` STRING output additionally carries the same editable scene to the Krea2/MOSS adapter. Earlier output indices remain unchanged. The pose signal is separate from the character building pipe: connecting the pipe alone still supplies masks only.

For an experimental Anima 2B test, load compatible weights with ComfyUI's **Load Model Patch**, connect `pose_image` to **Apply Anima LLLite**, and feed its MODEL output to the RS sampler. The scene's building pipe still supplies numbered character masks. The sampler accepts complete native Anima LLLite patch groups while preserving RS routing, and rejects other attention replacements, mismatched adapter dimensions and simultaneous image references. Other model families' ControlNets, Anima 2.9B pose weights, progressive sampling and character-LoRA combinations have not been validated by this test.

New scenes use the bundled native MHR mesh, bind transforms, skin weights and procedural twist supports. Body, hand and finger controls deform the mesh. Scene format v2 is shared by the browser and CPU renderer; existing v1 ellipsoid scenes retain their original geometry and output. The renderer deliberately omits learned pose correctives and facial/body-shape inference.

A successful output connection is not evidence of reliable pose following. The initial ellipsoid tests failed. Native anatomical renders subsequently induced seated and raised-arm poses in controlled Anima 2B tests; the integrated editor tests also show raised-arm transfer, but frontal two-person seating remains unreliable. Hand contact, exact joints, appearance and subject counts remain model-dependent. See the [component comparison](pose3d-validation.md) for paired seeds and failures.

Tested with [toyxyz/Anima_ControlNet-LLLite](https://huggingface.co/toyxyz/Anima_ControlNet-LLLite), `anima_3dpose_outline_7000.safetensors`, strength 1, full denoising interval. This adapter expects anatomical shaded renders with outlines rather than OpenPose sticks. A matching Anima 2B base and a recent native ComfyUI Anima LLLite implementation are required. Load its weights separately with Model Patch Loader. Outline affects only the pose image, never silhouette ownership. The experimental node does not auto-download adapter weights.

## Boundaries

- The pipe alone guides composition and prompt ownership through 2D masks. Pose guidance is separate: connect pose_image through a compatible adapter to the sampler MODEL. The generation model never receives the 3D rig itself.
- New bodies use a native skinned adult MHR mesh and hand/finger controls. Legacy scenes keep ellipsoid bodies. Single-image pose estimation uses the optional SAM 3D Body path below. Clothing simulation, facial controls and video body tracking are not included.
- Masks outside the canvas are clipped. If a selected silhouette is entirely outside/behind the camera or fully hidden in visible mode, Apply/execution explains which character needs correction. Full mode can retain hidden characters.
- Moving a person does not change its prompt number. Prompt enable/count settings determine which numbered regions are used by generation.
- New 3D masks preserve incoming prompts, LoRAs, placement transforms and camera settings. Position before/after this node gives the same result. Later mask producers overwrite earlier masks for their slot.
- Deleting a person clears a mask previously owned by this 3D node only when that same mask is still present upstream. It does not erase a later replacement mask. Deleting from a scene also leaves the corresponding prompt setting intact; disable that prompt if you want fewer characters.
- The first version is local to the MultiCharacter extension. It does not install a separate editor in the NovelAI Request extension.

## References and build

Interaction design was studied from [Online 3D OpenPose Editor](https://github.com/ZhUyU1997/open-pose-editor) (MIT, inspected revision `8e659f1f1995715621ac3f50d9c34d55faf5296d`) and its [ComfyUI wrapper](https://github.com/hinablue/ComfyUI_3dPoseEditor) (MIT, inspected revision `582c5b1410d5bd5a91465f05796f4e99a690cc52`). Their external mannequin and capture dependencies were not imported. RS scene format, rasterizer and building-pipe integration are implemented here.

The native human asset is derived from the adult LOD1 MHR data bundled by [toyxyz/ComfyUI_toyxyz_test_nodes](https://github.com/toyxyz/ComfyUI_toyxyz_test_nodes), inspected revision `8291d9b65d56d65be55ee0f31df073d42b7d0eb6`. It retains native bind transforms and skinning; sparse SAM facial landmark mapping is excluded. MHR is Apache-2.0, with license and attribution in `web/pose3d/MHR-LICENSE.txt` and `MHR-NOTICE.txt`. The standalone gzip asset is about 1.1 MiB and needs no new Python dependencies.

[Three.js](https://github.com/mrdoob/three.js) 0.170.0 supplies the WebGL renderer, OrbitControls and TransformControls under MIT. Its license is distributed in `web/pose3d/THREE-LICENSE.txt`. Rebuild the checked-in offline bundle with `cd tools/pose3d && npm ci && npm run build`. Python has no new dependencies.

Tests: `RS_MC_TEST_COMFYUI=/path/to/ComfyUI PYTHONPATH=/path/to/ComfyUI python -m unittest discover -s tests -q`, then `node --test tests/*_ui.cjs` with the same Python environment on PATH. An optional real-browser regression is in `tools/pose3d/test-editor.mjs`; it needs Playwright and a separate running ComfyUI at port 8189 (or `RS_COMFY_URL`), with only this candidate enabled. Set `RS_CHROMIUM` when using an existing Chromium executable. It exercises joint controls, actual translation/rotation-gizmo dragging, camera orbit, IDs, undo/redo, scene files, workflow restore and editor network isolation.


## Krea2 Turbo and MOSS pose adapters (experimental)

1. Connect the model loader's MODEL and its matching VAE to **RS 3D Pose Adapter (Experimental)**.
2. Connect **RS 3D Pose Masks → scene_json** to the adapter's `scene_json` input.
3. Connect the adapter MODEL to the ordinary **RS MultiCharacter Sampler**. Continue sending the 3D node's `building_pipe` through Prompt/LoRA/Position and Finalize for numbered character regions. Building-node order is unchanged.
4. Keep the sampler and scene at the same dimensions/aspect ratio. Start with strength 1 and the full application interval. MOSS can retain mannequin surfaces; compare an end of 0.5 if needed. These are experimental controls, not reliability presets.

Krea2 Turbo renders a COCO-body OpenPose guide from the joints, encodes it through the matching Krea2 VL text encoder/VAE and applies the trained pose LoRA. Its reference K/V are computed once per generation and released when sampling ends, including errors. The guide is a trained adapter input, not just body-name prompting. Hands and face landmarks are not synthesized.

MOSS renders flat per-person colors and depth using the same camera and depth buffer as the masks, then applies the trained color/depth LoRA and its expanded input embedder. The recommended MOSS path is native JSON captions plus trained color/depth control. New samplers default to `layout_method=auto`: an active MOSS 3D pose adapter selects `moss_native`; other paths select `regional`. Explicit `regional`/`moss_native` choices in existing workflows and restored image settings are respected. The execution report and saved generation settings record the effective layout. Native mode converts character masks into enclosing boxes; regional mode retains silhouette masks. Disabling the pose node's strength returns the base MODEL path. Start/end ranges control the map conditioning; MOSS's trained input embedder/LoRA remain installed over the full sampling interval.

First actual use downloads a revision-pinned, SHA256-verified adapter into `models/loras/rs_reference/krea_pose/` or `models/loras/rs_reference/moss_pose/`, with node progress. Importing the extension and strength 0 do not download weights. Model weights and usage terms remain upstream's. Sources: [Krea2 pose weights](https://huggingface.co/thedeoxen/Krea-2-pose-controlnet), [Ostris Edit](https://github.com/ostris/ComfyUI-Krea2-Ostris-Edit), [MOSS color/depth weights](https://huggingface.co/darask0/MOSS-Image-color-depth-control).

Use the **standard RS sampler at full resolution**. Progressive sampling, simultaneous image references, other attention replacements and nonmatching model families are rejected. Tested checkpoints are Krea2 Turbo FP8 and MOSS SFT BF16; other variants and adapter combinations require their own tests. These adapters are global pose guides; numbered character prompts/masks still provide regional ownership. Exact identity, joints, hand contact and subject count can fail, particularly with style LoRAs.

[Workflow PNGs](../examples/pose3d/README.md) · [Krea2/MOSS generation evidence](pose3d-krea-moss-validation.md).

If required reference/download dependencies are absent, install the existing `requirements-reference.txt` in the ComfyUI Python environment. Adapter weights total about 229 MB for Krea2 and 313 MB for MOSS, downloaded separately.

## Import another image while editing

Drop an image onto the 3D viewport or its image panel. In a one-person scene the image also updates the camera and canvas ratio; in a group scene only the selected person is replaced and the existing composition stays fixed. The result is applied to the node automatically. Subsequent manual edits still use **Apply to node**. If the scene changes during inference, the result is rejected to preserve those edits.

The panel displays queue/download/estimation state. The first estimate downloads SAM 3D Body (2.83 GB) into the local detection-model directory; a compatible ComfyUI core with `SAM3DBody_Loader` and `SAM3DBody_Predict` is required. Its weights use the separate [SAM License](https://github.com/facebookresearch/sam-3d-body/blob/main/LICENSE). Images are processed on the local ComfyUI server. Use one person or a crop: hidden depth and joints are estimated, and body parts outside the original image frame are clipped from output.

## Local pose library and random selection

The editor reads `library.json` from `ComfyUI/models/rs_pose3d` and any configured
`rs_pose3d` model directories. Use **Refresh library** after adding a catalogue.
Choose a pose and **Set pose**, **Random selected** to change only the selected
person, or **Random each person** to choose independently for everyone. Horizontal
placement and prompt numbers stay fixed; the new pose is grounded automatically.
Random selection is an editor action, not a change on every sampling run. Save
the scene or workflow to keep the chosen result. Click **Apply to node** after editing.

Downloaded pose samples are local data and are not shipped in this package.
An empty library leaves manual posing and image import available. The local
conversion helper `tools/pose3d/import-library.py` accepts a downloaded positional
sample JSON and a destination directory. Keep the source revision and its license
beside your local catalogue. No sample download runs automatically.

**한국어 — 빠른 사용법:** 3D 포즈 노드의 **이미지 → 3D**에 한 명이 나온 이미지를
넣으면 추정 후 편집기가 자동으로 열립니다. 관절을 클릭한 뒤 회전 고리를 드래그해
수정하고 **노드에 적용**을 누르세요. 반신은 화면 안에 나온 부분만 출력합니다.
포즈 라이브러리가 설치돼 있으면 **선택 인물 랜덤** 또는 **각 인물 랜덤**으로
새 자세를 고를 수 있습니다. 랜덤 결과는 현재 장면에 저장되며 생성 때마다 바뀌지 않습니다.
