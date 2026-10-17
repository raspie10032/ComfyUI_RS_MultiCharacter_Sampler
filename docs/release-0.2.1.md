# 0.2.1 Giyeok Fix / 기역 픽스 / キヨク修正版

Fixes the Character Prompt node showing both character and text inputs. Each row
now has **one shared STRING socket**. Character mode uses its value as a positive
prompt; text mode uses it as the literal words to draw. Switching kind retains
the socket and its connection.

[Usage in English / 한국어 / 日本語](modular-characters.md) ·
[Role-based nodes introduced in 0.2.0](release-0.2.0.md)

## Compatibility

- Loading an old two-input workflow moves its literal-text connection to the
  shared input. The former style connection is disconnected; its source node is
  retained. Text mode uses a default lettering description.
- Saved API prompts with separate styling and literal-text values remain
  supported. New workflows serialize only the shared input.
- Text regions still require a box position and no character LoRA.
- Role ordering, the final character pipe, sampling and metadata formats retain
  their existing behavior.
- Update and restart ComfyUI, then refresh the browser to load the new frontend.

## Validation scope

The shared-input fix passed 122 Python tests and five JavaScript test files.
Browser checks covered kind switching, connection retention, save/reload and
old two-input workflow migration. Execution on the installed ComfyUI confirmed
that a character prompt and the literal text `HELLO` reached their respective
regions in the final pipe. These checks cover input routing and compatibility;
this fix did not run a new diffusion image-generation benchmark.

## 한국어

**0.2.1 기역 픽스**는 캐릭터·텍스트 입력부가 동시에 나타나는 문제를 수정합니다.
번호별 **STRING 하나**를 받고, 종류에 따라 긍정 프롬프트 또는 실제로 그릴
글자로 해석합니다. 종류를 바꿔도 연결선을 유지합니다. 예전 두 입력 워크플로는
실제 글자 연결을 공용 입력으로 옮기며, 별도 서체·색 설명용 연결은 해제합니다.
연결됐던 원본 STRING 노드는 남깁니다. 텍스트는 위치를 box, LoRA를 None으로
설정하세요. 업데이트 후 ComfyUI를 재시작하고 브라우저를 새로고침하세요.

## 日本語

**0.2.1 Giyeok Fix**はキャラクター用と文字用の入力が同時に表示される不具合を
修正します。各番号で**共通のSTRINGを1つ**使い、種類に応じてポジティブ文か
実際に描く文字として解釈します。切り替えても接続を保持します。旧形式は
文字の接続を共通入力へ移し、別の書体・色の接続を解除しますが、元のSTRING
ノードは残します。文字は位置をbox、LoRAをNoneにしてください。更新後は
ComfyUIを再起動してブラウザーを再読み込みしてください。
