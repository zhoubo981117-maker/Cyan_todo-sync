# AI Todo Organizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first-version AI organizer that turns pasted text into editable todo drafts and only saves tasks after user confirmation.

**Architecture:** Keep AI calls on the Python backend so Xiaomi API keys never reach the browser. Add a focused authenticated endpoint that validates input, calls an OpenAI-compatible Xiaomi chat-completions API, sanitizes strict JSON, and returns drafts. Add a web panel that lets the user generate, edit, select, and save drafts through the existing todo/subtask APIs.

**Tech Stack:** Python standard library HTTP server, SQLite-backed auth/session flow, vanilla HTML/CSS/JS, Xiaomi MiMo OpenAI-compatible API.

---

### Task 1: Backend AI Organizer Core

**Files:**
- Modify: `server.py`
- Test: `tests/test_ai_organizer.py`

- [ ] **Step 1: Add tests for AI draft sanitization and error cases**

Create `tests/test_ai_organizer.py` with tests that import `server`, call pure helper functions, and avoid live Xiaomi network calls. Cover empty model output, invalid JSON, too many items, urgency clamping, string cleanup, and subtask cleanup.

- [ ] **Step 2: Implement backend helper functions**

Add helper functions in `server.py`:

```python
AI_PROVIDER = os.environ.get("TODO_AI_PROVIDER", "").strip().lower()
AI_API_KEY = os.environ.get("TODO_AI_API_KEY", "").strip()
AI_MODEL = os.environ.get("TODO_AI_MODEL", "mimo-v2-flash").strip()
AI_BASE_URL = os.environ.get("TODO_AI_BASE_URL", "https://api.xiaomimimo.com/v1").strip().rstrip("/")
AI_MAX_INPUT_CHARS = int(os.environ.get("TODO_AI_MAX_INPUT_CHARS", "6000") or "6000")

def sanitize_ai_todo_items(raw: Any) -> list[dict[str, Any]]:
    ...

def parse_ai_items_from_text(text: str) -> list[dict[str, Any]]:
    ...
```

Sanitized item shape must be `{title, note, urgency, dueAt, subtasks}`. Limit to 12 todo drafts and 12 subtasks per draft.

- [ ] **Step 3: Run tests**

Run:

```powershell
python -m unittest tests.test_ai_organizer
```

Expected: all tests pass.

### Task 2: Xiaomi API Endpoint

**Files:**
- Modify: `server.py`
- Test: `tests/test_ai_organizer.py`

- [ ] **Step 1: Add endpoint tests with mocked AI caller**

Add tests that patch `server.call_xiaomi_chat_completion` and verify:

- `/api/ai/organize` requires authentication.
- Empty text returns 400.
- Missing AI config returns a clear error.
- Valid text returns sanitized draft items.

- [ ] **Step 2: Implement Xiaomi call and route**

Add:

```python
def call_xiaomi_chat_completion(text: str) -> str:
    ...
```

Use `urllib.request` to `POST {AI_BASE_URL}/chat/completions` with model, system prompt, user text, `temperature: 0.2`, and JSON-only instruction. Add authenticated route:

```text
POST /api/ai/organize
```

Return `{"items": [...]}` on success. Return controlled JSON errors for missing config, timeout, and invalid model JSON.

- [ ] **Step 3: Run backend verification**

Run:

```powershell
python -m py_compile server.py
python -m unittest tests.test_ai_organizer tests.test_feishu
```

Expected: syntax check passes and all tests pass.

### Task 3: Frontend AI Draft Panel

**Files:**
- Modify: `web/index.html`
- Modify: `web/app.js`
- Modify: `web/styles.css`

- [ ] **Step 1: Add AI panel markup**

Add an "AI 整理" card near the new todo panel with textarea, generate button, status text, draft list, and save selected button.

- [ ] **Step 2: Add frontend API and state**

In `web/app.js`, add:

```javascript
organizeTodos(text) {
  return this.request("/api/ai/organize", { method: "POST", body: JSON.stringify({ text }) });
}
```

Add `state.aiDrafts = []` and helpers to render/edit/select drafts.

- [ ] **Step 3: Save selected drafts through existing APIs**

For each selected draft, call `API.addTodo(...)`, then create its subtasks with `API.addSub(...)`. After save, clear saved drafts and call `refresh()`.

- [ ] **Step 4: Add responsive styles**

Style the AI panel to fit the existing dark UI and keep the mobile layout single-column.

### Task 4: Docs, Verification, Commit

**Files:**
- Modify: `README.md`
- Modify: `compose.yaml`

- [ ] **Step 1: Document AI environment variables**

Document:

```bash
TODO_AI_PROVIDER=xiaomi
TODO_AI_API_KEY=...
TODO_AI_MODEL=mimo-v2-flash
TODO_AI_BASE_URL=https://api.xiaomimimo.com/v1
```

- [ ] **Step 2: Run final verification**

Run:

```powershell
python -m py_compile server.py
python -m unittest tests.test_ai_organizer tests.test_feishu
git status --short
```

- [ ] **Step 3: Commit and publish**

Commit message:

```text
Add AI todo organizer
```

Publish to GitHub using the established GitHub API fallback if normal `git push` is unavailable.
