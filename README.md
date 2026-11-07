# Evidence Research

A deployable study and research assistant. It gives exam-style answers, creates original exam-level practice with answer keys, helps with one-time daily drafts and plans, and researches factual questions with clickable citations and evidence checks.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/anikey78/evidence-research) [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/anikey78/evidence-research)

> Evidence is not a guarantee. No system can prove every answer correct for every possible question. Exam similarity is approximate; generated questions are not official or guaranteed future papers.

## What it can do

- **Answer an exam question:** enter the exam/board/course, class or level, subject, marks, and language for a closer answer format.
- **Create exam-style practice:** choose an exam, topic, question type, difficulty, number, and whether to include worked answers. It uses public syllabus or sample-paper guidance when available and generates original questions.
- **Daily helper:** create a one-time draft, checklist, explanation, calculation, or plan. It does not send messages or perform actions outside the app.
- **Research facts:** live web search, linked source citations, moderation, and a separate fresh-search review. It withholds substantive research answers that do not pass the evidence gate.

## Run it

### GitHub Codespaces

1. Add your own OPENAI_API_KEY as a [Codespaces secret](https://github.com/settings/codespaces) and grant it access to this repository.
2. Click **Open in GitHub Codespaces** above and create a codespace.
3. The app starts in the codespace; open the forwarded **Evidence Research** preview on port 8000. Codespaces ports are private by default.

### Deploy your own hosted copy

Click **Deploy to Render** above, sign in to your own Render account, and provide your own API key when asked. Each deployment creates a separate service in that account. The included free service is intended for demos; free instances can sleep when idle. Render and AI-provider usage may incur charges in your accounts.

A hosted instance has a public URL. This starter has no user accounts or shared spending controls, so anyone who can reach it can submit requests. Add authentication, usage budgets, and abuse monitoring before running a shared public service.

### Run locally

Requirements: Python 3.12+ and an OpenAI API key with access to the configured model and web search.

```bash
cp .env.example .env
# Add OPENAI_API_KEY to .env, then:
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000. For Docker, run docker compose up --build.

## Privacy

The app does not keep chat history, use analytics, or log request bodies. Requests are still sent to the configured AI provider for moderation and generation; Responses API calls set store: false, and exam/research modes use web search. Daily-helper answers are not web-verified. Hosting and provider data handling depends on the operator's account settings and current provider terms. Do not submit passwords, IDs, private student records, or confidential details. Read [PRIVACY.txt](PRIVACY.txt).

## Evidence, safety, and limits

- With exam, subject, and marks specified, the response follows that requested style as closely as public sources and the model allow. Exact official marking-scheme or future-paper matches cannot be guaranteed.
- Fresh-search review is a risk reduction step, not proof of correctness or a calibrated probability. Two citations can still repeat the same underlying report.
- The stated **99% precision goal has not been measured or achieved** for this repository. See [ACCURACY_EVALUATION.md](ACCURACY_EVALUATION.md).
- Moderation and phrase filters can miss harmful requests or block benign ones; they are not guarantees.
- For current factual answers, use research or exam mode, read the linked sources, and check official materials for high-stakes decisions.

## API

POST /api/answer accepts question, mode (exam_answer, practice, daily, or research), and optional exam settings (exam_target, subject, marks, question_type, difficulty, question_count, include_answer_key, language). It returns the answer, citations, verification status, mode, and a format note. GET /api/health reports readiness without revealing credentials.

## Configuration and security

Set OPENAI_API_KEY only through a server-side secret manager. OPENAI_MODEL defaults to gpt-6-astra; OPENAI_VERIFIER_MODEL can select a separate review model. Rate limiting is in-memory and intended for a single instance. The container runs as non-root with a read-only root filesystem and dropped capabilities.

GitHub secret scanning, push protection, private vulnerability reporting, Dependabot, CodeQL, and the protected main ruleset are enabled. Keep the default branch protected and review alerts and dependency updates.

## Legal and privacy files

- [PRIVACY.txt](PRIVACY.txt) explains request handling and provider/hosting limits.
- [LAW.txt](LAW.txt) lists India-focused legal topics and official sources for operator review.
- [TERMS_AND_CONDITIONS.txt](TERMS_AND_CONDITIONS.txt) is a draft. Complete its fields and obtain qualified Indian legal review before publishing it as final terms.
