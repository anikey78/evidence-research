# Evidence Research

A deployable research-assistant web app that searches the live web, returns clickable source citations, states uncertainty, and applies safety checks to both questions and generated answers.

> **Evidence is not a guarantee.** No system can prove every answer correct for every possible question. This app requires web search, asks for citations on factual claims, checks citations returned by the provider, and declines to present an uncited answer as verified.

## Features

- Required web search for each research request.
- Clickable citations from the Responses API's URL citation annotations.
- Primary-source preference, source comparison, explicit uncertainty, and no invented citations in the research instructions.
- Input and output moderation with `omni-moderation-latest`; moderation errors fail closed.
- Safe refusal guidance for requests that would enable harm.
- Optional configurable blocked phrases as a supplemental filter.
- Input size limits, request rate limiting, bounded concurrency, timeouts, no conversation storage, and no question-body logging.
- Security headers, host validation, non-root container, read-only container filesystem, and minimal Docker capabilities.
- Unit checks plus GitHub Actions lint, static security scan, dependency audit, and container build; Dependabot updates.

## Quick start

Requirements: Python 3.12+ and an OpenAI API key with access to the configured model and web search.

1. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.
2. Start the app:

   ```bash
   python -m venv .venv
   # macOS/Linux
   source .venv/bin/activate
   # Windows PowerShell: .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

3. Open [http://localhost:8000](http://localhost:8000).

The key stays on the server. Never place it in browser code, commit it, or share it in screenshots. The app sends the question to the configured provider for moderation and research; `store: false` is set on Responses API calls. Review the provider's current data controls and terms before sending sensitive information.

## Run with Docker

```bash
cp .env.example .env
# Add OPENAI_API_KEY to .env, then:
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000). The container runs as a non-root user, drops Linux capabilities, uses a read-only root filesystem, and writes only to a temporary filesystem.

## Deploy online

The repository includes `render.yaml` for a Render Docker web service on its free plan. Free services can sleep when idle and are intended for testing or hobby projects; choose an appropriate paid compute plan if you need production availability. You can also deploy the Dockerfile on another container host.

1. Push this directory to a GitHub repository.
2. Create a web service from the repository using the included Render blueprint, or select Docker as the runtime on your host.
3. Add `OPENAI_API_KEY` through the host's secret settings. Do not put a live key in GitHub Actions, source files, or the Render blueprint.
4. Set `ALLOWED_HOSTS` to the exact public hostname, such as `your-service.onrender.com`.
5. Confirm the HTTPS URL and `/api/health` endpoint. `research_ready` should be `true` once the secret is configured.
6. GitHub secret scanning, push protection, private vulnerability reporting, Dependabot, and CodeQL are enabled; check the GitHub Security tab for new findings.

This repository does not publish itself or create a hosting account. Hosting, model, and search usage may incur charges under your provider account.

## Configuration

| Variable | Default | Purpose |
|---|---:|---|
| `OPENAI_API_KEY` | empty | Server-side API credential; required for answers |
| `OPENAI_MODEL` | `gpt-6-astra` | Model available to your account |
| `MAX_QUESTION_CHARS` | `4000` | Maximum user question size |
| `MAX_OUTPUT_TOKENS` | `1400` | Response cap |
| `REQUEST_TIMEOUT_SECONDS` | `90` | Provider timeout |
| `MAX_REQUESTS_PER_MINUTE` | `30` | Per-process, per-peer request cap |
| `MAX_CONCURRENT_RESEARCH` | `4` | Maximum simultaneous provider workflows |
| `BLOCKED_PHRASES` | built-in examples | Additional comma-separated literal phrases to reject |
| `ALLOWED_HOSTS` | `*` | Comma-separated allowed HTTP Host names; set explicitly in production |

The in-memory rate limit is intended for a single app process/instance. For multi-replica or high-traffic deployments, use a shared Redis-backed rate limiter and review edge proxy IP handling. Do not trust arbitrary `X-Forwarded-For` values.

## Safety and evidence limits

- Moderation is a layer, not a guarantee. It may miss harmful requests or flag legitimate discussion; configure the app and review the provider's current moderation behavior for your use case.
- The built-in and configurable phrase filters supplement moderation only. Literal phrase filters are easy to evade and can block benign questions; they are not the safety system.
- A citation proves that a source was cited, not that the source is accurate, current, or that it supports every sentence. Read important sources directly.
- Search can be unavailable or return weak/conflicting results. When no citation annotation is available, the app says it cannot verify the answer.
- This starter has no user accounts, billing controls, durable logs, or enterprise abuse operations. Add those before a broad public launch.

## API

`POST /api/answer`

```json
{"question":"What does the latest evidence say about ...?"}
```

Returns `answer`, `citations`, `grounded`, and `refused`. `GET /api/health` returns service status without revealing credentials. API documentation routes are disabled in production.

## GitHub security checklist

- GitHub Secret Scanning currently reports no unresolved alerts. A pattern-based scan of 53 reachable commits across 18 refs and 44 unique blobs found no matches for configured credential patterns, including common provider/GitHub/AWS tokens, private-key headers, bearer tokens, and generic credential assignments. This bounded scan is not proof that history contains no secrets; keep alerts enabled and investigate any future finding.
- Add the real API key only to the deployment host's secret manager.
- Enabled: dependency graph, Dependabot alerts, malware alerts and security updates, secret scanning, push protection, private vulnerability reporting, CodeQL default setup, and GitHub AI application scanning.
- The active Protect main ruleset requires pull requests and current quality and container checks; CodeQL and AI application scanning are enabled but are not required merge checks.
- Keep the default branch protected and review dependency/base-image updates.

## Legal text files

- [`LAW.txt`](LAW.txt) lists India-focused legal topics and official sources for
  the operator to review.
- [`TERMS_AND_CONDITIONS.txt`](TERMS_AND_CONDITIONS.txt) is a project-specific
  draft. Complete its bracketed operator, contact, date, and court-location
  fields and obtain qualified Indian legal review before using it as public
  terms. It is not a privacy notice or a compliance certification.


## Accuracy target and evidence review

The project sets a **99% precision target among substantive answers** on a curated, human-reviewed benchmark. This target has not been measured or achieved for this repository, and it is not a guarantee for every possible question. Report coverage and abstentions with precision. See [ACCURACY_EVALUATION.md](ACCURACY_EVALUATION.md) for the evaluation protocol.

At runtime, the app performs a second fresh-search review and withholds substantive answers unless every material claim is judged supported, no issue is reported, and the review supplies matching citation annotations from at least two distinct source hosts. The app labels this gate as a review pass, not proof of correctness or statistical 99% accuracy. Different hosts may repeat the same underlying report, and the default verifier uses the same model, so correlated errors remain possible. The extra search increases response time and API use.

Set OPENAI_VERIFIER_MODEL to a different supported model to add some model diversity. Leave it empty to use OPENAI_MODEL for both passes. If the review is uncertain, returns issues, lacks the required citations, or fails, the service abstains.

POST /api/answer now also returns citation_spans and verified. The verified field means only that the review gate passed; it is not a correctness guarantee.
