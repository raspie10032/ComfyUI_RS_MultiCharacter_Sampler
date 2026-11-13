# 1.1.6 Hangeul — RS-CAMERA-CONTROL-v2

**RS Camera Control · RS-CAMERA-CONTROL** now loads v2 on Anima 2B. Existing
workflows can use the same node. On first use with nonzero `lora_strength`,
the node downloads and verifies the v2 file if it is absent, even when v1
is installed. For offline use, download
[RS-CAMERA-CONTROL-v2.safetensors](https://huggingface.co/raspie/RS-CAMERA-CONTROL/resolve/main/RS-CAMERA-CONTROL-v2.safetensors)
to `ComfyUI/models/loras/anima/`.

The node selects the nearest of 42 trained views and adds `from left` or
`from right` to the scene prompt for a lateral view, alongside the camera
caption and composition tags. It still removes face, expression and gaze
tags for rear views.

Open the [Anima example workflow](../examples/camera/anima-camera-control.json)
or follow the [original wiring guide](release-1.1.4.md). The LoRA is available
under the [CircleStone Labs Non-Commercial License](https://huggingface.co/raspie/RS-CAMERA-CONTROL/blob/main/LICENSE.md).

## 한국어

기존 카메라 노드가 v2를 자동으로 사용합니다. v1이 설치돼 있어도 v2 파일을
처음 사용할 때 별도로 받습니다. 좌우 시점에는 `from left` 또는 `from right`가
자동으로 붙고, 후방 시점에서는 눈·표정·시선 태그를 거릅니다.
