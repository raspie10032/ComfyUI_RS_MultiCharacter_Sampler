# OpenPose mask guides

The automatic masks are rough composition guides. Optional body-part guidance is **very weak attention guidance using the names of skeleton parts**. The generation model receives body-part text at mapped locations, not an OpenPose skeleton image. No ControlNet, pose detector or additional pose weights are loaded.

한국어: **뼈대 자체를 쓰는 것이 아니라, 그 위치에 부위 이름을 넣어 아주 약하게 어텐션을 유도합니다.**

## Connect the nodes

Connect `RS OpenPose Masks` to the building pipe, followed by Character Prompt, Character LoRA (optional), Character Position and Finalize Character Pipe. Prompt, LoRA and Position can be in any order. The pose node preserves these settings and existing mask transforms when updating masks. A later mask source can replace its person mask; body-part guidance is then cleared so old part regions do not remain attached to the replacement mask.

1. Click **Load OpenPose JSON**, paste one JSON frame, or connect one `POSE_KEYPOINT` frame from DWPose/OpenPose. A connected frame takes priority over pasted JSON.
2. Choose **thickness** to adjust limb width and body padding. Start at `1.0`; available range is `0.25–3.0`.
3. Match character prompt rows to the JSON `people` array: first person = row 1, second = row 2. Disabled prompt rows retain their original numbers.
4. In **Character Position**, select the person number above the layout, drag its mask, and use corners or −/+ to resize it. Part-name regions move and scale around the same person center. Canvas overflow is clipped; generated bodies are not cut out.
5. Keep **body_part_strength = 0** for mask-only composition. Anima/SDXL users can optionally try a low value such as `0.1–0.2`. Six shared labels are used: `head`, `hands`, `chest`, `thighs`, `legs`, `feet`. Higher strength is not a promise of better pose adherence.

Input coordinates must be pixels, with a `people` array containing COCO-18 (54 values) or BODY-25 (75 values) `pose_keypoints_2d`. JSON canvas dimensions take priority; width/height widgets are fallback values for the **original pose canvas**, not the generation resolution. Missing or low-confidence joints are omitted. COCO-18 ankle regions approximate feet; no fingers or toes are reconstructed. Use a single frame, not a video batch or a collection of named poses. Export a frame from a collection first. A skeleton PNG alone is not decoded.

## Overlap separation

`RS Character Interaction` optionally delays the decay of separation **only between non-overlapping character areas**. Overlap and background keep the sampler's existing schedule.

| Preset | Behavior |
|---|---|
| baseline | Existing boundary behavior |
| delay3 | Keep exclusive boundaries for 3 additional steps |
| delay6 | Keep exclusive boundaries for 6 additional steps |
| custom | Choose the additional hold steps and decay amount |

The sampler's boundary hold and decay settings still govern the ordinary schedule. This extra path is implemented for Anima/SDXL and experimental SD1.5. Other families report a clear error when additional separation is requested. The baseline preset and automatic masks remain usable with existing model families. Body-part name guidance is limited to Anima/SDXL.

## Preview, saving and limits

The pose node shows numbered person masks. Position and Finalize show their transformed placement. Direct JSON edits update the diagram before generation. For connected JSON, `POSE_KEYPOINT`, or connected thickness/confidence/canvas controls, **run the graph once**: its executed masks populate the diagram and position editor without evaluating arbitrary upstream nodes in the browser. You can then edit unconnected thickness/confidence controls and move/resize the masks. Changing the upstream source or its connection hides the old masks and requests another execution. Execution snapshots are temporary; reloaded workflows with connected inputs need another execution. ComfyUI's intermediate-output replay also supplies the masks when that execution is fully cached.

Connect `pose_preview` to Preview Image to inspect joints and person masks; `person_masks` outputs a mask batch. Automatic masks and part regions are preserved in the extension's PNG/WebP metadata, together with interaction settings. The image loader restores the effective placed masks; metadata is not a saved skeleton editor.

These controls do not guarantee exact joint angles, correct hand contact, character identity or anatomy. The SDXL 20 OFF / 20 ON comparison did **not** demonstrate improved high-five pose accuracy; names can change clothing and appearance. Part-name guidance therefore defaults OFF. Keep using character prompts and suitable model-specific settings.

See [release validation](release-1.0.0.md) for the actual tested paths. A basic pose example is in [examples/openpose](../examples/openpose).
