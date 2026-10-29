# Experimental 3D Pose Masks

Arrange native skinned MHR bodies in a local 3D editor, then use their camera-projected silhouettes as numbered character regions. Editing and masks need no inference weights, external service or runtime CDN. Pose conditioning uses a separately trained compatible adapter. Three.js is bundled with the extension.

1. Add **RS 3D Pose Masks (Experimental)** and click **Open 3D editor**.
2. Choose a character number matching the Prompt/LoRA slot. Add or copy up to ten people. Numbers stay fixed when people cross; renumber explicitly to change the assignment.
3. Click a joint and drag its colored rings, or select a joint and use the XYZ sliders. Choose **Move person** to drag the whole person. Height and body-width controls change that person's silhouette.
4. Drag empty space to orbit the output camera; right-drag pans, the wheel zooms. Use Front/Side/Back to reset the view and set canvas dimensions (64–2048 pixels per side).
5. Choose **Full silhouettes** to keep overlapping character regions, or **Visible silhouettes** to subtract regions hidden behind other people. The small preview shows the actual CPU mask projection.
6. Click **Apply to node**. Connect its `building_pipe` anywhere before **Finalize**, along with the Prompt, LoRA and Position nodes. Finalize still determines the active prompt slots. Set the sampler to the same aspect ratio as the editor; other aspect ratios stretch the normalized masks.

The node outputs its mask preview and two MASK batches (full/visible), sorted by character number. The chosen mode only selects which masks enter the building pipe. `scene_info` lists the batch's character IDs. Scene JSON is stored in the node's workflow widget. Save/load scene buttons also allow an independent JSON backup.

[Drop-in workflow PNG](../examples/pose3d/anima-native-pose.png) · [Example requirements](../examples/pose3d/README.md)

## Experimental pose-adapter path

The last output, `pose_image`, renders shaded colored bodies on black using the same scene, camera, depth ordering and aspect ratio as the masks. It excludes editor handles and grids. Existing output indices are unchanged. This image is separate from the character building pipe: connecting the pipe alone still supplies masks only.

For an experimental Anima 2B test, load compatible weights with ComfyUI's **Load Model Patch**, connect `pose_image` to **Apply Anima LLLite**, and feed its MODEL output to the RS sampler. The scene's building pipe still supplies numbered character masks. The sampler accepts complete native Anima LLLite patch groups while preserving RS routing, and rejects other attention replacements, mismatched adapter dimensions and simultaneous image references. Other model families' ControlNets, Anima 2.9B pose weights, progressive sampling and character-LoRA combinations have not been validated by this test.

New scenes use the bundled native MHR mesh, bind transforms, skin weights and procedural twist supports. Body, hand and finger controls deform the mesh. Scene format v2 is shared by the browser and CPU renderer; existing v1 ellipsoid scenes retain their original geometry and output. The renderer deliberately omits learned pose correctives and facial/body-shape inference.

A successful output connection is not evidence of reliable pose following. The initial ellipsoid tests failed. Native anatomical renders subsequently induced seated and raised-arm poses in controlled Anima 2B tests; the integrated editor tests also show raised-arm transfer, but frontal two-person seating remains unreliable. Hand contact, exact joints, appearance and subject counts remain model-dependent. See the [component comparison](pose3d-validation.md) for paired seeds and failures.

Tested with [toyxyz/Anima_ControlNet-LLLite](https://huggingface.co/toyxyz/Anima_ControlNet-LLLite), `anima_3dpose_outline_7000.safetensors`, strength 1, full denoising interval. This adapter expects anatomical shaded renders with outlines rather than OpenPose sticks. A matching Anima 2B base and a recent native ComfyUI Anima LLLite implementation are required. Load its weights separately with Model Patch Loader. Outline affects only the pose image, never silhouette ownership. The experimental node does not auto-download adapter weights.

## Boundaries

- The pipe alone guides composition and prompt ownership through 2D masks. Pose guidance is separate: connect pose_image through a compatible adapter to the sampler MODEL. The generation model never receives the 3D rig itself.
- New bodies use a native skinned adult MHR mesh and hand/finger controls. Legacy scenes keep ellipsoid bodies. Clothing simulation, facial controls, body tracking and photo-to-pose estimation are not included.
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
