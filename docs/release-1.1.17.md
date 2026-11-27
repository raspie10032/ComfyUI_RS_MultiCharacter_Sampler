# 1.1.17 Hangeul

This release adds experimental Korean lettering for **Anima Base v1.0 (2B)**. The v0.1 beta pack combines a LoRA and learned embeddings for 3,000 Hangul syllables. [Model card and evaluation](https://huggingface.co/raspie/RS-Anima-Korean-Text)

- **Regional lettering.** Connect Anima's MODEL and CLIP directly to the sampler and select the beta under `korean_text_pack`. Set the lettering row to `text` and its position to `box`. Active boxes containing Hangul use the pack. Give English its own box with a gap between it and the Korean box to preserve the base Anima prediction there. Disable unused rows. [Download the BBox workflow](https://huggingface.co/raspie/RS-Anima-Korean-Text/resolve/main/RS-Anima-Korean-Text-BBox.json)
- **Prompt-only lettering.** Connect MODEL and CLIP through the built-in **RS Anima Korean Text Loader** to apply the pack to the whole image. In the positive prompt, describe the surface and put the exact lettering in quotes. [Download the prompt-only workflow](https://huggingface.co/raspie/RS-Anima-Korean-Text/resolve/main/RS-Anima-Korean-Text-Prompt-Only.json)
- **First use.** Queue the workflow to download the approximately 114 MB pack into `ComfyUI/models/rs_anima_korean_text/`. The sampler verifies the download's size and SHA-256. The regional option defaults to Off.

Korean boxes use Precision LoRA predictions. If the workflow also needs an image reference, choose Reference Frame. Role K/V and SnapRef are incompatible with Korean box mode.

The pack is experimental. In prompt-only testing, the checkpoint exactly rendered 30/48 new Korean-only samples and 0/8 mixed Korean–English samples. In the two-seed BBox flag example, `WIN` was exact in both and `별빛` in one. [Model card and sample images](https://huggingface.co/raspie/RS-Anima-Korean-Text)

## 한국어

**Anima Base v1.0(2B)**에 실험용 한글 글자 생성을 추가했습니다. 베타 팩에는 LoRA와 한글 3,000음절을 학습한 임베딩이 들어 있습니다. [모델 카드와 평가 결과](https://huggingface.co/raspie/RS-Anima-Korean-Text)

- **BBox에서 한글 쓰기.** Anima의 MODEL과 CLIP을 샘플러에 직접 연결하고 `korean_text_pack`에서 베타 팩을 선택하세요. 글자 행은 `text`, 위치는 `box`로 설정합니다. 켜진 상자 중 한글이 있는 곳에만 팩이 적용됩니다. 영문 상자는 한글 상자와 간격을 두면 그 영역에 기본 Anima가 쓰입니다. 쓰지 않는 행은 끄면 됩니다. [BBox 워크플로 다운로드](https://huggingface.co/raspie/RS-Anima-Korean-Text/resolve/main/RS-Anima-Korean-Text-BBox.json)
- **프롬프트에서 한글 쓰기.** 내장 **RS Anima Korean Text Loader**에 MODEL과 CLIP을 연결하면 팩을 이미지 전체에 적용합니다. 긍정 프롬프트에 글자가 들어갈 표면을 설명하고, 쓸 문구를 따옴표로 감싸세요. [프롬프트 전용 워크플로 다운로드](https://huggingface.co/raspie/RS-Anima-Korean-Text/resolve/main/RS-Anima-Korean-Text-Prompt-Only.json)
- **첫 실행.** 약 114 MB 팩을 `ComfyUI/models/rs_anima_korean_text/`에 내려받고 파일 크기와 SHA-256을 확인합니다. 샘플러의 기본값은 Off입니다.

한글 상자는 정밀 LoRA 방식으로 처리합니다. 이미지 참조를 함께 쓸 때는 Reference Frame을 선택하세요. Role K/V와 SnapRef는 한글 상자와 함께 사용할 수 없습니다.

프롬프트 전용 새 문구의 완전 일치는 한글 단독 30/48, 한영 혼합 0/8이었습니다. 한글과 영문을 서로 다른 상자에 넣은 깃발 예제에서는 두 시드 중 `WIN`이 두 번, `별빛`이 한 번 맞았습니다. [모델 카드와 예제 이미지](https://huggingface.co/raspie/RS-Anima-Korean-Text)
