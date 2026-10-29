# Experimental 3D Pose Masks

Arrange procedural mannequins in a local 3D editor, then use their camera-projected silhouettes as numbered character regions. No inference model, ControlNet, external service or runtime CDN is required. Three.js is bundled with the extension.

1. Add **RS 3D Pose Masks (Experimental)** and click **Open 3D editor**.
2. Choose a character number matching the Prompt/LoRA slot. Add or copy up to ten people. Numbers stay fixed when people cross; renumber explicitly to change the assignment.
3. Click a joint and drag its colored rings, or select a joint and use the XYZ sliders. Choose **Move person** to drag the whole person. Height and body-width controls change that person's silhouette.
4. Drag empty space to orbit the output camera; right-drag pans, the wheel zooms. Use Front/Side/Back to reset the view and set canvas dimensions (64–2048 pixels per side).
5. Choose **Full silhouettes** to keep overlapping character regions, or **Visible silhouettes** to subtract regions hidden behind other people. The small preview shows the actual CPU mask projection.
6. Click **Apply to node**. Connect its `building_pipe` anywhere before **Finalize**, along with the Prompt, LoRA and Position nodes. Finalize still determines the active prompt slots. Set the sampler to the same aspect ratio as the editor; other aspect ratios stretch the normalized masks.

The node outputs its mask preview and two MASK batches (full/visible), sorted by character number. The chosen mode only selects which masks enter the building pipe. `scene_info` lists the batch's character IDs. Scene JSON is stored in the node's workflow widget. Save/load scene buttons also allow an independent JSON backup.

## Boundaries

- This guides composition and prompt ownership. The generation model receives 2D masks; it does not receive a 3D rig or a pose ControlNet. Exact joint angles, occlusion, people counts and physical contact remain model-dependent. In the initial Anima/SDXL smoke tests the same pose was also written in the common prompt; these are execution checks, not evidence that the mask alone improves pose accuracy.
- Procedural bodies are simple ellipsoids, not anatomical meshes. Fingers, facial landmarks, clothing, body tracking and photo-to-pose estimation are not included.
- Masks outside the canvas are clipped. If a selected silhouette is entirely outside/behind the camera or fully hidden in visible mode, Apply/execution explains which character needs correction. Full mode can retain hidden characters.
- Moving a person does not change its prompt number. Prompt enable/count settings determine which numbered regions are used by generation.
- New 3D masks preserve incoming prompts, LoRAs, placement transforms and camera settings. Position before/after this node gives the same result. Later mask producers overwrite earlier masks for their slot.
- Deleting a person clears a mask previously owned by this 3D node only when that same mask is still present upstream. It does not erase a later replacement mask. Deleting from a scene also leaves the corresponding prompt setting intact; disable that prompt if you want fewer characters.
- The first version is local to the MultiCharacter extension. It does not install a separate editor in the NovelAI Request extension.

## References and build

Interaction design was studied from [Online 3D OpenPose Editor](https://github.com/ZhUyU1997/open-pose-editor) (MIT, inspected revision `8e659f1f1995715621ac3f50d9c34d55faf5296d`) and its [ComfyUI wrapper](https://github.com/hinablue/ComfyUI_3dPoseEditor) (MIT, inspected revision `582c5b1410d5bd5a91465f05796f4e99a690cc52`). Their external mannequin and capture dependencies were not imported. The procedural geometry, scene format, rasterizer and RS building-pipe integration are implemented here.

[Three.js](https://github.com/mrdoob/three.js) 0.170.0 supplies the WebGL renderer, OrbitControls and TransformControls under MIT. Its license is distributed in `web/pose3d/THREE-LICENSE.txt`. Rebuild the checked-in offline bundle with `cd tools/pose3d && npm ci && npm run build`. Python has no new dependencies.

Tests: `RS_MC_TEST_COMFYUI=/path/to/ComfyUI PYTHONPATH=/path/to/ComfyUI python -m unittest discover -s tests -q`, then `node --test tests/*_ui.cjs` with the same Python environment on PATH. An optional real-browser regression is in `tools/pose3d/test-editor.mjs`; it needs Playwright and a separate running ComfyUI at port 8189 (or `RS_COMFY_URL`), with only this candidate enabled. Set `RS_CHROMIUM` when using an existing Chromium executable. It exercises joint controls, actual translation/rotation-gizmo dragging, camera orbit, IDs, undo/redo, scene files, workflow restore and editor network isolation.
