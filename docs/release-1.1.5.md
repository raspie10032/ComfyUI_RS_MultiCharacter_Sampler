# 1.1.5 Hangeul — Automatic rear-view prompt filtering

**RS Camera Control · RS-CAMERA-CROL** automatically removes standalone eye,
expression, and gaze tags such as `purple eyes`, `smile`, and `looking at viewer`
when it selects a rear or rear-diagonal view. With the default scope, it filters
the positive prompts for both the scene and the characters. Expand wildcards
upstream of the camera node so it can read their tags.

The existing [Anima 2B workflow](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/blob/v1.1.5/examples/camera/anima-camera-control.json)
uses the published [RS-CAMERA-CONTROL LoRA](https://huggingface.co/raspie/RS-CAMERA-CONTROL).

## 한국어

**RS Camera Control · RS-CAMERA-CONTROL**에서 정후방이나 뒤쪽 대각선을 고르면
`purple eyes`, `smile`, `looking at viewer`처럼 얼굴을 보여주도록 유도하는
단독 태그를 자동으로 거릅니다. 기본 적용 범위에서는 장면과 캐릭터의 긍정
프롬프트에 모두 적용됩니다. 와일드카드는 카메라 노드 앞에서 펼쳐 주세요.
