# RS MultiCharacter Sampler

**渐进分辨率：**[RS 渐进分辨率采样器](docs/progressive-resolution.md)以最终宽高的0.5–1.0倍开始，使用Lanczos逐步放大，以部分细节换取大尺寸图像的采样速度。起始比例越低，细节损失和构图变化可能越大，无法保证质量。实际速度取决于模型和设置。原有多角色采样功能仍可使用。

用于 ComfyUI 的区域生成与本地细节修复。为每个角色提供独立提示词、可选 LoRA，以及点、矩形或遮罩，引导角色特征在画面中的分布。

[English](README.md) · [한국어](README.ko.md) · [日本語](README.ja.md) · **简体中文** · [繁體中文](README.zh-TW.md) · [详细文档](docs/README.md) · [更新记录](CHANGELOG.md) · [发布版本](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/releases)

**当前版本：[1.0.9 Hangeul](docs/release-1.0.9.md)。** 使用本地模型，无需安装 RS NovelAI 扩展或提供 API 密钥。

**1.0.9：** Krea 2 Turbo、MOSS专用的已训练3D姿势适配器可与分角色区域配合使用。`auto`在启用MOSS姿势控制时选择原生JSON，在Krea中选择regional。首次使用自动下载专用权重。[连接与限制](docs/pose3d.md#krea2-turbo-and-moss-pose-adapters-experimental) · [36张对比](docs/pose3d-genshin-diverse-validation.md)。

![未使用 LoRA 的 Anima 双角色示例](examples/two-characters-result.png)

**相机视角：** [RS Camera Control](docs/camera-control.md) 向RS与NAI共用上下文添加视角标签，可在节点内调整方向、高度、距离、随机视角，还可选择区域缩放、旋转和平面透视变换。生成的三维姿态取决于模型。

**相机功能参考：** [Anima 相机标签辅助](https://arca.live/b/aiart/179423561) / `ComfyUI-KR-Camera-Control`（原始署名：`ComfyUI_bsk_UI` / 灰暗x）。[参考范围与来源说明](THIRD_PARTY_NOTICES.md#camera-control-references)。

**1.0.7 实验功能：**[3D人体编辑器](docs/pose3d.md)可调整关节、手部和相机，输出编号遮罩与姿势图像。仅使用遮罩无需额外权重；姿势引导需要另接Anima 2B LLLite适配器，不保证精确关节或接触。[工作流PNG](examples/pose3d/anima-native-pose.png)。[参考v2](docs/anima-reference-v2.md)需在MODEL适配器节点中选择 `Auto: Anima v2 (2B)`。实测更快，但可能改变头发、服装并增加内存，不替换默认参考路径。v2不支持2.9B或角色独立LoRA。

## 主要功能

- 公共场景提示词与独立角色提示词，最多 **10 个角色/文字区域**。
- 为各角色指定 LoRA，通过点、矩形、外部遮罩或按编号绘制的遮罩设置位置。
- 将彩色 OpenPose PNG、JSON 或 `POSE_KEYPOINT` 数据转换为可编辑的人物遮罩。
- 检测角色，使用对应的原始提示词和 LoRA 进行局部细节修复。
- 保存 PNG/WebP 生成设置，并通过图像加载器恢复。

坐标与遮罩只引导提示词影响区域，不保证准确人数、身份、姿势或文字拼写。[角色图像参考](docs/image-reference.md) 为**实验性支持，不推荐使用**；有合适的角色 LoRA 时优先使用 LoRA。


**Anima Role K/V · 实验性：** 图像参考节点可选择编号区域各自独立的参考K/V。首次生成时自动下载约504 MiB专用适配器，默认仍使用原有参考帧。[使用方法、限制与验证](docs/anima-role-kv.md)。

**Anima 2B/2.9B参考帧：** 用户自行选择检查点，采样器自动准备匹配的参考适配器。质量和速度可能不同。独立的Role K/V适配器目前仅支持2B。[用法与限制](docs/anima-reference-frame.md)。

## 安装与更新

在 ComfyUI-Manager 中搜索 **RS MultiCharacter Sampler**，或查看 [Comfy Registry 页面](https://registry.comfy.org/publishers/raspie10032/nodes/comfyui-rs-multicharacter-sampler)。包 ID：`comfyui-rs-multicharacter-sampler`。

手动安装时，在 **`ComfyUI/custom_nodes` 文件夹内**执行：

```sh
git clone https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler.git
```

通过 Manager 更新，或在已有 Git 安装文件夹内运行 `git pull --ff-only`。安装或更新后，**重启 ComfyUI 并刷新浏览器**。同一扩展只保留一个安装副本。

需要 Python **3.11+**、Torch、NumPy 和 Pillow。ComfyUI 核心必须原生支持所选模型系列；扩散模型、匹配的文本编码器和 VAE 需自行准备。如果 Load CLIP 缺少 `krea2` 或 `moss_image` 选项，请更新核心及运行环境。参阅[兼容性与测试版本](docs/compatibility.md)。

在 ComfyUI 设置中将语言切换为 **中文**或**繁體中文**，即可显示相应的节点名称、输入/输出标签、说明面板和悬停提示。鼠标停留约 **2 秒**后显示简短说明。内部节点 ID、模型文件名及 `regional`、`moss_native` 等设置值保持原样，已有工作流仍可使用。详细专题文档目前主要为英文。

可选功能需另行配置：

| 功能 | 配置 |
| --- | --- |
| 本地细节修复 | 通过 Manager 安装 **ComfyUI-Impact-Pack** 和 **ComfyUI-Impact-Subpack**，再用 ComfyUI 的 Python 安装 `requirements-detailer.txt`。SAM 可选。执行时自动下载所选且缺失的检测/标签目录模型。 |
| 图像参考 · 实验性 | Anima 使用参考帧，Krea 2 使用 Identity Edit v2，FLUX 使用原生参考（FLUX.1 需要 Kontext）。SD1.5、SDXL、MOSS 保留现有方式。用 ComfyUI 的 Python 安装 `requirements-reference.txt`。启用参考可能下载额外模型；关闭或强度为 0 时不加载。[后端与限制](docs/image-reference.md) |

## 从示例工作流开始

加载[模块化 Anima 双角色工作流](examples/modular/two-characters-anima.json)，或使用下方对应模型的示例。普通 JSON 用于界面导入，文件名以 `-api.json` 结尾的文件用于 API。也可将原始[工作流 PNG](examples/two-characters-workflow.png) 拖入画布。

1. 在加载器中选择已安装的 **MODEL、CLIP、VAE**。Anima 示例的 Load CLIP 类型保持为 `stable_diffusion`。
2. 将 STRING 文本节点连接到 **RS 角色提示词**，每行填写对应角色的外观和动作。公共场景、风格、总人数写在采样器的公共提示词中，排除项写在公共负向提示词中。
3. 使用 **RS 角色位置**设置布局。X/Y 为 0–1，左上角是 `(0, 0)`。提示词、LoRA、位置节点的编号必须对应。
4. 将构建节点连接到 **RS 角色管线汇总**，再将 `character_pipe` 连接到 **RS 多角色采样器**。LoRA 和位置可省略，汇总前各构建节点的连接顺序不限。
5. 选择**模型系列预设 → 应用预设**，确认分辨率和模型相关设置后执行。预设只复制采样/区域参数，模型、LoRA、提示词、布局、尺寸与种子需另行选择。

自动保存将结果写入 `output/RS_MultiCharacter/`，支持 PNG、无损 WebP 和有损 WebP，并保留生成信息。若需要在图像中嵌入可编辑工作流，请使用 ComfyUI 标准的 **Save Image** 节点。

[角色构建指南](docs/modular-characters.md) · [预设数值](docs/model-presets.md) · [Anima 采样器/调度器比较](docs/sampler-combinations.md)

## 模型与示例

**RS NAI 互通：** 更新两个扩展后，角色与上下文管线、检测组合加载器及标签器可相互连接。共享提示词与坐标，并在往返时保留本地遮罩、LoRA 和各后端的生成设置。[行为与限制](docs/shared-nai-context.md)。

下列配置是起点，并非通用的质量保证。FLUX 各变体有不同工作流与采样要求。

| 模型系列 | 工作流 | 起始设置与范围 |
| --- | --- | --- |
| **Anima** | [双角色](examples/modular/two-characters-anima.json) | 主要示例；使用匹配的编码器和 Qwen Image VAE。默认 Euler ancestral / SGM uniform。 |
| **SDXL / Illustrious** | [双角色](examples/two-characters-sdxl.json) · [角色 LoRA](examples/character-lora/illustrious.json) | Load Checkpoint 提供 MODEL/CLIP/VAE。基础示例：30 步、CFG 5.5、Euler ancestral / normal。[已测试衍生模型与限制](docs/sdxl-validation.md) |
| **FLUX.1 / 2 / 3** | [各模型工作流](examples/flux) | 包括 Dev、Schnell、Klein 等变体。[变体矩阵与验证](docs/flux-validation.md) |
| **Krea 2 Turbo** | [双角色](examples/two-characters-krea2.json) · [角色 LoRA](examples/character-lora/krea2.json) | 8 步、CFG 1、Euler / simple；Qwen3-VL 4B（`krea2`）+ Qwen Image VAE。CFG 1 时公共负向不生效。 |
| **MOSS-Image SFT** | [基础](examples/two-characters-moss.json) · [8 步 LoRA](examples/moss-8step/two-cfg3.json) | 基础：50 步、CFG 3、Euler / simple；Qwen3.5 9B（`moss_image`）+ Flux2 VAE。[8 步配置](docs/moss-8step.md) 需另接加速 LoRA。 |
| **SD1.5 · 实验性，不稳定** | [双角色](examples/two-characters-sd15.json) | 已验证运行，人数和外观分离不稳定。[试验与限制](docs/sd15-validation.md) |

Krea 2 和 MOSS 的区域支持为实验性。MOSS 使用 ComfyUI 普通 CFG，不包含官方管线中负向分支跳过第 22 层的逻辑。[模型文件与验证](docs/krea-moss-validation.md)

## 角色 LoRA 与适配器

在 **RS 角色 LoRA** 中选择各角色的文件及模型/CLIP 强度。采样器前连接标准 ComfyUI LoRA 加载器可应用全局 LoRA。基础模型、适配器架构与维度必须匹配。

- **精确应用**为默认：每组 LoRA 设置独立预测，受支持路径使用低秩矩阵优化。
- **普通应用**：受支持的 Anima/SDXL 线性 LoRA 共享层计算。不支持的模型或适配器自动使用精确模式，并说明原因。两种模式的角色细节可能不同。
- 静态适配器支持 **LoRA、LoCon/Tucker、DoRA、LoHa/DoHa、LoKr/DoKr、GLoRA、OFT/BOFT、IA³ 及匹配的 diff/set 补丁**。打包 INT8/FP8 路径包括 MOSS 的部分 Q/K/V LoRA。复杂适配器可能增加耗时与临时内存。

**GGUF：**连接另行安装的 **ComfyUI-GGUF** 加载器的 MODEL 输出。应用角色 LoRA 时保留压缩权重。FLUX 使用精确模式，选择普通模式也会自动切换。[安装与已验证范围](docs/gguf-compatibility.md)

**原生量化：**在支持的模型系列中保留 FP8／INT8 压缩权重，使用所连接加载器的运算应用角色 LoRA。可用内核和画质取决于量化模型、ComfyUI 和 GPU。[格式、验证范围与限制](docs/quantization-compatibility.md)

**T-LoRA、GLoKr、其他自定义张量及改变形状的补丁不在此适配器路径的支持范围内。** 模型/CLIP 限制和数值检查见[适配器格式指南](docs/adapter-formats.md)。另见 [LoRA 配置](docs/regional-lora.md)、[模式比较](docs/shared-lora-experiment.md)和[角色 LoRA 测试矩阵](docs/character-lora-matrix-20261021.md)。

## 布局、遮罩与局部修复

在 **RS 角色位置**中拖动编号点、矩形或遮罩。外部 MASK 使用 **RS 角色遮罩**，也可通过 **RS 角色遮罩绘制**在仅供显示的参考图上涂画。[遮罩指南与示例](docs/character-masks.md)

生成**两个人和一个词**时使用三个槽位：两个 `character` 点区域与一个 `text` 矩形。将实际文字连接到文字行的 STRING，LoRA 保持 None。物体可使用 `character` 矩形槽位并填写物体描述。区域控制使用 `layout_method=regional`；MOSS 原生布局的每个区域需为矩形或遮罩。**`moss_native` 会将最终遮罩转换为外接矩形，不保留轮廓细节。** [混合布局](examples/epsilon) · [物体示例](examples/epsilon/objects) · [布局指南](docs/regional-layout.md)

**RS OpenPose 自动遮罩**从骨架构建大致的人物遮罩，不向模型输入骨架本身。可选部位名称引导默认关闭，支持 Anima/SDXL。**RS 角色重叠控制**可在 Anima/SDXL 和实验性 SD1.5 中延后非重叠区域的分离衰减。均不保证准确关节与接触。[姿势输入、预览与限制](docs/openpose-mask-guides.md) · [姿势示例](examples/openpose)

局部修复可加载[生成＋细节修复工作流](examples/two-characters-detailer-anima.json)。向 **RS 多角色细节修复**连接图像、角色管线、相同 MODEL/CLIP/VAE，以及 **RS 检测组合加载器**和 **RS 角色标签模型加载器**。建议从面部 SEGM、WD ViT v3、重绘强度 **0.25** 开始。标签模型只选择原有角色提示词，不追加推断标签。请检查输出的角色分配报告。[执行检查与限制](docs/detailer-validation.md)

## 恢复生成设置

在 **RS 多角色图像加载器**中打开原始 PNG/WebP，将其角色管线连接到采样器。图像内提示词和角色会覆盖公共提示词输入。开启 **use_image_settings** 可同时恢复种子、尺寸及采样/区域参数；使用预设或当前控件时请关闭。

模型、LoRA、CLIP、VAE 需显式连接；元数据不会自动下载或加载文件。参考图需重新连接。这是基于文本与种子的重新生成；细节修复另行执行遮罩 img2img。可导入 NAI V4 风格角色描述，但无法在本地复现其采样设置。[元数据与恢复范围](docs/architecture.md)

## 节点一览

共 **15 个节点**。界面标签与说明支持英语、韩语、日语、简体中文和繁体中文，并跟随 ComfyUI 语言设置。

| 节点 | 用途 |
| --- | --- |
| RS 角色提示词 / LoRA / 位置 / 管线汇总 | 按编号构建角色设置，输出采样器/细节修复管线。 |
| RS 角色遮罩 / 遮罩绘制 | 连接外部遮罩或按编号绘制。 |
| RS OpenPose 自动遮罩 / 角色重叠控制 | 创建姿势遮罩并调节重叠区域分离。 |
| RS 角色图像参考（实验性，不推荐） | 将参考图关联到角色编号。 |
| RS 多角色采样器 / 图像加载器 | 生成图像并恢复保存设置。 |
| RS 多角色细节修复 / 检测组合加载器 / 角色标签模型加载器 | 检测、匹配和局部修复角色。 |
| RS 多角色提示词（旧版） | 保留以兼容旧工作流，新工作流请使用模块化节点。 |

## 限制与排错

- 每次生成一张，最多 10 个输入槽位。密集布局与交叉物体可能导致多余/缺失人物、特征混合或分镜。只有一个角色时占用全画布，移动唯一的点不会移动人物。
- 区域采样器使用公共负向提示词，不支持单独角色负向及按时间调度的文本条件。
- 区域采样器不支持 SD2、专用 inpainting/refiner 检查点、FLUX Fill/Control 或外部 ControlNet/注意力补丁。可选图像参考有独立的后端与限制。
- 采样器支持 **2–100 步、CFG 1–20**。预设不识别所连接的模型，也不保证质量。优先从对应模型工作流开始。
- 恢复需原始元数据及匹配的文件/环境。社交平台可能剥离元数据；自动保存不保留无关 EXIF/GPS/相机信息。
- 报错时请在 [issue](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/issues) 中附上扩展/核心版本、准确的模型与 LoRA 版本、工作流 JSON 和完整 traceback。

[文档与验证索引](docs/README.md) 分别记录实际生成、适配器数值及 CPU/CI 兼容性检查。

## 开发与许可证

安装 Torch、NumPy、Pillow 后，在仓库根目录运行：

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_ui.cjs
```

原生集成测试可将 `RS_MC_TEST_COMFYUI` 设为 ComfyUI 源码目录。[CI 配置](.github/workflows/tests.yml) 列出全部 JavaScript 界面测试及核心/系统矩阵。

GPL-3.0-only。参阅 [COPYING](COPYING)、[第三方声明](THIRD_PARTY_NOTICES.md)及[源码来源](docs/source-lineage.json)。


**Krea2 Turbo / MOSS 3D 姿态适配器（实验）：** 将 3D 节点的 `scene_json` 连接到 **RS 3D Pose Adapter**，再将 MODEL 连接到普通 RS 采样器。自动准备已训练的姿态适配器。角色区域管道仍须连接；不保证精确关节或人数。 [Setup](docs/pose3d.md#krea2-turbo-and-moss-pose-adapters-experimental).
