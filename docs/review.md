# PROJECT REVIEW AND GAP ANALYSIS REQUEST

## Contradictions

| Contradiction | Documentation / Config Says | Implementation / Runtime Reality | Impact |
| :--- | :--- | :--- | :--- |
| [ ] **Default port conflict** | `README` says `http://localhost:8000` in `README.md:69`; API docs say default `8000` in `api.md:3`; model default is `8000` in `config.py:20`. | Active config uses `8080` in `system.json:5`, and `main.py:53` runs the configured port. | Users following README may open the wrong URL. |
| [ ] **System endpoint names conflict** | `api.md:10` documents `/system/startup`; `api.md:13` documents `/system/shutdown`. | Actual routes are `/system/connect`, `/system/disconnect`, and `/system/restart` in `system.py:30`. Runtime probe returned 404 for `/system/startup`. | API clients built from docs fail. |
| [ ] **Channel write body conflict** | `api.md:53` documents query param `value: float`. | `channel.py:37` requires JSON body. Runtime probe confirmed query style returns 422. | Docs and UI both guide users toward failing requests. |
| [ ] **Device toggle body conflict** | `api.md:34` says body `{"enabled": boolean}`. | `device.py:73` accepts `enabled` as a query parameter. | Client implementations may send the wrong shape. |
| [ ] **Flash status conflict** | `task.md:86` marks Phase 14 flash tasks incomplete. | Flash interface, manager, router, and mock exist in `base_flash.py:11`, `flash_manager.py:12`, `flash.py:11`, and `flash_mock.py:10`. | Roadmap understates implemented functionality. |
| [ ] **Flash upload size conflict** | Design says `>100MB` uploads in `design.md:76`; spec endpoint also says `>100MB` in `spec.md:652`. | Router enforces 10 MB at `flash.py:60` and `flash.py:67`. | Firmware users may plan around the wrong upload limit. |
| [ ] **Fault injection status conflict** | Spec defines fault endpoints in `spec.md:869` and MCP tools in `spec.md:843`. | No matching routes appear in `device.py`, `system.py`, or `mcp.py`. | Feature is documented as designed but not implemented. |
| [ ] **Diagnostics/security scope conflict** | Spec lists `/system/diagnostics`, `/system/metrics`, RBAC, and audit logging in `spec.md:446`, `spec.md:447`, `spec.md:460`, and `spec.md:461`. | Actual system router exposes config/connect/restart/log stream only in `system.py:13`. | Requirements overstate production readiness. |

## Gaps

| Priority | Gap | Evidence | Impact / Recommendation |
| :--- | :--- | :--- | :--- |
| **High** | [x] UI channel writes are broken against the actual API contract. | UI sends `PUT /channel/{id}?value=...` in `app.js:480` and `app.js:1337`, but the route requires JSON body `{"value": ...}` in `channel.py:37`. | Sliders, toggles, channel mapper writes, and UI test steps return 422. Update UI calls to `apiPut('/channel/${id}', { value: Number(val) })`. |
| **High** | [x] Raw device writes from UI have the same contract bug. | UI sends query-param write in `app.js:851`, while `device.py:97` requires a `WriteValue` body. | Device Explorer write buttons fail. Send JSON body instead. |
| **High** | [x] Test runner UI bypasses the backend `/test/run` engine. | Backend has JSONL execution at `test.py:9`, but UI manually loops and writes channels in `app.js:653`. | UI tests do not exercise the real concurrency lock/history engine and currently hit the broken query write path. Generate JSONL and call `/test/run`. |
| **Medium** | [x] Quick Look oscilloscope can throw at runtime. | `openQuickOscilloscope` uses undefined `chartContainer` in `app.js:1366`. | Clicking waveform Quick Look may fail before chart creation. Use `container.clientWidth/clientHeight`. |
| **Medium** | [x] UI config references non-existent channels. | `ui.json:19` and `ui.json:55` reference `test`; no such channel exists in `channels.json`. | Numeric and waveform widgets subscribe to missing streams and produce 404/no data. Replace with valid channels or add `test`. |
| **Medium** | [x] Config recovery does not meet the documented behavior. | Docs promise fresh defaults in `spec.md:254`, but `config_manager.py:53` only returns `model_class()` if possible and does not persist a default. | Mandatory configs like `SystemConfig` cannot default cleanly. Add explicit defaults and write them to disk. |
| **Medium** | [x] Missing per-plugin JSON defaults are not created. | Spec promises default device config creation in `spec.md:515`, but discovery only loops existing `device_*.json` files in `device_manager.py:31`. | Dropping in a plugin without JSON silently skips it. Create default JSON from plugin metadata or log a clear actionable error. |
| **Medium** | [x] Partial connect failures return success without a failure summary. | `device_manager.py:65` logs per-device errors but still marks system connected at `device_manager.py:75`; `system.py:36` returns success. | Users can think the bench is healthy when only some devices connected. Return per-device results and use warning/partial status. |
| **Medium** | [x] Test dependencies are missing. | `pytest.ini:2` configures async pytest behavior, but `requirements.txt` does not include `pytest` or `pytest-asyncio`. | `python -m pytest` failed with `No module named pytest`. Add test extras or dev requirements. |
| **Low** | [x] Static UI diagnostics are noisy. | Problems panel reports many inline-style warnings starting at `index.html:20`. | Not a runtime blocker, but it hides meaningful frontend diagnostics. Move repeated inline styles to CSS over time. |
