# 1.1.4 Hangeul — RS Camera Control for Anima

**RS Camera Control · RS-CAMERA-CONTROL** adds a camera-view LoRA to Anima 2B.
The editor selects the nearest of 42 training viewpoints, adds the learned tags
to the scene prompt, and adds composition guidance to the scene and character
prompts with the default scope. The **Face left** and **Face right** presets
refer to the direction the character faces on screen.

Open the [example workflow](../examples/camera/anima-camera-control.json) in
ComfyUI and select your local Anima 2B diffusion model, Qwen text encoder, and
Qwen Image VAE. For a custom graph, connect Anima's MODEL to the camera node,
and connect the character building pipe and the scene prompt to
`building_pipe` and `base_prompt`. Send the camera MODEL to the sampler and the
camera building pipe through **RS Finalize Character Pipe** to the sampler.

The first queued run at nonzero `lora_strength` downloads the
[LoRA from Hugging Face](https://huggingface.co/raspie/RS-CAMERA-CONTROL)
if absent. A verified download is saved under
`ComfyUI/models/loras/anima/RS-CAMERA-CONTROL.safetensors`. For offline
installation, place the file there manually. Use `lora_strength=0` to compare
the same prompts with the LoRA bypassed. The LoRA is distributed under the
[CircleStone Labs Non-Commercial License](https://huggingface.co/raspie/RS-CAMERA-CONTROL/blob/main/LICENSE.md).

The earlier 5060 Ti integration test matched manual conditioning pixel for
pixel on two greenhouse profile shots, using one seed, RS-CVN5, Progressive,
832 × 1216, Euler A CFG++, 15 steps, and CFG 3. Both directions also matched
with the camera LoRA off in that test. The 42-view preset mapping is covered
by tests. Generation across subjects, seeds, and the full sphere remains
unverified.

## 한국어

[예제 워크플로](../examples/camera/anima-camera-control.json)를 열고 Anima 2B,
Qwen 텍스트 인코더, Qwen Image VAE를 선택하세요. 카메라 노드에서 **화면 왼쪽**
또는 **화면 오른쪽**을 누르고 실행하면 됩니다. 첫 실행 시 LoRA 파일이 없으면
Hugging Face에서 받아 로컬에 저장합니다. `lora_strength=0`으로 두면 같은 구도
프롬프트에서 LoRA만 끄고 비교할 수 있습니다.
