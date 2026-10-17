# Two people + object workflows

Requires **0.1.5 Epsilon or later**. Select the model files installed on your machine.

These use the existing **Anima — mixed** and **Krea 2 Turbo** presets. They are normal ComfyUI workflow JSON files; corresponding `-api.json` files are for API clients. Prompts, seeds and generation values match the recorded trial.

Slots 1–2 use character points. Slot 3 uses a generic `character` box containing an object description. This object remains a character-pipe entry and is **not automatically excluded from face detailing**; these examples end at generation.

| Object | Anima | Krea 2 Turbo | Seed |
|---|---|---|---:|
| apple | [Workflow](01-apple-anima.json) / [API](01-apple-anima-api.json) | [Workflow](01-apple-krea2.json) / [API](01-apple-krea2-api.json) | 830868837 |
| teapot | [Workflow](02-teapot-anima.json) / [API](02-teapot-anima-api.json) | [Workflow](02-teapot-krea2.json) / [API](02-teapot-krea2-api.json) | 3034467454 |
| flowers | [Workflow](03-flowers-anima.json) / [API](03-flowers-anima-api.json) | [Workflow](03-flowers-krea2.json) / [API](03-flowers-krea2-api.json) | 2345733486 |
| teddy | [Workflow](04-teddy-anima.json) / [API](04-teddy-anima-api.json) | [Workflow](04-teddy-krea2.json) / [API](04-teddy-krea2-api.json) | 2020488034 |
| book | [Workflow](05-book-anima.json) / [API](05-book-anima-api.json) | [Workflow](05-book-krea2.json) / [API](05-book-krea2-api.json) | 3784684837 |
| camera | [Workflow](06-camera-anima.json) / [API](06-camera-anima-api.json) | [Workflow](06-camera-krea2.json) / [API](06-camera-krea2-api.json) | 1868553389 |
| lantern | [Workflow](07-lantern-anima.json) / [API](07-lantern-anima-api.json) | [Workflow](07-lantern-krea2.json) / [API](07-lantern-krea2-api.json) | 3615478632 |
| cake | [Workflow](08-cake-anima.json) / [API](08-cake-anima-api.json) | [Workflow](08-cake-krea2.json) / [API](08-cake-krea2-api.json) | 1527163390 |
| basketball | [Workflow](09-basketball-anima.json) / [API](09-basketball-anima-api.json) | [Workflow](09-basketball-krea2.json) / [API](09-basketball-krea2-api.json) | 2050307009 |
| cactus | [Workflow](10-cactus-anima.json) / [API](10-cactus-anima-api.json) | [Workflow](10-cactus-krea2.json) / [API](10-cactus-krea2-api.json) | 915598712 |

[All images, observations and limits](../../../docs/object-layout-validation.md) · [Preset controls](../../../docs/model-presets.md)

The existing preset only copies sampler values. It does not fill in object prompts, change region count or set the box; load the workflow for that setup. These settings do not guarantee exact object bounds or a general success rate.

한국어: 영역 수 3개 중 두 칸은 사람의 좌표, 마지막 칸은 물체를 적은 상자입니다. 상자는 정확한 크기 제한이 아니며, 이 물체 슬롯은 디테일러에서 자동 제외되지 않습니다.

日本語: 3領域のうち2枠は人物の座標、最後の枠は物体を記述した矩形です。矩形は正確な大きさの制限ではなく、この物体枠はディテイラーから自動除外されません。
