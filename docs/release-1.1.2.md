# 1.1.2 Hangeul — Reactive workflow snapshot fix

RS Workspace now snapshots workflow and widget settings through the JSON format
used by workflow files and the `/prompt` API. Native `structuredClone` rejects
otherwise serializable reactive JavaScript Proxy objects, which can prevent
app generation or model-setting persistence with a `DataCloneError`.

Resolved wildcard prompts are detached before source templates are restored.
Queued workflow provenance and saved settings do not share mutable nested
objects with the live graph. Serialization failures still restore the templates
and are reported rather than submitting a partial request. App errors also log
the original stack in the browser console to help diagnose other reports.

## Update

Update to **1.1.2**, then hard-refresh the ComfyUI browser tab with
**Ctrl+Shift+R** (macOS: **Cmd+Shift+R**). A server already serving the new files
can serve this JavaScript fix without interrupting its current generation queue.
Use the normal restart procedure after a full extension update when idle.

## Evidence and limits

The old snapshot path reproduced `DataCloneError` with nested Proxy objects.
The revised path passed browser and Node.js regressions covering a reactive
workflow, reactive wildcard metadata, model-setting snapshots, template recovery
on success and failure, independent nested copies, Unicode and large safe
integer seeds. All JavaScript regression scripts passed locally.

The original report contained only the exception message, without a stack,
frontend version or action that triggered it. These tests prove this app-side
failure mode and its fix; they do not prove the reporter used this path. The
exception is a browser serialization failure and does not identify Windows or
any other operating system. This patch does not alter model inference or claim
new image-quality validation.
