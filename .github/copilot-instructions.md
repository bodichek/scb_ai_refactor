## copilot-instructions for scb_ai_refactor

Purpose: give an AI coding agent the essential, concise knowledge to be productive in this repo.

- Project type: Django (Python >=3.13, Django 5.2) monorepo with a React/Vite frontend in `frontend/`.
- Key directories: `accounts/`, `coaching/`, `ingest/`, `dashboard/`, `survey/`, `suropen/`, `chatbot/`, `exports/`, `frontend/`.

What matters most
- Django settings live in `app/settings.py`. Environment variables are loaded from a `.env` file at repo root. Important settings: `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-4o-mini`), `DEBUG` is currently set True for local dev.
- Multiple modules call OpenAI via the new OpenAI Python client (`from openai import OpenAI`). See examples in:
  - `suropen/views.py` (OpenAI client at top-level `client = OpenAI(api_key=...)`, `_ask_openai` wrapper)
  - `ingest/openai_parser.py` (PDF analysis, `MODEL = settings.OPENAI_MODEL`)
  - `survey/utils.py` and `survey/views.py` (survey summarization)
  - `chatbot/views.py` (chat API, context-specific prompts, stores `ChatMessage`)

Project-specific coding patterns
- OpenAI usage: prefer a module-level `client = OpenAI(api_key=settings.OPENAI_API_KEY)` and then helper functions that call `client.chat.completions.create(...)`. Provide `model` from settings fallback `OPENAI_MODEL`.
- Prompting convention: system prompt in Czech and responses expected in Czech. Many prompts request concise, actionable outputs and set max_tokens. See `_build_ai_prompt` in `suropen/views.py` and `ingest/openai_parser.py` for examples.
- Error handling: OpenAI calls often wrap exceptions and return human-readable fallback strings rather than raising. Mirror this behavior when adding new AI calls.
- DB interactions: chatbot and suropen persist AI responses (models `ChatMessage`, `OpenAnswer`). Prefer atomic writes for multi-row saves (see `_create_submission` in `suropen/views.py`).

Dev workflows and commands
- Python/Django (poetry-managed): use the repo-level `pyproject.toml`. Common commands (adapt to your environment):
  - Run Django dev server: `python manage.py runserver` (ensure `.env` has `OPENAI_API_KEY` for AI endpoints)
  - Run migrations: `python manage.py migrate`
  - Create superuser: `python manage.py createsuperuser`
  - Run tests: `python manage.py test` (no test runner wrapper present; tests are Django tests in apps)
- Frontend (React + Vite) in `frontend/`:
  - Install deps: `cd frontend && npm install` (or `pnpm`/`yarn` if preferred)
  - Dev server: `cd frontend && npm run dev`
  - Build: `cd frontend && npm run build`

Conventions and gotchas
- Language: UI and prompts are in Czech. New messages to users or prompt text should be Czech by default.
- OpenAI model names vary across modules (`gpt-3.5-turbo`, `gpt-4o-mini`). Use `settings.OPENAI_MODEL` when available, otherwise default to `gpt-4o-mini`.
- .env: Sensitive keys are read by `python-dotenv`. Do not hardcode API keys. Some local VS Code settings may contain OpenAI keys (inspect `vscode-userdata/`), remove if committing.
- Tests: some test endpoints check that `OPENAI_API_KEY` exists and has certain format — when running tests locally, either mock OpenAI calls or set a valid-looking key in `.env`.

Quick examples to copy
- Create a module-level OpenAI client with fallback:

  from openai import OpenAI
  from django.conf import settings

  client = OpenAI(api_key=getattr(settings, "OPENAI_API_KEY", None))

- Minimal safe call pattern:

  def ask_ai(messages, model=None):
      model = model or getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
      try:
          resp = client.chat.completions.create(model=model, messages=messages, temperature=0.2)
          return resp.choices[0].message.content.strip()
      except Exception as exc:
          return f"Nepodařilo se získat odpověď od AI: {type(exc).__name__}"

Where to look for examples
- Prompt patterns: `suropen/_build_ai_prompt`, `ingest/openai_parser.py:_call_openai`, `chatbot/views.py:system_prompt`
- DB write patterns: `suropen/_create_submission` (transaction.atomic)
- API endpoints and JSON handling: `chatbot/chat_api`, `suropen/form_api` (they accept JSON body and return JsonResponse)

Contribution guidance for AI agents
- Keep behavior consistent with existing endpoints: Czech language, concise outputs, quiet fallbacks on OpenAI errors.
- When adding new OpenAI usage, wire the API key via `settings.OPENAI_API_KEY` and use `getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")` for model selection.
- Prefer reusing helper wrappers and module-level `client` instances shown above.

If anything here seems incomplete or you want more examples (prompts, tests, or typical PRs), tell me which area to expand and I'll iterate.
