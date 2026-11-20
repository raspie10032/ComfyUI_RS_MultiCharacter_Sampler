# 1.1.11 Hangeul

For Anima 2B reference-pose workflows, connect the MODEL after any style LoRAs to **RS Anima Camera + Multi LoRA**, then connect its output to the pose adapter. At strength 1.00 the merge applies camera v3 at 0.20 and multi-character composition at 0.50. Use one instance per model chain.

For workflows using **RS Camera Control · RS-CAMERA-CONTROL** to set a view, select `anima_lora = camera_multi_merge` on that node to use the same file. Existing workflows default to `camera_v3`. MOSS uses its dedicated adapter.

First use downloads the [merged weights](https://huggingface.co/raspie/RS-CAMERA-CONTROL/blob/1dabdaf118e26acd55b066616eb1859aa3f60e50/RS-Anima-Camera020-Multi050.safetensors) into `models/loras/anima/` and verifies their size and SHA-256 before installation. The loader reuses an installed copy, including models in configured LoRA directories. Strength 0 bypasses the download and model patch.

## 한국어

레퍼런스 포즈 워크플로에서는 스타일 LoRA 뒤에 **RS Anima Camera + Multi LoRA**를 연결하고, 출력 MODEL을 포즈 어댑터에 연결합니다. 강도 1.00에서 카메라 v3는 0.20, 멀티 구도는 0.50으로 적용됩니다. 카메라 다이얼을 쓰는 워크플로는 기존 카메라 노드의 `anima_lora`에서 `camera_multi_merge`를 선택하세요. 두 경로 중 한 곳에서 적용하면 됩니다.
