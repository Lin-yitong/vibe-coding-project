# MewHelp Ch01 Chat UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pixel-style Vue chat workspace that streams the existing MewHelp SSE replies into multi-turn, browser-local conversations.

**Architecture:** The SPA owns browser-only sessions and message rendering; the existing FastAPI service remains the source of assistant replies and server-side in-process history. `chatClient.ts` is the only SSE parser/network boundary; `App.vue` coordinates sessions and components receive typed props/events.

**Tech Stack:** Vue 3, Vite, TypeScript, Vitest, Vue Test Utils, jsdom, native Fetch/ReadableStream, CSS.

**Spec:** `docs/superpowers/specs/2026-09-13-mewhelp-ch01-chat-ui-design.md`

## Global Constraints

- Create the UI only under `MewHelp/frontend/`; do not modify `/api/chat` or add a database, tool call, Agent loop, or backend persistence.
- Use the existing `POST /api/chat` SSE protocol: JSON `delta`, JSON `error`, and `[DONE]`.
- Never render upstream reasoning, tool-call badges, or invented order/logistics/refund information.
- Store front-end session metadata and messages in browser `localStorage`; reuse each `session_id` across follow-up requests.
- Desktop layout is two columns; below `768px` the session sidebar becomes a collapsible panel.
- Use no external images, fonts, or CSS libraries; avatar and pixel design are local CSS/Unicode only.

---

## Planned File Structure

| File | Responsibility |
| --- | --- |
| `MewHelp/frontend/package.json` | Vue/Vite scripts and dev/test/build dependencies. |
| `MewHelp/frontend/vite.config.ts` | Vue plugin, test environment, `/api` development proxy to port 8000. |
| `MewHelp/frontend/src/api/chatClient.ts` | `POST /api/chat` fetch plus incremental SSE frame parsing. |
| `MewHelp/frontend/src/types/chat.ts` | UI message/session/event types. |
| `MewHelp/frontend/src/composables/useChatSessions.ts` | UUID creation, localStorage persistence, send orchestration. |
| `MewHelp/frontend/src/components/*.vue` | Sidebar, header, bubble, and composer presentation/interaction units. |
| `MewHelp/frontend/src/App.vue` | Typed composition of sessions, streaming state, and layout. |
| `MewHelp/frontend/src/styles/index.css` | Responsive pixel-style tokens and layout. |
| `MewHelp/frontend/src/**/*.spec.ts` | Focused parser, composable, and component tests. |
| `MewHelp/README.md` | Frontend install/run/build instructions. |

### Task 1: Scaffold a testable Vue/Vite frontend

**Files:**
- Create: `MewHelp/frontend/package.json`, `MewHelp/frontend/index.html`, `MewHelp/frontend/tsconfig.json`, `MewHelp/frontend/vite.config.ts`
- Create: `MewHelp/frontend/src/main.ts`, `MewHelp/frontend/src/App.vue`, `MewHelp/frontend/src/styles/index.css`
- Test: `MewHelp/frontend/src/App.spec.ts`

**Interfaces:**
- Produces: `npm run dev`, `npm run test`, and `npm run build` from `MewHelp/frontend/`.

- [ ] **Step 1: Write a failing Vue smoke test**

```ts
import { mount } from '@vue/test-utils'
import App from './App.vue'

it('renders the MewHelp customer-service title', () => {
  expect(mount(App).get('h1').text()).toContain('小喵')
})
```

- [ ] **Step 2: Run it to verify RED**

Run: `cd MewHelp/frontend && npm run test -- --run src/App.spec.ts`

Expected: FAIL because the Vue project is absent.

- [ ] **Step 3: Add the minimal scaffold**

Use `vue@^3`, `vite@^6`, `@vitejs/plugin-vue`, `typescript`, `vitest`, `jsdom`, and `@vue/test-utils`. Configure Vite to proxy `/api` to `http://127.0.0.1:8000` and Vitest with `environment: 'jsdom'`. Create an `App.vue` with only the required title, then import `styles/index.css` in `main.ts`.

- [ ] **Step 4: Verify GREEN and production build**

Run: `cd MewHelp/frontend && npm run test -- --run src/App.spec.ts && npm run build`

Expected: test PASS and Vite produces `dist/`.

- [ ] **Step 5: Commit**

```bash
git add MewHelp/frontend
git commit -m "chore: scaffold MewHelp chat frontend"
```

### Task 2: Implement typed SSE parsing and browser session state

**Files:**
- Create: `MewHelp/frontend/src/types/chat.ts`, `MewHelp/frontend/src/api/chatClient.ts`, `MewHelp/frontend/src/composables/useChatSessions.ts`
- Test: `MewHelp/frontend/src/api/chatClient.spec.ts`, `MewHelp/frontend/src/composables/useChatSessions.spec.ts`

**Interfaces:**
- Produces: `streamChat(request: { sessionId: string; message: string }, handlers: { onDelta(delta: string): void; onDone(): void; onError(message: string): void }): Promise<void>`.
- Produces: `ChatSession { id: string; title: string; preview: string; messages: ChatMessage[] }` and `ChatMessage { id: string; role: 'user' | 'assistant'; content: string; status: 'complete' | 'streaming' | 'error' }`.

- [ ] **Step 1: Write parser and persistence RED tests**

```ts
it('parses split delta frames and DONE', async () => {
  mockFetchSse(['data: {"delta":"您', '好"}\n\ndata: [DONE]\n\n'])
  const deltas: string[] = []
  await streamChat({ sessionId: 's', message: 'hi' }, { onDelta: d => deltas.push(d), onDone, onError })
  expect(deltas).toEqual(['您好'])
  expect(onDone).toHaveBeenCalledOnce()
})

it('restores saved sessions from localStorage', () => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify([savedSession]))
  expect(useChatSessions().sessions.value[0].id).toBe(savedSession.id)
})
```

- [ ] **Step 2: Verify RED**

Run: `cd MewHelp/frontend && npm run test -- --run src/api/chatClient.spec.ts src/composables/useChatSessions.spec.ts`

Expected: FAIL because modules are absent.

- [ ] **Step 3: Implement the smallest boundaries**

`chatClient.ts` must buffer decoded stream text, split only on blank SSE-frame boundaries, accept only `data:` lines, parse delta JSON, surface protocol/HTTP/network errors, and ignore unknown fields. `useChatSessions.ts` must create IDs via `crypto.randomUUID()` with a timestamp/random fallback, persist after every mutation, create/activate sessions, and return a reactive current session.

- [ ] **Step 4: Verify GREEN**

Run: `cd MewHelp/frontend && npm run test -- --run src/api/chatClient.spec.ts src/composables/useChatSessions.spec.ts`

Expected: PASS for split frames, done/error, persistence, and UUID fallback.

- [ ] **Step 5: Commit**

```bash
git add MewHelp/frontend/src
git commit -m "feat: add browser chat session and SSE client"
```

### Task 3: Build presentational chat components

**Files:**
- Create: `MewHelp/frontend/src/components/SessionSidebar.vue`, `ChatHeader.vue`, `MessageBubble.vue`, `ChatComposer.vue`
- Test: `MewHelp/frontend/src/components/SessionSidebar.spec.ts`, `MessageBubble.spec.ts`, `ChatComposer.spec.ts`

**Interfaces:**
- `SessionSidebar` consumes `sessions`, `activeSessionId`, `open`; emits `select(id)`, `new`, `close`.
- `MessageBubble` consumes `message: ChatMessage`; renders a streaming cursor only for `status === 'streaming'`.
- `ChatComposer` consumes `disabled`, `busy`; emits `send(message)` and never emits blank trimmed text.

- [ ] **Step 1: Write component RED tests**

```ts
it('sends on Enter but keeps a newline on Shift+Enter', async () => {
  const wrapper = mount(ChatComposer)
  await wrapper.get('textarea').setValue('退款申请')
  await wrapper.get('textarea').trigger('keydown.enter')
  expect(wrapper.emitted('send')?.[0]).toEqual(['退款申请'])
})

it('shows only assistant content, never a tool badge', () => {
  expect(mount(MessageBubble, { props: { message: assistant } }).text()).not.toContain('调用')
})
```

- [ ] **Step 2: Verify RED**

Run: `cd MewHelp/frontend && npm run test -- --run src/components`

Expected: FAIL because components are absent.

- [ ] **Step 3: Implement focused components**

Use typed `defineProps`/`defineEmits`. The header contains CSS-only cat avatar, online dot, brand, and new-chat button. Sidebar shows session title/preview and current state. Composer uses a textarea with `@keydown.enter.exact.prevent`; Shift+Enter is unhandled. Bubbles have semantic labels and no backend/tool metadata UI.

- [ ] **Step 4: Verify GREEN**

Run: `cd MewHelp/frontend && npm run test -- --run src/components`

Expected: PASS for send keyboard behavior, disabled state, selected session, and streaming cursor.

- [ ] **Step 5: Commit**

```bash
git add MewHelp/frontend/src/components
git commit -m "feat: add MewHelp chat UI components"
```

### Task 4: Compose streaming interaction and pixel-responsive layout

**Files:**
- Modify: `MewHelp/frontend/src/App.vue`, `MewHelp/frontend/src/styles/index.css`
- Test: `MewHelp/frontend/src/App.spec.ts`

**Interfaces:**
- Consumes: Tasks 2–3 interfaces.
- Produces: browser flow that adds user message immediately, appends every delta to one assistant message, saves on done/error, and disables concurrent sends.

- [ ] **Step 1: Write App RED tests**

```ts
it('grows one assistant bubble as deltas arrive and re-enables sending on DONE', async () => {
  mockStream(({ onDelta, onDone }) => { onDelta('您好'); onDelta('，请提供订单号'); onDone() })
  const wrapper = mount(App)
  await send(wrapper, '订单未发货')
  expect(wrapper.text()).toContain('您好，请提供订单号')
  expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeUndefined()
})
```

- [ ] **Step 2: Verify RED**

Run: `cd MewHelp/frontend && npm run test -- --run src/App.spec.ts`

Expected: FAIL because App has only the scaffold title.

- [ ] **Step 3: Implement composition and CSS**

App appends user then streaming assistant messages, calls `streamChat`, appends deltas only to that message, replaces its status on done/error, scrolls a `ref` container after each DOM update, and delegates `new`/`select` to the composable. Use CSS variables for orange/cream/ink colors, 4px hard shadows, square borders, grid background, desktop two-column grid, and `@media (max-width: 767px)` sidebar overlay/collapse. Show “客服正在处理…” while busy, without displaying reasoning.

- [ ] **Step 4: Verify interaction and build**

Run: `cd MewHelp/frontend && npm run test -- --run && npm run build`

Expected: all frontend tests and build PASS.

- [ ] **Step 5: Commit**

```bash
git add MewHelp/frontend/src
git commit -m "feat: stream SSE replies in pixel chat workspace"
```

### Task 5: Document and perform integrated verification

**Files:**
- Modify: `MewHelp/README.md`, `MewHelp/Makefile`
- Test: no new file; run existing frontend/backend suites.

**Interfaces:**
- Produces: `make frontend-dev`, `make frontend-test`, `make frontend-build` from `MewHelp/`.

- [ ] **Step 1: Add failing documentation-command expectation**

Add a small shell-checked test or Make dry-run assertion that requires each frontend Make target to delegate to the corresponding `frontend/npm` command.

- [ ] **Step 2: Verify RED**

Run: `cd MewHelp && make -n frontend-dev`

Expected: target absent.

- [ ] **Step 3: Add commands and README instructions**

Add:

```make
frontend-dev:
	cd frontend && npm run dev
frontend-test:
	cd frontend && npm run test -- --run
frontend-build:
	cd frontend && npm run build
```

Document `npm install`, starting `make dev` and `make frontend-dev` in separate terminals, opening Vite's URL, and the three manual browser acceptance steps from the spec.

- [ ] **Step 4: Full verification**

Run:

```bash
cd MewHelp && make test && make frontend-test && make frontend-build
```

Expected: backend suite, frontend suite, and frontend production build all PASS.

- [ ] **Step 5: Browser acceptance with local credentials**

Run `make dev` and `make frontend-dev`, open Vite's displayed local URL, send a question, observe growing assistant text, send a follow-up in the same session, then start a new conversation and confirm message lists do not mix.

- [ ] **Step 6: Commit**

```bash
git add MewHelp/README.md MewHelp/Makefile
git commit -m "docs: add MewHelp chat UI development workflow"
```

## Plan Self-Review

- Spec coverage: Task 1 creates the required Vue/Vite platform; Task 2 owns SSE parsing and local sessions; Task 3 owns independently testable UI controls; Task 4 composes multi-turn streaming and responsive pixel styling; Task 5 covers commands, build, backend compatibility, and browser acceptance.
- Type consistency: all components share `ChatSession`/`ChatMessage` from Task 2, and `App.vue` is the only consumer of `streamChat` callbacks.
- Scope: the plan adds no backend endpoint or order/tool logic; no visual element presents fabricated data or reasoning.
