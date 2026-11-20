# 1.1.12 Hangeul

Add **RS Unified Camera Control** from **RS → Camera**. Select the mode that fits the model and workflow.

| Mode | When to use it |
| --- | --- |
| `merged_lora_only` (default) | For Anima 2B reference poses, connect the model after style LoRAs and send its output to the pose adapter. Strength 1.00 applies camera v3 at 0.20 and multi-character composition at 0.50. The node passes through the character pipe and base prompt. |
| `camera_and_lora` | Set a trained view with the dials or 3D orbit. Anima 2B supports camera v3 and the merged weights. MOSS-Image uses its dedicated adapter. |
| `prompt_only` | Add camera tags to a prompt or an RS/NAI character pipe. The model connection is optional. |

Existing workflows retain their saved node IDs, connections and settings. The original three camera nodes, combined character prompts, standalone 3D pose adapter and Anima character reference are registered under **RS MultiCharacter → Legacy**. Enable deprecated nodes in the node library to browse these entries, and enable experimental nodes to see experimental entries. The separate NovelAI camera is still available.

The old and new loaders produced pixel-identical 1152×1152 images in a same-seed Reference Pose Duo comparison on an RTX 4070 Ti SUPER. The local check covered the merged-only mode with the personal style LoRAs and 3D pose guidance.

## 한국어

레퍼런스 포즈 워크플로에는 **RS → Camera → RS 통합 카메라 컨트롤**을 추가합니다. 기본 모드인 `merged_lora_only`에서 스타일 LoRA 뒤에 MODEL을 연결하고, 출력 MODEL을 포즈 어댑터로 보냅니다. 병합 강도 1.00은 카메라 0.20과 멀티 구도 0.50에 해당합니다. 42방위 카메라를 조작할 때는 `camera_and_lora`, 시점 태그만 만들 때는 `prompt_only`를 선택하세요.

기존 워크플로의 구형 노드 6개는 저장된 연결로 계속 실행됩니다. 노드 라이브러리에서 사용 중단 노드 표시를 켜면 **RS MultiCharacter → Legacy**에서 찾을 수 있습니다. 실험 노드는 실험적 노드 표시도 필요합니다. [카메라 연결 방법](camera-control.md)
