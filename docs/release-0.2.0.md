# 0.2.0 Giyeok / 기역 / キヨク

Split the growing character input into four nodes: **Character Prompt, Character
LoRA, Character Position, and Finalize Character Pipe**. Each role displays its
1–N rows together. Connect Prompt, LoRA and Position in any order, then Finalize;
matching row numbers compose into the existing sampler/detailer character pipe.

[Usage in English / 한국어 / 日本語](modular-characters.md) ·
[Two-character Anima workflow](../examples/modular/two-characters-anima.json)

## Behavior and compatibility

- Positive prompts arrive through external **STRING connections**. The new nodes
  have no individual negative prompt field; set the common negative in Sampler.
- LoRA exposes each character's file, model strength and CLIP strength.
- Position provides XY/box settings and a shared layout preview. Finalize shows
  the complete layout and outputs the existing character pipe.
- Prompt count determines active slots. Reducing it or disabling a row excludes
  that row's previous LoRA and position settings. Connected inactive STRING inputs
  are preserved, but excluded from generation.
- LoRA and Position are optional; missing rows default to no LoRA and center
  coordinates. Repeating a role replaces that role's whole table with the later
  table. Other roles retain their settings.
- Up to ten character/text slots are supported. The layout preview is a guide,
  not a guarantee of exact composition or people count.
- The deprecated all-in-one node remains registered for saved workflows.
  Existing sampling, detailing, image settings and metadata formats are retained,
  including the Anima LoRA correction from [0.1.7 Zeta Fix](release-0.1.7.md).

## Validation scope

The role-node implementation was validated before this version-label update:
119 Python tests and five JavaScript test files passed. Builder coverage includes
all six role orders, count reduction, disabled rows, repeated roles, independent
branches, legacy equivalence, ten slots and metadata round trips.

The actual ComfyUI browser check displayed all five rows simultaneously, preserved
STRING connections while reducing counts, and saved/reopened the workflow.
A real Anima generation with two distinct character LoRAs, 1024×768, 30 steps and
Euler ancestral / SGM uniform matched the previous all-in-one node's image pixels
and PNG metadata exactly. This comparison is one Anima case, not a new generation
benchmark for every model family or the detailer.

## 한국어

**0.2.0 기역**은 긴 캐릭터 입력 노드를 **프롬프트·LoRA·위치·최종 파이프**로
분리합니다. 각 역할에서 1~N번 설정을 한꺼번에 보며, 세 역할의 연결 순서는
자유입니다. 긍정 프롬프트는 외부 STRING 연결로 받고 개별 UC 입력은 없습니다.
위치와 최종 파이프에서 예상 배치도를 확인할 수 있습니다. 기존 긴 노드는
저장된 워크플로 호환용으로 유지합니다. 최종 파이프는 기존 샘플러·디테일러에
연결하며, 공통 네거티브는 샘플러에서 설정합니다.

## 日本語

**0.2.0 Giyeok（기역・キヨク）**では、長い入力ノードを**プロンプト・LoRA・
位置・最終パイプ**に分割します。各役割の1～N番を同時に表示し、3種類の
接続順は自由です。ポジティブは外部STRINGで接続し、個別UC入力はありません。
位置と最終パイプに配置図を表示します。旧ノードは保存済みワークフロー用に
維持します。最終パイプは既存のサンプラー・ディテイラーに接続し、共通
ネガティブはサンプラーで設定します。
