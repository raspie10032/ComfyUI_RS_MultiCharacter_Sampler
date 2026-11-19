# 1.1.10 Hangeul

**RS Camera Control · RS-CAMERA-CONTROL** now automatically downloads and loads
**RS-CAMERA-CONTROL-v3** on Anima 2B. The v3 LoRA continues training from v2 for
10 epochs on the 42 camera directions.

In same-seed comparisons of two full-body scenes across ten views each, directly
overhead and directly below views followed the requested angle more closely.
At `lora_strength=1.0`, backgrounds can take on a 3D-rendered look. In one
six-view scene with RS-CVN5, `0.65` retained more of the illustration style and
softened the steepest views.

[LoRA and model card](https://huggingface.co/raspie/RS-CAMERA-CONTROL) ·
[Camera controls and wiring](camera-control.md) ·
[Anima example workflow](../examples/camera/anima-camera-control.json)

## 한국어

Anima 2B를 연결하면 **RS Camera Control · RS-CAMERA-CONTROL**이
**RS-CAMERA-CONTROL-v3**를 자동으로 받아 적용합니다. v2에서 이어 42방위
데이터로 10에폭 추가 학습한 LoRA입니다.

전신 장면 두 개에서 시드와 프롬프트를 고정해 각각 10개 시점을 비교했습니다.
수직 위와 아래 시점이 요청 각도에 더 가깝게 나왔습니다. `lora_strength=1.0`에서는
배경에 3D 렌더 느낌이 강해질 수 있습니다. RS-CVN5를 적용한 한 장면에서는
카메라 강도를 `0.65`로 낮추자 일러스트 질감이 더 살아났고, 극단적인 고도각은
완만해졌습니다.
