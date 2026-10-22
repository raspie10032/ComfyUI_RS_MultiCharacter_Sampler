# 1.0.1 Hangeul: OpenPose PNG input correction

The 1.0.0 pose node accepted coordinates only. Version 1.0.1 adds image selection/upload and image connections so ordinary use does not require JSON.

## User flow

Use **Load Pose PNG** or drop a colored skeleton image onto **RS OpenPose Masks**. Numbered masks and the original colored map appear before sampling. Adjust thickness; then select a person in Character Position to move and resize its mask. JSON stays collapsed as an advanced alternative. A connected single `IMAGE` works too, with its preview appearing after execution.

Try the original [two-person pose PNG](../examples/openpose/two-people-pose.png). Standard COCO-18/DWPose body colors on black or transparent backgrounds are supported, at 64–2048 pixels per side. Uploaded images override the JSON field; connected keypoints override connected images, which override the uploaded selection. PNG person numbers follow neck position from left to right. Check the masks before matching prompt rows.

No model download is needed. The decoder follows colored links to associate joints with a person. It supports opaque editor maps and maps whose sticks are painted over joint dots. Assigned-body checks reject rainbow finger clutter rather than adding a phantom person. NumPy/Pillow provide the fallback when OpenCV is unavailable.

## Verification, 2026-10-22

- Python: **213 tests, 212 passed and one existing native-bypass skip**, with the installed ComfyUI core available. Nine tests directly cover image decoding, two-person separation, a crossing arm, opaque/blended render styles, finger clutter, invalid images, connected IMAGE inputs, path bounds and the no-OpenCV fallback.
- JavaScript: **10 UI suites passed**, including upload/drop handlers, hidden JSON, source changes, stale responses and connected execution previews.
- Browser on actual ComfyUI: file-selection dialog, immediate numbered preview, actual pointer drag, enlarge, thickness update, serialization and workflow reload passed with no page errors. Saved position offsets and scale survived reload.
- External two-person map: [bonepose editor example](https://github.com/hisashi-ito/bonepose/blob/main/docs/export_example.png), decoded as two people. An additional test map rendered with the original [ControlNet drawer](https://github.com/lllyasviel/ControlNet/blob/main/annotator/openpose/util.py) also decoded as two. Photographic ControlNet example inputs were rejected with a skeleton-image message.
- Actual generation: Anima Base v1.0, 1024×1536, 30 steps, CFG 4, Euler ancestral / **SGM uniform**, same seed, part-name strength 0.15. Uploaded-file and connected-IMAGE runs both succeeded; their output RGB pixels were exactly equal. Generation PNG metadata restored two placed person masks and the part-name strengths through the normal metadata loader.

These checks establish working PNG input and integration, not exact pose adherence or improved image quality. This patch does not change the regional attention or body-part guidance algorithm. Body-part name guidance remains experimental and defaults to zero.

Local evidence folder: `RS_MC_openpose_png_validation_20261022` under the developer's Codex documents, containing API prompts, histories, original metadata-bearing output copies, decoder results, screenshots and test logs. Third-party input images and the full generated images are not bundled in the package.

## Limits and errors

PNG pixels do not preserve person IDs or hidden joints. Crossed/occluded limbs can be assigned incorrectly; the preview asks users to check the numbered masks. Missing joints are omitted rather than invented. Arbitrary recoloring, monochrome maps, raster BODY-25, photos, dense labels and tiny/cropped necks are unsupported. Exact coordinates and BODY-25 remain available through JSON/POSE_KEYPOINT. Animated or batched image input is rejected. Errors explain the expected format in English and Korean; node controls and ordinary UI messages also include Japanese localization.
