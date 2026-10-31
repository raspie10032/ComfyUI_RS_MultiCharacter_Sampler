# 3D pose guidance through the building pipe

Validation date: 2026-10-31 (Asia/Seoul).

## User-facing change

`RS 3D Pose Masks` owns pose mode, strength and start/end controls. Its existing
building-pipe output carries the scene and these settings to Finalize and the RS
sampler. The sampler uses its own MODEL/VAE and selects the compatible adapter.
The pose node needs no additional model, VAE or patch-loader connection.

The workspace app uses this same route. Its former generated adapter chain is
migrated to the editor's settings. The old MODEL adapter remains deprecated for
saved workflows. Old 3D nodes without the new controls retain mask-only behavior;
select `auto` explicitly to enable learned guidance.

## Evidence

| Check | Evidence and scope |
| --- | --- |
| Python regression suite | 427 tests run, 413 passed and 14 skipped. Skips do not prove their paths. |
| JavaScript regression scripts | All 18 `tests/test_*.cjs` scripts passed; the additional `ui_source.cjs` helper also executed without error. App graph assertions verify that new graphs omit separate pose MODEL loaders. |
| Final targeted recheck | 51 pose tests run, 49 passed and 2 skipped after documentation/legacy-message cleanup. |
| Pipe and metadata | Tests cover prompt/pose insertion order, context round trips, disabled and unsupported paths without downloads, cloned deferred Krea2/MOSS routes, and conflicting adapters/references. |
| Actual Anima 2B generation | Isolated ComfyUI on RTX 5060 Ti, prompt ID `0c09a42f-9338-4c16-a11d-02fc0ec2e41a`; success recorded in history. 768×1024, 30 steps, Euler ancestral / SGM uniform, seed 2026102901, RSCV5 style LoRA 0.9. Two characters, raised-arm scene. History reports `3D pose: Anima adapter`. Execution start-to-success: 62.891 s, including preparation. |
| PNG import | `examples/pose3d/anima-building-pipe.png` was opened with ComfyUI's actual file-open UI. The graph restored the 3D preview and the auto/strength/start/end controls, with no MODEL/VAE inputs on that node. |
| Local installation | Changed files copied to the installed extension with byte equality checked. Main server `/object_info` exposes `building_pipe`, `pose_control`, `pose_strength`, `pose_start`, `pose_end` on `RSMultiCharacterPose3D`. |

The Anima PNG includes ComfyUI `workflow` and `prompt` metadata and can be
dropped into ComfyUI. The raised arm transfers, but the result does not establish
precise hand, joint or appearance fidelity.

## Limits

Anima learned guidance supports 2B, not 2.9B. Other unsupported families use masks
and report the reason. Krea2/MOSS routing has regression coverage in this change;
their actual image quality was not retested here. Their existing learned-guidance
paths still require full resolution. Learned pose guidance and image references
cannot currently be combined; the error explains the conflict.

During installation an initial queue guard stopped file replacement when work
appeared, but a separately issued restart still restarted the main service. A
running request may have been interrupted. Installation was subsequently run
inside one guarded procedure: both queues were observed empty, files were
verified, the queue was checked again and only then was the service restarted.
Stored images were preserved; no interrupted request was silently requeued.
