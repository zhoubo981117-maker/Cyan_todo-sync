# AI Todo Organizer Design

## Goal

Add a first-version AI assistant that turns pasted free-form text into editable todo drafts. The AI must not directly create tasks without user confirmation.

## Scope

This iteration covers one input path:

- User pastes text such as meeting notes, chat records, or rough thoughts.
- Server sends the text to Xiaomi MiMo.
- Server returns structured todo drafts.
- User reviews, edits, selects, and saves drafts as real todos.

This iteration does not cover voice input, automatic daily planning, calendar integration, or Feishu/WeChat AI ingestion.

## User Flow

1. User clicks an "AI 整理" entry in the web app.
2. User pastes text into a textarea.
3. User clicks "生成草稿".
4. App shows draft todos with title, note, urgency, due time, and subtasks.
5. User can edit or unselect individual drafts.
6. User clicks "保存选中", and the app creates normal todos through existing API behavior.

## Server Design

Add one authenticated endpoint:

```text
POST /api/ai/organize
```

Request body:

```json
{
  "text": "raw pasted text"
}
```

Response body:

```json
{
  "items": [
    {
      "title": "todo title",
      "note": "optional note",
      "urgency": 1,
      "dueAt": "2026-05-06T10:00:00+08:00",
      "subtasks": ["subtask title"]
    }
  ]
}
```

The endpoint validates login token, input length, Xiaomi configuration, and AI output shape. If Xiaomi is not configured, it returns a clear configuration error instead of failing silently.

## Xiaomi MiMo Integration

Use environment variables:

```bash
TODO_AI_PROVIDER=xiaomi
TODO_AI_API_KEY=...
TODO_AI_MODEL=mimo-v2-flash
TODO_AI_BASE_URL=https://api.xiaomimimo.com/v1
```

The server calls Xiaomi from backend only. API keys are never exposed to browser JavaScript.

The prompt asks the model to return strict JSON only. The server parses and sanitizes the result before sending it to the browser.

## Frontend Design

Add an AI organizer panel near the new-todo form:

- Textarea for pasted content.
- Generate button with loading and error states.
- Draft list with editable title/note/urgency/due date/subtasks.
- Save selected drafts button.

Drafts remain local until saved. Saving uses the same existing todo/subtask creation APIs so sync behavior remains unchanged.

## Error Handling

- Empty input: show "请先粘贴要整理的内容".
- Input too long: show a clear limit message.
- AI not configured: show "服务器未配置 AI Key".
- Xiaomi timeout or error: show retryable error.
- Invalid AI JSON: show "AI 返回格式异常，请重试".

## Tests

Add server tests for:

- AI endpoint requires authentication.
- Empty text is rejected.
- Valid mocked Xiaomi response returns sanitized drafts.
- Invalid model JSON returns a controlled error.

Manual browser checks:

- Generate drafts from pasted text.
- Edit one draft and save it.
- Confirm saved tasks appear in normal task list and survive refresh.
