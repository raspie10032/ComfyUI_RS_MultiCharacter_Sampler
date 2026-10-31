# RS Workspace — app screen (experimental, included in 1.1.0)

## Opening and troubleshooting

1. Install or update **RS MultiCharacter Sampler** to **1.1.0 or later** using ComfyUI-Manager. Package ID: `comfyui-rs-multicharacter-sampler`. [Registry listing](https://registry.comfy.org/publishers/raspie10032/nodes/comfyui-rs-multicharacter-sampler).
2. For an existing Git installation, run `git pull --ff-only` inside the extension folder. For a first Git install, run the following inside `ComfyUI/custom_nodes`:

   ```sh
   git clone https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler.git
   ```

3. **Restart the ComfyUI server**. Reloading a browser alone does not reload Python routes.
4. Open your usual ComfyUI URL (the local default is `http://127.0.0.1:8188/`) and hard-refresh with **Ctrl+Shift+R**, or **Cmd+Shift+R** on macOS.
5. Click **RS Workspace** at the **bottom right**. Frontends exposing extension menu commands also offer **Edit → RS Model Workspace (Experimental)**.
6. Select your installed model, enter character prompts, edit placement and click **생성** (Generate). Required loaders and supported feature paths follow the selected model.

No separate app or server is required. Base models, encoders and VAEs are installed separately. The app currently uses Korean labels; the table below maps the main controls.

If the button is missing, check the installed version, restart the server, hard-refresh, then check that `RS.MultiCharacter.Workspace` is enabled in ComfyUI extension settings. Keep only one installation of this extension. If opening reports an inventory HTTP error, use your working ComfyUI URL and check that any reverse proxy forwards the app API paths. On older frontends requesting an empty tab, first save your current work and open a blank workflow tab.

![RS Workspace model selection and character controls](assets/app-workspace/workspace.png)

The app creates its
own workflow tab when opened from a normal user workflow. Existing workflows
are preserved. Click **노드 그래프** to return to the editable graph.

Select an installed model. The app inspects safetensors headers, selects the
matching checkpoint or split-model loaders, and connects existing public RS
nodes. Missing encoder/VAE files and unsupported feature combinations block
generation with an explanation. The app does not download a base checkpoint.

For the full Korean walkthrough, see [앱 사용 가이드](app-workspace.ko.md).

## Controls

| App label | Meaning |
| --- | --- |
| 모델 | Installed model and automatic routing |
| 캐릭터 | Character/text slots, LoRAs and references |
| 와일드카드 | Wildcard file search, insertion and seeded preview |
| 배치 / 마스크 | Point/box placement and mask drawing |
| 3D 포즈 | 3D pose editor and image-to-3D import |
| 카메라 | View, framing and interaction boundary controls |
| 생성 / 보정 | Common prompts, sampling and face detail settings |
| 결과 | Generated results |
| 생성 | Generate one image request |
| 워크플로 저장 | Download the editable workflow JSON |
| 노드 그래프 | Return to the underlying node graph |


- **캐릭터:** numbered STRING prompts, character/text choice, per-character
  LoRA and image references. Inactive slots remain saved but do not execute.
- **와일드카드:** search installed TXT files, insert `__name__` into common,
  negative or active character prompts, and preview the expansion for the
  current generation seed. `{A|B}`, nested files and wildcard filename matching
  are supported. Text/typography slots stay literal. The app reads the user,
  ComfyUI and installed extensions' wildcard folders without copying them.
- **배치 / 마스크:** the existing point/box/mask editor and drawing canvas.
  Enable drawing and paint a numbered region before generating.
- **3D 포즈:** the existing image-to-3D/scene editor. Anima 2B uses LLLite;
  Krea2 and MOSS use the scene adapters. Other supported families, including
  Anima 2.9B, use the rendered region masks without a pose adapter. The status
  panel explicitly distinguishes these routes. The editor requires WebGL2.
  The editor's building pipe carries all pose settings; no extra MODEL/VAE/patch
  nodes are needed. Select auto or masks_only and strength/start/end in this tab.
  Mask-only uses no adapter downloads. Learned pose + image references is blocked;
  Krea2/MOSS learned pose also requires full resolution.
- **카메라:** the existing shared camera editor and interaction controls.
- **생성 / 보정:** common prompts, sampling settings, progressive resolution,
  global LoRA, detection and face detail settings. Multiple characters
  automatically connect the WD tagger required for prompt matching.
- **결과:** execution previews, saved outputs and error messages.

Scene, masks and prompts stay in the workflow. Model-specific sampler, LoRA,
pose, detector, tagger and detail settings are remembered separately. Generation
uses the selected output's dependency graph; stale loaders and hidden reference
slots are excluded. Save with **워크플로 저장** and reopen through ComfyUI's
usual workflow loader. App metadata is stored in `extra.rs_workspace`; public
nodes and widgets remain the execution source of truth.

With wildcards enabled, each submitted request and saved PNG uses the resolved
prompts, including the camera and detailer. The app keeps the original templates
in `extra.rs_workspace.wildcardLast` and restores them when reopened. Ordinary
graph replay of the PNG uses the resolved widgets and does not need the original
TXT files. Continuing to draw random choices in the app requires those files.
Manual graph edits take precedence over automatic template restoration. Fixed
seeds repeat choices; random/increment seed controls retain the node behavior.
One press submits one image request; this screen has no batch-count control yet.

## Current boundaries

RS Workspace is an experimental screen distributed with this extension from
1.1.0. It runs inside ComfyUI and uses the existing public RS nodes. The catalog currently recognizes installed safetensors models from the
supported Anima, SDXL, SD1.5, FLUX1/2/3, Krea2 and MOSS families. It does not
classify arbitrary renamed text encoders or expose a GGUF loader in this screen.

Krea2/MOSS scene adapters cannot currently run together with image references
or progressive resolution. FLUX1 checkpoints need a supported Kontext path for
image references; the app blocks an unsupported combination. Anima 2.9B does
not accept the 2B Role K/V weights. These boundaries come from the existing
generation paths and are displayed before execution.

Graph routing checks do not prove image quality or every combination. See the
[release validation](app-workspace-validation.md) for tested paths and actual execution evidence.

## Downloadable example

The [1.1.0 release](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/releases/tag/v1.1.0) includes **RS-Workspace-Wildcard-Example.zip** with a workflow PNG, a small background TXT and instructions. Drop the original PNG onto ComfyUI, select locally installed model/detector/tagger files, then open RS Workspace. The node graph can replay the resolved prompts without TXT files; rerolling in the app needs the included TXT in the documented user wildcard folder. Models and personal wildcard collections are not bundled.
