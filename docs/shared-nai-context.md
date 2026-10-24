# Shared RS NAI and MultiCharacter connections

Both extensions must contain the shared-context update. Existing output socket names and positions remain compatible with old workflows.

Connect an **NAI CONTEXT** output to a local **character_pipe** or **building_pipe** input, or a local character pipe to the NAI **nai_context** / **character_prompts** input. The local character, LoRA, position, mask, reference, interaction and final-pipe nodes can continue editing a received scene. No new conversion node is required.

The two detection combine loaders have the same controls and can feed either detailer. The two WD tagger loaders also have identical controls and interchangeable outputs. This shares loader functionality; local detailing still requires the connected local model, CLIP and VAE, while NAI detailing uses the API.

| Data | Behavior |
| --- | --- |
| Common and character prompts, negative captions, X/Y | Shared; prompt weights convert at the boundary, once. Character negatives stay regional in local sampling and detailing. Empty character negatives keep the original common-negative path. |
| Masks, boxes, text regions, regional LoRAs, body parts, image references, interaction settings | Used locally and carried through the NAI context for a return to local nodes. NAI receives character centers and captions; these local features are not translated into NAI masks, LoRAs, references or text layout. An execution notice explains the limitation. |
| Sampling configuration | NAI and local settings are stored separately. A local checkpoint name cannot become an NAI model ID. Local settings restoration remains opt-in through `use_image_settings`. |
| Seed, image dimensions, payment protection, reference assets | Each NAI stage retains its own controls. Sharing a context does not enable paid requests or copy local assets into API reference fields. |
| Character count | The receiving model applies its limit. Local supports ten active regions in total; NAI capacity depends on its model. The source pipe remains immutable. Changing a slot count does not rewrite count tags in the common prompt. |

PNG, lossless WebP and lossy WebP saved by these nodes retain the shared scene and the two settings groups. NAI detailer saves retain the whole scene separately from individual face requests. Inset metadata describing a different canvas cannot substitute for the full original scene. This does not add workflow serialization.

For an imported NAI image with more than ten characters, the local image loader shows a selection-time notice before queuing. Execution also reports its limit. Reloading a resized social-media image whose metadata was removed cannot restore a pipe.

## Validation

The companion NAI repository's `tests/test_bidirectional_pipe.py` covers prompt syntax, both directions, builder edits, effective request settings, active counts, masks, LoRA mode, references, text/body-part/interaction data, PNG/WebP restoration, detailer saves and cross-loader schemas. `tests/test_pipe_compat.py` here covers local adapters and regional negatives. The precision LoRA regression checks that hooks preserve an existing negative region mask.

The companion `tests/verify_shared_graph.py --comfy <ComfyUI> --mc <this checkout>` uses the real ComfyUI validator and executor on a nine-node mixed graph. Its NAI transport returns two controlled responses and rejects real HTTP. This proves graph execution and effective request construction; it does not prove live API or GPU image quality.

On 2026-10-25, 250 Python tests ran successfully (one old-core-only case skipped), and all 14 UI test files passed. The companion NAI suite passed 288 Python tests, including cross-package checks enabled with both `RS_MC_TEST_PATH` and `RS_MC_TEST_COMFYUI`, plus 13 JavaScript test files. No Anlas was spent.

한국어: 양쪽 확장을 함께 업데이트하면 캐릭터·컨텍스트와 감지기·태거를 서로 연결할 수 있습니다. 로컬 전용 기능은 NAI에 적용되지 않지만 왕복할 때 보존됩니다. NAI 과금 보호는 각 노드의 설정을 그대로 따릅니다.
