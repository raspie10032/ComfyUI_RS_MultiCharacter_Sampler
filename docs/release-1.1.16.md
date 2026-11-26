# 1.1.16 Hangeul

- RS MultiCharacter Load Image confines file reads and cache hashing to the selected ComfyUI input, output or temp directory. The metadata notice uses the same rules. OpenPose PNG selections stay within the input directory.
- Workspace wildcards and the pose catalogue check resolved paths against their configured directories. File errors shown in Workspace omit absolute filesystem paths.
- The optional PixAI Tagger verifies both pinned configuration files and the model Python file before loading the architecture. Model weights load as Safetensors.

## 한국어

- RS MultiCharacter Load Image의 이미지 읽기와 캐시용 해시 계산을 선택한 ComfyUI 입력·출력·임시 폴더로 제한합니다. 메타데이터 알림에도 같은 규칙을 적용합니다. OpenPose PNG는 입력 폴더에서 읽습니다.
- Workspace 와일드카드와 포즈 목록은 링크를 해석한 실제 경로가 설정 폴더 안에 있는지 확인합니다. Workspace의 파일 오류에는 절대 경로를 표시하지 않습니다.
- 선택 기능인 PixAI Tagger는 모델을 불러오기 전에 고정 버전의 설정 파일 두 개와 Python 모델 코드를 검증합니다. 모델 가중치는 Safetensors 형식으로 읽습니다.
