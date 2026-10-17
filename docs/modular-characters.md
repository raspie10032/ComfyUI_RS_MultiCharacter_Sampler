# Role-based character input / 역할별 캐릭터 입력 / 役割別キャラクター入力

[Example workflow](../examples/modular/two-characters-anima.json)

## 한국어

긴 입력 노드를 **프롬프트 전체·LoRA 전체·위치 전체·최종 파이프**로 분리합니다. 각 역할 노드는 **1~N번 설정을 한꺼번에 표시**합니다. 한 캐릭터를 선택해서 번갈아 편집하는 방식이 아닙니다.

```text
STRING 1 ─┐
STRING 2 ─┼→ 캐릭터 프롬프트 → 캐릭터 LoRA → 캐릭터 위치 → 최종 파이프 → 샘플러 / 디테일러
STRING N ─┘      1~N번             1~N번            1~N번
```

| 노드 | 함께 표시하는 설정 |
| --- | --- |
| RS 캐릭터 프롬프트 | 캐릭터 수, 각 번호의 사용·종류·공용 STRING 연결부. 캐릭터 UC와 문장 입력창은 없습니다. |
| RS 캐릭터 LoRA | 각 번호의 파일·모델 강도·CLIP 강도. 파일이 None인 행의 강도만 접습니다. |
| RS 캐릭터 위치 | 각 번호의 XY 또는 상자 중심·크기, 전체 예상 배치도. |
| RS 최종 캐릭터 파이프 | 완성된 배치도와 기존 샘플러·디테일러용 `character_pipe` 출력. |

세 역할의 **연결 순서는 자유**입니다. `위치 → LoRA → 프롬프트 → 최종 파이프`도 같은 결과입니다. 같은 행 번호끼리 설정이 합쳐집니다. 각 노드의 `building_pipe`를 다음 노드에 연결하고, 첫 노드의 파이프 입력은 비워둡니다. 마지막에는 반드시 최종 파이프를 둡니다.

- **최종 인원수는 프롬프트 노드 기준**입니다. LoRA·위치의 개수는 해당 표에서 설정할 행 수입니다. 보통 같은 수로 맞추면 됩니다. LoRA·위치를 생략하거나 행 수가 적으면 나머지는 None·중앙 좌표입니다.
- 캐릭터 수를 늘리면 그 역할의 여러 행이 함께 펼쳐집니다. 프롬프트 수를 줄이거나 사용을 끄면 해당 캐릭터의 옛 LoRA·좌표도 실행에서 제외됩니다. 이미 연결된 범위 밖 STRING 연결선은 지우지 않지만 실행에는 사용하지 않습니다.
- 같은 역할 노드를 다시 연결하면 **그 역할의 표 전체를 뒤쪽 노드가 교체**합니다. 다른 역할의 값은 유지됩니다. 서로 다른 역할끼리는 순서에 관계없습니다.
- 문장은 ComfyUI 기본 **Text (Multiline)** 같은 STRING 출력 노드에서 작성합니다. 공통 네거티브는 샘플러에서 설정합니다. 활성 행의 문장이 비었으면 최종 파이프가 번호를 알려줍니다.
- 위치 노드의 그림은 그 노드까지 들어온 설정, **최종 파이프의 그림은 완성된 설정**을 표시합니다. 같은 점 좌표는 번호순으로 좌우 배치합니다. 실제 구도·인원수·픽셀 마스크를 보장하는 그림은 아닙니다.
- 글자 영역은 해당 행의 종류를 `text`, 위치를 `box`로 선택합니다. **번호별 STRING 하나**에 실제 쓸 단어를 연결합니다. `character`는 같은 입력을 긍정 프롬프트로, `text`는 실제 글자로 해석합니다. 종류를 바꿔도 연결선은 그대로 유지됩니다. 해당 행의 LoRA는 None으로 둡니다. 예전 두 입력 워크플로를 열면 실제 글자 선을 공용 입력으로 옮기며, 별도 스타일 선은 사용하지 않습니다.

최대 10개 캐릭터·글자 영역이며 처리 수가 늘수록 품질을 보장하지 않습니다. 기존 파이프·샘플러·디테일러와 이미지 설정 저장·복원을 사용합니다. 이미지 로더는 완성된 설정을 복원하며 편집 노드 연결 순서까지 복원하지는 않습니다. 워크플로를 이미지에 넣으려면 일반 Save Image를 사용하세요. 기존 긴 노드는 저장된 워크플로 호환용으로 유지됩니다.

## English

Split the large node into **all prompts, all LoRAs, all positions, and Finalize**. Each role displays rows **1–N simultaneously**; there is no selected-character editor. Positive text arrives through external **STRING sockets**. There is no character UC or multiline prompt widget. Use Text (Multiline) nodes and set the common negative in Sampler.

Connect the three role nodes in **any order**, then Finalize. Matching row numbers identify the same character. LoRA and Position are optional. **Prompt count determines active slots**; the other counts determine the rows supplied by those tables, with None/center defaults beyond them. Reducing prompt count or disabling a row excludes its old LoRA/position, even if an inactive STRING remains connected. Existing inactive connections are preserved when reducing count. Repeating a role replaces that role's **whole table** with the later table without changing other roles.

Position previews settings received up to that node; Finalize shows the complete line. Coincident points spread left to right. The guide does not guarantee composition or people count. Linked dynamic settings are not guessed. Each slot has one shared STRING: character uses it as a positive prompt; text uses it as the exact words to draw, with a default lettering description. Switching kind keeps the same connection. Text needs a box Position and no character LoRA. On loading an old two-input workflow, the literal-text connection moves to the shared input; the separate style connection is no longer used. Up to ten character/text slots; quality is not guaranteed as count increases.

The output uses the existing character pipe and metadata format. Image settings restore through the image loader; autosave does not embed the editing workflow. Use Save Image for that. The previous all-in-one node stays available for old workflows.

## 日本語

長いノードを**全プロンプト・全LoRA・全位置・最終パイプ**に分割します。各役割の**1～N番の設定を同時に一覧表示**します。一人を選択して切り替える編集画面ではありません。文章は外部のText (Multiline)などから**STRINGで接続**します。個別UCや文章入力欄はなく、共通ネガティブはサンプラーで設定します。

3種類の役割は**任意の順序**で接続し、最後に最終パイプを置きます。同じ行番号の設定が合わさります。LoRA・位置は省略可能です。**有効な数はプロンプトノードが決定**し、LoRA・位置の数は各表の行数です。指定範囲外はNone・中央になります。プロンプトの数を減らすか行を無効にすると、その行の古いLoRA・位置も生成から除外します。接続済みの範囲外STRINGは線を保持しますが使用しません。同じ役割を重ねると後の**表全体**がその役割だけを置き換えます。

位置ノードはそこまでの設定、最終パイプは全設定の配置図を表示します。同一の点座標は番号順で左右に配置します。構図・人数の保証ではありません。文字領域は種類をtext、位置をboxにし、各番号でSTRINGを1つだけ接続します。characterではポジティブ文、textでは実際に描く単語として使い、種類を変えても接続は保持されます。旧形式の2入力ワークフローは文字の接続を共通入力へ移し、別の書体・色の接続は使いません。文字にLoRAは使いません。最大10領域で、数が多いほど品質を保証できません。

出力・画像メタデータは既存のサンプラー・ディテイラー・ローダーに対応します。画像から復元するのは生成設定で、編集ノードの接続順ではありません。ワークフロー埋め込みにはSave Imageを使用します。旧ノードは既存ワークフローの互換性のため残します。
