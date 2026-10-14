# dify-theater-box-office

*A theater box-office chatbot built in Dify with zero code, and fully traced in Opik by one platform setting.*

![Dify](https://img.shields.io/badge/Dify-1.17.1-1C64F2?style=flat)
![Model](https://img.shields.io/badge/model-gpt--4o--mini-412991?style=flat)
![Opik](https://img.shields.io/badge/Opik-native%20Dify%20tracing-2f54eb?style=flat)

The Marigold Lane Players are a fictional 140-seat community theater, and their box-office phone never stops: *Can my mother's wheelchair get in the side door? We booked online, can we still get a refund?* Someone on the volunteer team builds a chat assistant in Dify for it. There is no Python or TypeScript to put an Opik decorator on, so how do you see what the bot told a patron about refunds last Tuesday?

Dify has an answer built in: a tracing integration you switch on per app. This example turns it on **through Dify's console API**, so the whole thing is reproducible with one script.

## What you'll build

- A self-hosted Dify stack (release 1.17.1, vendored in `dify-docker/` so it stays pinned).
- A chat app imported from a DSL file. Its system prompt holds the 2026-27 season schedule, ticket prices, concessions, the accessible-seating policy and the refund/exchange rules. Anything else (group quotes, private hire, auditions) is redirected to the box-office staff.
- A configuration script that does what you would click through in the UI (create the admin, install the OpenAI plugin, store the key, import the app) and then the one step this example is about: write the Opik tracing config and turn tracing on.
- A demo that has one patron ask four questions in a single conversation.

```
patron ──► Dify service API ──► gpt-4o-mini ──► answer
                │
                └─► Opik (project: dify-theater-box-office): trace + llm span, one thread
```

## See it in Opik

Open the **dify-theater-box-office** project at `http://localhost:5173` after `./demo.sh`.

- **Traces tab:** five traces. Four are named `message`, one per patron question. The fifth, `generate_conversation_name`, is Dify's own housekeeping call that titles the chat; platform-level tracing catches calls you did not know your platform made. Open a `message` trace and you see one `llm` span with the full prompt Dify assembled (the whole season fact sheet plus the chat history) and the model's answer.
- **Token usage:** the prompt-token count climbs with each turn as history is attached: 885, 963, 1034, then 1095 prompt tokens for questions one to four (929 to 1148 total; exact counts vary slightly run to run). Mostly it is the fact sheet being re-sent every time, which is exactly what you want to see when deciding whether to shorten it.
- **Threads tab:** one thread, with ten messages (four questions and four answers, plus the title call's pair). Its id is the Dify conversation id; Dify forwards it as the Opik thread id, so no session handling is needed on your side.
- **Metadata:** each trace carries Dify's `conversation_id`, `message_id`, `app_id`, `end_user_id` (`demo-patron`) and the model name (`ls_model_name: gpt-4o-mini`), so you can jump from a bad answer back to the exact Dify message.
- **The policy tests, visible:** question two (a refund request five days before the show) should be answered "no refund, but a free exchange"; question four (a 30-person group quote) should be redirected to the staff phone and email. Read both outputs in the traces.

## Run it yourself

1. `cp .env.example .env` and set `OPENAI_API_KEY` (a repo-root `.env` is also read). Docker must be running, and a local Opik must be reachable at `http://localhost:5173` (swap in your own endpoint with the variables in the Poke-around list below).
2. `./setup.sh` starts the Dify stack on `http://localhost:8090` and then runs `configure_dify.py`. The first run pulls about ten images, so allow a few minutes.
3. `./demo.sh` asks the four questions.
4. Open the `dify-theater-box-office` project in Opik.

`configure_dify.py` is standard-library Python (3.9+), so there is nothing to install. You can run it alone against an already running Dify with `DIFY_URL=http://localhost:8090 python3 configure_dify.py`.

Teardown: `docker compose -f dify-docker/docker-compose.yaml --project-directory dify-docker down` (add `-v` to wipe Dify's databases). The Dify login is `admin@marigoldlane.example` / `MarigoldBoxOffice2026`; override it with `DIFY_ADMIN_EMAIL` and `DIFY_ADMIN_PASSWORD` if the machine is shared.

## Poke around

- Open `http://localhost:8090`, edit the refund rules in the app's prompt, ask the refund question again in the preview and compare the new trace with the old one in Opik.
- Change `gpt-4o-mini` to another model in `app/box-office-assistant.yml`, delete the app in Dify and re-run `configure_dify.py`, then compare prompt tokens and latency per answer.
- Point tracing at Comet Cloud: `OPIK_API_KEY=... OPIK_WORKSPACE=your-workspace OPIK_URL_FOR_DIFY=https://www.comet.com/opik/api/ python3 configure_dify.py`.
- Ask in the Dify preview "can I bring my own wine?" and read the trace to see whether the model stayed inside the fact sheet.

## Gotchas we hit

**Dify can't reach Opik at `localhost:5173`.** Dify sends traces from inside its containers, where `localhost` is the container itself. Use `http://host.docker.internal:5173/api/` as the Opik URL in the tracing config (this is the default in `configure_dify.py`). Your browser still uses `localhost:5173`.

**Local Opik has no key, but Dify's form seems to ask for one.** An empty `api_key` is accepted by Dify 1.17.1's Opik config endpoint and by a local Opik, so the config is `{"api_key": "", "project": "dify-theater-box-office", "workspace": "default", "url": "http://host.docker.internal:5173/api/"}`. Cloud users need a real key.

**Saving the config does nothing until you enable tracing.** `POST /console/api/apps/{id}/trace-config` stores the settings, but traces only flow after `POST /console/api/apps/{id}/trace` with `{"enabled": true, "tracing_provider": "opik"}`. A second `POST` to `trace-config` fails with `trace_config_already_exists`; use `PATCH` to update. The script does both.

**`total_estimated_cost` is null on the LLM spans.** The spans carry token usage, but their `model` and `provider` fields are empty (the model name is only in trace metadata as `ls_model_name`), so Opik cannot price them. Treat the integration as a source of prompts, answers, threads and token counts; compute cost from usage yourself if you need dollars.

## How it's put together

- `setup.sh`: writes `dify-docker/.env` (compose project name and port), runs `docker compose up -d`, then calls the configurator.
- `configure_dify.py`: the console-API configurator, idempotent; includes `ensure_opik_tracing`, the Opik part.
- `demo.sh`: four patron questions in one conversation through Dify's service API.
- `app/box-office-assistant.yml`: the app as Dify DSL, including the full fact sheet.
- `dify-docker/`: Dify 1.17.1's official compose files, vendored.
- `.env.example`, `.gitignore`: the one key needed; the ignore file keeps `dify-docker/.env` and Dify's volume data out of git.

No tests ship with this example: there is no application code, only configuration.

---

*built with Opik · inspired by Opik's examples and documentation*
