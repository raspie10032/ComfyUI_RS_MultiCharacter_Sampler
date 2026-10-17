# 0.1.6 Zeta — 캐릭터별 LoRA 검증 (2026-10-17)

검증 시점: 개발 브랜치 `codex/0.1.6-zeta-regional-lora`. 당시 공개 main 및 Linux 설치본은 0.1.5.
캐릭터 파이프에 LoRA 파일명, 모델 강도, CLIP 강도를 저장한다. 기존 전역 LoRA 위에
ComfyUI weight hook을 추가하고, 각 예측을 기존 좌표/상자 마스크로 합친다.

이 문서는 최초 weight-hook 구현의 결과다. 이후 Anima Bypass 최적화의 별도 실측은
[Bypass 검증 기록](regional-lora-bypass-validation.md)을 참조한다.

## 실제 실행

Anima: 1024×768, 30 steps, CFG 4, Euler ancestral / SGM uniform, seed 250917.
RSC 및 MyMy 스타일 LoRA, 모델 1.0 / CLIP 0.0. 프롬프트와 좌표는 고정한다.
SDXL: 1024×768, 24 steps, CFG 5.5, Euler ancestral / normal, seed 250917.
Phoebe / Camellya 캐릭터 LoRA 모델·CLIP 0.8. CLIP 전용 확인은 4스텝 실행이다.
정확한 값은 로컬 검증 묶음의 API 요청, history, audit 파일에 있다.

| 실행 | 상태 | 제출부터 완료까지 초 | 관측 최대 RSS GiB |
|---|---|---:|---:|
| anima-after-checked | success | 36.5 | 15.66 |
| anima-after | success | 27.3 | 6.48 |
| anima-baseline | success | 30.3 | 6.47 |
| anima-detailer-ready | success | 30.3 | 10.63 |
| anima-detailer | error | 3.0 | 6.49 |
| anima-global-ab | success | 30.3 | 8.56 |
| anima-regional-ab | success | 145.6 | 8.49 |
| anima-regional-ba | success | 148.6 | 8.49 |
| anima-restored | success | 151.7 | 8.33 |
| anima-smoke | success | 24.4 | 10.29 |
| anima-zero | success | 30.3 | 8.52 |
| sdxl-characters-ab | success | 127.4 | 15.47 |
| sdxl-characters-ba | success | 109.3 | 13.06 |
| sdxl-clip-only | success | 12.2 | 13.10 |

시간은 polling 간격 및 로딩/캐시를 포함한다. 첫 smoke의 로딩시간과 이후 warmed 실행은
직접 비교할 수 없다. RSS는 약 3초 간격 표본이며 순간 최대치를 놓칠 수 있다. GPU 기록은
장치 전체 사용량으로 프로세스 전용 사용량이 아니다. HWM은 서버 시작 이후 누적 값이다.

초기 디테일러 실패는 시험 환경에 Impact Pack import 경로가 빠진 오류였다. 기존 설치 경로를
시험 서버에 연결한 뒤 2개 얼굴 모두 자동 매칭·보정했다. 보고서에 각 얼굴의 캐릭터 번호와
서로 다른 LoRA명이 남아 있다. `anima-detailer-ready.history.json` 참조.

## 확인한 것

- Anima 무적용 / 두 LoRA 전역 적용 / 좌우 분리 / LoRA 좌우 교환 실제 생성.
- 강도 0, 뒤이은 무적용 생성은 baseline과 RGB 픽셀이 완전히 같다. 무적용 후속은
  sampler를 다시 실행하고 lossless WebP로 저장했으며 이전 sampler 캐시를 재사용하지 않았다.
- 이미지 로더에서 두 LoRA를 복원한 재생성은 원본 regional-ab와 픽셀이 완전히 같다.
- 실제 생성 이미지를 PNG / lossless WebP / lossy WebP로 저장·읽어 캐릭터 파이프,
  LoRA 파일명 및 두 강도가 모두 정확히 복원됨. lossy WebP의 픽셀 일치는 주장하지 않는다.
- SDXL 두 캐릭터 LoRA와 CLIP 패치, LoRA 배정 교환, CLIP만 적용하는 경로 실행.
- 브라우저 10개 검증: 구형 워크플로 기본값, 선택/강도 표시, 저장·재열기, 인원 감소,
  텍스트 슬롯 숨김. 내보낸 예제의 실제 API 입력은 원본 생성과 같음
  (사용하지 않는 point 슬롯 width의 float 표현 0.3999999999999999/0.4만 차이).
- 현재 ComfyUI Python 100개 통과. v0.3.76은 93개 통과 / 없는 아키텍처 7개 제외.
  JavaScript 4개 시험 파일 통과.
- 소형 실제 SD1.5 UNet CPU 통합: 첫 모델 평가에서 LoRA 영향은 배정한 절반에만 발생하고
  반대 절반은 기준 예측과 허용오차 내 일치. 좌우 교환도 확인. 다음 스텝/완성 이미지까지
  영향이 그 안에만 갇힌다는 의미는 아니다. 중단/오류 주입 후 원래 가중치와 결과도 복원됨.

## 판독 범위와 제한

Anima 스타일 LoRA 배정 변경으로 얼굴·채색·구도가 달라진다. SDXL은 두 사람의 금발/은발,
흰 상의/빨간 상의 구분을 유지하면서 표정·의상·자세가 달라졌다. 이 비교는 LoRA가 계산에
들어간다는 근거이며 특정 캐릭터 정체성이 완벽히 따라간다는 근거는 아니다. 같은 시드 한
쌍씩의 기능 확인이므로 타율이나 모든 LoRA의 품질 보장이 아니다.

Krea2/MOSS/SD1.5의 완성 이미지에 이번 영역별 LoRA를 적용한 품질 시험은 하지 않았다.
기존 모델별 좌표/상자 경로의 CPU 회귀 검사는 통과했다. MOSS native에서는 캐릭터별
CLIP LoRA를 지원하지 않아 regional 모드 또는 CLIP 0이 필요하다. Anima llm_adapter를
변경하는 LoRA는 사전 계산과 충돌하므로 전역 로더를 사용하도록 오류로 안내한다.

2개 LoRA의 Anima 생성은 약 146–149초로 baseline 약 30초보다 느리다. 조합마다 예측을
계산하기 때문이다. 같은 파일·모델 강도는 계산 그룹을 공유한다. 추가 checkpoint 전체를
슬롯마다 복사하지 않지만 LoRA 텐서, CLIP 패치, 계산 비용은 추가된다.

텍스트 및 상자 밖 배경에는 캐릭터 LoRA를 추가하지 않는다. 주의: attention과 후속 denoise,
VAE로 영역 밖 간접 영향이 생길 수 있다. 전체 스타일/가속 LoRA는 기존 전역 로더에서 쓴다.

NAI 요청 / Anlas 사용 없음. 시험용 8199 서버만 종료하고 평소 8188 설치본은 그대로 유지.
