# Claude.md — технічна мапа застосунку

Документ для швидкої навігації по проєкту: де шукати логіку, куди вносити зміни, які потоки даних і які місця ризику.

## 1) Що це за проєкт

Monorepo з:
- `backend/` — FastAPI + SQLAlchemy (async) + SQLite.
- `frontend/` — React + Vite + TypeScript.

Ключові фічі:
- чат з LLM (stream + arena mode),
- маскування PII,
- секретар-агент з tool-calling (Gmail/Calendar + Microsoft),
- памʼять користувача (memories),
- метрики,
- push-нотифікації,
- digest-режим для Gmail.

## 2) Швидка карта репозиторію

- `backend/app/main.py` — головний entrypoint API, CORS, startup, підключення роутів.
- `backend/app/worker.py` — окремий воркер із cron-задачами digest.
- `backend/app/core/` — `config.py`, `database.py`, `security.py`.
- `backend/app/routers/` — HTTP API роутери.
- `backend/app/services/` — бізнес-логіка, інтеграції, pipeline.
- `backend/app/services/chat/` — модульний чат-пайплайн (контекст, PII, attachments, persist).
- `backend/app/providers/` — LLM-провайдери (OpenAI/Gemini).
- `backend/app/models/` — ORM-моделі.
- `frontend/src/main.tsx` — старт фронтенду + реєстрація SW.
- `frontend/src/App.tsx` — маршрути.
- `frontend/src/api/client.ts` — axios client + типи + API helpers.
- `frontend/src/pages/ChatPage.tsx` — основний chat UI (stream/arena/secretary).
- `frontend/src/pages/ProfilePage.tsx` — акаунт, OAuth, memories, push.

## 3) Backend: як усе зібрано

### 3.1 Entry points

- API: `backend/app/main.py`
  - створює таблиці на startup через `Base.metadata.create_all`;
  - генерує invite-коди при відсутності активних;
  - підключає роутери: `auth`, `google_auth`, `secretary`, `chats`, `metrics`, `memories`, `audio`, `digest`, `notifications`.

- Worker: `backend/app/worker.py`
  - планувальник `apscheduler` (Europe/Kyiv),
  - запускає digest для всіх користувачів 3 рази на день.

### 3.2 Конфіг і БД

- `backend/app/core/config.py` — env-параметри (`OPENAI_API_KEY`, `DATABASE_URL`, OAuth, VAPID тощо).
- `backend/app/core/database.py` — async engine/session, SQLite WAL.
- DB за замовчуванням: `backend/chat.db`.

### 3.3 API роутери (де шукати)

- Auth: `backend/app/routers/auth.py`
  - `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/change-password`.
- Chats: `backend/app/routers/chats.py`
  - CRUD чатів,
  - `POST /chats/{id}/messages` (звичайний + arena),
  - `POST /chats/{id}/messages/stream` (SSE),
  - vote endpoint для arena.
- Secretary: `backend/app/routers/secretary.py`
  - `POST /secretary/ask`, `GET /secretary/accounts`.
- Memories: `backend/app/routers/memories.py`.
- Metrics: `backend/app/routers/metrics.py`.
- Audio STT: `backend/app/routers/audio.py`.
- Google OAuth: `backend/app/routers/google_auth.py`.
- Digest: `backend/app/routers/digest.py`.
- Push: `backend/app/routers/notifications.py`.

### 3.4 Головні сервіси

- Chat orchestration:
  - `backend/app/services/chat_service.py` — фасад для роутера чату.
  - `backend/app/services/chat/pipeline.py` — основний runtime-пайплайн.
  - `backend/app/services/chat/context_builder.py` — prompt + history + memory context.
  - `backend/app/services/chat/pii_middleware.py` — mask/unmask у runtime.
  - `backend/app/services/chat/attachment_processor.py` — вкладення (зокрема PDF/image).
  - `backend/app/services/chat/transcript_persister.py` — збереження повідомлень/титулу.

- PII:
  - `backend/app/services/pii_service.py` — regex masking mapping.

- Secretary agent:
  - `backend/app/services/secretary_service.py` — tool loop (chat completions/responses API).
  - `backend/app/services/secretary_tools.py` — реалізація інструментів (mail/calendar).
  - `backend/app/services/tools_definition.py` — JSON schema інструментів.

- Інтеграції:
  - `backend/app/services/google_workspace.py`
  - `backend/app/services/microsoft_graph.py`
  - `backend/app/services/google_auth_service.py`
  - `backend/app/services/microsoft_auth_service.py`

- Digest/notifications/metrics:
  - `backend/app/services/digest_engine.py`
  - `backend/app/services/action_executor.py`
  - `backend/app/services/notification_service.py`
  - `backend/app/services/metrics_service.py`

### 3.5 LLM провайдери

- `backend/app/providers/openai_provider.py` — найскладніший провайдер, підтримка tools + retries + stream.
- `backend/app/providers/gemini_provider.py` — генерація і stream через Gemini SDK.
- `backend/app/providers/__init__.py` — `ProviderFactory`.

## 4) Frontend: де яка логіка

### 4.1 Каркас

- `frontend/src/main.tsx` — `BrowserRouter`, `App`, реєстрація `sw.js`.
- `frontend/src/App.tsx` — маршрути сторінок + `ProtectedRoute`.
- `frontend/src/context/AuthContext.tsx` — токен, профіль, auth state.
- `frontend/src/api/client.ts` — централізований API доступ та TS-типи.

### 4.2 Сторінки

- `frontend/src/pages/ChatPage.tsx`
  - чат, sidebar, stream,
  - arena mode,
  - secretary mode/auto-secretary,
  - optimistic rendering.

- `frontend/src/pages/ProfilePage.tsx`
  - user profile,
  - change password,
  - memories CRUD,
  - OAuth connect/disconnect/labels,
  - push subscription manager.

- `frontend/src/pages/MetricsPage.tsx` — метрики та leaderboard.
- `frontend/src/pages/AdminDashboard.tsx` — глобальні admin-метрики.
- `frontend/src/pages/LoginPage.tsx`, `RegisterPage.tsx`.

### 4.3 Важливий networking

- `frontend/vite.config.ts`: proxy `/api -> http://localhost:8000` з rewrite до backend root.
- В `api/client.ts`: `baseURL: '/api'`.
- У `ChatPage.tsx` stream робиться через `fetch` на `${baseURL}/chats/.../stream` (тобто теж через `/api`).

## 5) Ключові runtime-потоки

### 5.1 Звичайний чат (stream)

1. UI: `ChatPage.tsx` → `POST /chats/{id}/messages/stream`.
2. Router: `routers/chats.py` → `ChatService.send_message_stream`.
3. Pipeline: `services/chat/pipeline.py`
   - save user msg,
   - build context,
   - process attachments,
   - mask PII,
   - stream from provider,
   - unmask,
   - save assistant msg.

### 5.2 Arena mode

1. UI: `ChatPage.tsx` → `POST /chats/{id}/messages` з `models: [A, B]`.
2. `ChatService.send_arena_message` викликає обидві моделі паралельно.
3. Відповіді зберігаються як 2 assistant-message з `comparison_id` у `meta_data`.
4. Голоси: `POST /chats/{chat_id}/messages/{message_id}/vote?vote_type=...`.

### 5.3 Secretary

1. UI: `ChatPage.tsx` (`secretaryMode` або `/secretary`-команда).
2. `POST /secretary/ask`.
3. `SecretaryService.process_request`:
   - mask history/query,
   - запускає tool-calling loop,
   - виконує tools через `SecretaryTools` (Google/Microsoft),
   - unmask фінального тексту.

### 5.4 OAuth (Google/Microsoft)

1. UI (`ProfilePage`) запитує `/api/auth/{provider}/login` з Bearer-токеном.
2. Backend повертає `url` для редіректу.
3. Callback у backend зберігає/оновлює акаунт і редіректить назад на фронтенд.

## 6) Основні моделі даних

- Auth/users: `users`, `invites`.
- Chat: `chats`, `messages`.
- Memory: `memories`.
- Integrations: `google_accounts`, `microsoft_accounts`.
- Digest: `gmail_sync_states`, `email_snapshots`, `digest_runs`, `action_proposals`.
- Push: `push_subscriptions`.

Описи полів — у `backend/app/models/*.py`.

## 7) Що перевіряти першим при типових задачах

- Новий API endpoint:
  1) додати router,
  2) підключити в `backend/app/main.py`,
  3) додати helper у `frontend/src/api/client.ts`,
  4) виклик зі сторінки/компонента.

- Зміни в prompt/context:
  - `backend/app/services/chat/context_builder.py`,
  - `backend/app/services/chat/pipeline.py`,
  - secretary: `backend/app/services/secretary_service.py`.

- Зміни в PII:
  - `backend/app/services/pii_service.py` + потім `test_pii*.py`.

- Новий tool для secretary:
  1) опис у `tools_definition.py`,
  2) dispatch у `secretary_service.py`,
  3) реалізація у `secretary_tools.py` (+ клієнт інтеграції).

- OAuth проблеми:
  - роутери `google_auth.py`, `microsoft_auth.py`,
  - `config.py` (`*_CLIENT_ID`, `*_CLIENT_SECRET`, `*_REDIRECT_URI`, `FRONTEND_PUBLIC_URL`).

## 8) Відомі неузгодженості/ризики (важливо)

1. `backend/app/routers/agent_settings.py` існує, але **не підключений** у `backend/app/main.py`; фронтенд викликає `/agent-settings`.
2. `backend/app/routers/microsoft_auth.py` існує, але **не підключений** у `backend/app/main.py`; фронтенд має кнопку Connect Microsoft.
3. `frontend/src/components/ActionCard.tsx` викликає `POST /digest/action/{id}/execute` **без `user_id`**, а backend endpoint очікує `user_id` query param.
4. `backend/app/core/security.py` містить хардкод `SECRET_KEY` (потрібно винести в env).
5. `create_admin_user.py` імпортує `AsyncSessionLocal`, але в `database.py` є `SessionLocal` (скрипт виглядає застарілим).
6. Є артефакти кодування (биті символи) у `README.md` і частині рядків у коді/інтерфейсі.
7. У `backend/app/services/chat_service.py` зона arena-логіки велика і ризикова — будь-які зміни там робити обережно.
8. Частина debug/verify/test скриптів у корені та `backend/tests` може бути неактуальною до поточного auth-flow (register з invite-кодом).

## 9) Команди запуску (орієнтир)

- Backend:
  - `cd backend`
  - `uvicorn app.main:app --reload`

- Frontend:
  - `cd frontend`
  - `npm install`
  - `npm run dev`

## 10) Мінімальний чек перед змінами

1. Чи підключений потрібний router у `main.py`.
2. Чи є фронтовий виклик у `api/client.ts`.
3. Чи не ламається auth: Bearer токен + `get_current_user`.
4. Якщо чіпаємо chat runtime — перевірити stream і arena окремо.
5. Якщо чіпаємо secretary — перевірити хоча б один tool-call сценарій.

