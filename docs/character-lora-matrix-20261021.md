# 캐릭터 LoRA와 양자화 모델 비교 — 2026-10-21

Krea 2 Turbo FP8의 캐릭터별 LoRA 실패는 RS의 가중치 Hook이 packed weight의
`weight_scale` 속성을 찾지 못하는 오류였다. MOSS INT8에서도 같은 오류를 재현했다.
Krea2와 packed MOSS의 일반 선형 LoRA를 Bypass 경로로 보내 수정했다.
기존 양자화 forward에 LoRA down/up 계산을 더하며 원본 가중치와 scale 키를
바꾸지 않는다. BF16 MOSS는 기존 Hook 경로를 유지한다. 지원하지 않는 packed
LoRA 형식은 생성 전에 모델 계열과 이유를 표시한다. GGUF 및 모든 변형 LoRA의
지원을 뜻하지 않는다.

## 실제 생성

별도 로컬 서버에서 같은 장면과 시드 346751로 무적용, 일반 전역 로더,
캐릭터 1, 캐릭터 2, 강도 0, 제거 후의 6개 조건을 실행했다. 대상 LoRA 강도는
모델 1 / CLIP 0이다.

| 모델 | 대상 LoRA | 결과와 범위 |
|---|---|---|
| Krea 2 Turbo FP8 | First Lara Krea2 | 수정 전 오류 재현, 수정 후 6/6 생성. 게임풍 표현이 선택한 사람 쪽으로 이동 |
| FLUX.1 Dev FP8 | LaraCroft flux v1 | 6/6 생성. 선택한 캐릭터의 얼굴·복장 변화 확인 |
| FLUX.2 Klein 4B FP8 | Neytiri Klein 4B | 6/6 생성. 선택한 쪽의 얼굴·피부 표현 변화 확인 |
| FLUX.2 Klein Base 4B FP8 | 같은 Neytiri LoRA | 6/6 생성. Base 조합의 호환성 확인 |
| FLUX.2 Klein 9B 4-step | ElsaTC V2 Base LoRA | 6/6 생성. LoRA는 Base 학습용이므로 체크포인트 조합 차이에 유의 |
| Anima BF16 | 보유 RSC 스타일 LoRA | 6/6 생성. 스타일 적용 경로 시험 |
| Illustrious | 보유 Phoebe 캐릭터 LoRA | 조정한 1024×768에서 6/6 생성, 두 사람 유지. 반복 픽셀 일치에는 아래 한계가 있음 |
| MOSS BF16 + 별도 8-step LoRA | 보유 Mythic Mosaic 스타일 LoRA | 6/6 생성. 대상은 스타일 LoRA |
| MOSS INT8, 20 steps | 같은 Mythic Mosaic LoRA | 수정 전 좌우 조건 오류, 수정 후 6/6 생성. 스타일 변화가 선택한 쪽으로 이동 |

Illustrious를 제외한 위 조합은 강도 0 및 제거 후 이미지가 무적용 PNG와
RGB 픽셀 단위로 정확히 일치했다. Illustrious는 일부 반복 이미지가 달라져
전체 조합의 픽셀 복원 보장을 주장하지 않는다. 새 서버에서 LoRA를 한 번도
적용하지 않은 첫 두 생성에서도 같은 차이(평균 RGB 절댓값 차이 약 4.22)를
재현했다. 따라서 이 차이만으로 LoRA 잔류를 의미하지는 않는다. 영역별 변화는 육안 기능 확인이며,
캐릭터 재현율·영역 밖 무영향·여러 시드의 성공률을 측정한 결과는 아니다.
FLUX.3와 캐릭터별 CLIP LoRA는 이번에 시험하지 않았다.

## 예제와 조정값

- [Krea2 UI](../examples/character-lora/krea2.json) / [API](../examples/character-lora/krea2-api.json): 768×512, 8 steps, CFG 1, Euler/simple, common 0.60, character 1.70, separation 0.90.
- [Illustrious UI](../examples/character-lora/illustrious.json) / [API](../examples/character-lora/illustrious-api.json): 1024×768, 24 steps, CFG 5.5, Euler ancestral/normal, common 0.05, character 1.70, separation 0.90.

두 설정은 모델 프리셋에도 추가했다. 프리셋은 샘플링·영역 조정값만 적용한다.
캔버스 크기와 캐릭터 LoRA는 직접 선택하거나 전체 예제를 사용한다. 예제의
파일명은 로컬 시험 파일명이며 가중치는 포함하지 않는다. Illustrious의 강한
분리는 장면에 따라 경계나 인물 중복을 만들 수 있어 문장과 함께 조절한다.

원본 로컬 증거는 `RS_MC_character_lora_matrix_20261021` 폴더의 API 요청,
history, audit, PNG, `results.json` 및 비교판에 보관한다.
