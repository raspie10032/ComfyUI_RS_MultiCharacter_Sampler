# 1.1.3 Hangeul — Prompt autocomplete

RS Workspace reuses the original ComfyUI prompt textarea so an installed,
enabled Custom Scripts AutoCompleter or Autocomplete-Plus can keep providing
its suggestions. Autocomplete++ is also detected; its full UI integration has
not been exercised. rgthree Power Prompt is not a global autocomplete provider.

When no known provider is enabled, RS supplies lightweight offline suggestions
from bundled tags, prompt tags already in the graph and local wildcard filenames.
Use Up/Down to select, Tab/Enter to insert, Escape to dismiss, and Ctrl+Space to
open suggestions. Weighted text and trailing prompts are retained. IME composition
is protected, and literal typography inputs are excluded.

An existing user dictionary can be copied to `web/autocomplete.txt` inside this
extension. Custom Scripts `tag,count` text and A1111 CSV files are supported.
Counts prioritize matches, aliases insert canonical tags, and parentheses are
escaped. The optional dictionary is personal data: it is ignored by Git and
is not included in the release. No third-party extension or dictionary is
automatically downloaded.

Update the extension, restart ComfyUI when idle, then hard-refresh the browser
with Ctrl+Shift+R (macOS: Cmd+Shift+R). Built-in suggestions can be switched off
with `RS: Built-in prompt autocomplete` in ComfyUI settings. External providers
retain their own enable settings.

## Validation scope

Token insertion, provider dispatch, dictionary parsing, line endings, wildcard
names, weighted prompts and literal text exclusion have regression coverage.
Actual browser checks of the fallback, original textarea reuse, tab changes,
popup cleanup, and Custom Scripts/Autocomplete-Plus integration are recorded in
[prompt autocomplete validation](prompt-autocomplete-validation.md). External
provider data used in integration checks was represented by small fixtures;
compatibility with every third-party configuration is not claimed. This UI
release does not change model inference or claim new image-generation tests.

Release checks: Python unittest discovery ran 427 tests successfully (413 passed,
14 skipped) against the local ComfyUI runtime. All 20 JavaScript regression
scripts passed, including camera Python parity checks.
