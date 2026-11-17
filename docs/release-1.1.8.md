# 1.1.8 Hangeul — Camera prompt filtering and visible details

**RS Camera Control · RS-CAMERA-CONTROL** now filters conflicting standalone
viewpoint tags in positive scene and character prompts using the nearest of
the 42 trained views. For example, a left-side view removes `front view` and
`from right`, and a directly overhead view removes `eye level` and
`from below`. Scope controls which prompts receive the changes.

The camera adds a small set of visible subject details based on the selected
view and framing. A rear medium shot can describe the upper back and the backs
of the shoulders. A rear close-up uses the back of the head. An overhead
view can describe the top of the head. A crop like `feet focus` skips the
general body cues. Anima uses tags and MOSS uses short sentences.

`visible_details` is on by default. Turn it off to compare the same seed with
viewpoint filtering alone. These changes were checked at the prompt and
workflow level. Rendered composition varies with the model, prompt, and seed.

## 한국어

선택된 42개 학습 시점에 맞춰 장면과 캐릭터의 긍정 프롬프트에서 충돌하는
단독 시점 태그를 정리합니다. 선택한 시점과 구도에 따라 화면에 보이는
부위도 보강합니다. 후면 중간 거리에서는 윗등과 어깨 뒤쪽을, 후면
클로즈업에서는 뒤통수를, 수직 하향에서는 정수리를 묘사합니다.

`visible_details`는 기본값이 켜짐입니다. 같은 시드에서 끄면 시점 필터만
적용한 결과와 비교할 수 있습니다. ComfyUI를 업데이트한 뒤 재시작하고
브라우저를 새로고침하세요.

- [Camera controls and wiring](camera-control.md)
- [3D Orbit guide](release-1.1.7.md)
