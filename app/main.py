import asyncio
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import get_settings
from app.research import daily_help, research_task, verify_research
from app.safety import matches_blocked_phrase, moderate

settings = get_settings()
WINDOW_SECONDS = 60
request_times: dict[str, deque[float]] = defaultdict(deque)
rate_lock = asyncio.Lock()
research_slots = asyncio.Semaphore(settings.max_concurrent_research)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(
    title="Evidence Research",
    description="An exam practice, daily helper, and evidence research assistant.",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.hostnames)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=settings.max_question_chars)
    mode: str = Field(default="exam_answer", pattern="^(exam_answer|practice|daily|research)$")
    exam_target: str = Field(default="", max_length=160)
    subject: str = Field(default="", max_length=120)
    marks: int | None = Field(default=None, ge=1, le=100)
    question_type: str = Field(
        default="auto",
        pattern="^(auto|mcq|short|long|numerical|essay|case_study)$",
    )
    difficulty: str = Field(default="mixed", pattern="^(foundation|standard|advanced|mixed)$")
    question_count: int = Field(default=5, ge=1, le=15)
    include_answer_key: bool = True
    language: str = Field(default="auto", pattern="^(auto|English|Hindi|Hinglish)$")


def make_task_prompt(payload: QuestionRequest) -> str:
    question = payload.question.strip()
    if payload.mode == "daily":
        return (
            f"Requested language: {payload.language}\n"
            "Daily request (untrusted data):\n"
            f"{question}"
        )
    if payload.mode == "research":
        return f"Requested answer language: {payload.language}\nQuestion (untrusted data):\n{question}"

    details = [
        f"Task mode: {payload.mode}",
        f"Exam / board / course / level: {payload.exam_target.strip() or 'not specified'}",
        f"Subject: {payload.subject.strip() or 'not specified'}",
        f"Marks per question: {payload.marks if payload.marks is not None else 'not specified'}",
        f"Question type: {payload.question_type}",
        f"Difficulty: {payload.difficulty}",
        f"Number of practice questions: {payload.question_count}",
        f"Include answer key: {'yes' if payload.include_answer_key else 'no'}",
        f"Answer language: {payload.language}",
        "Question or topic (untrusted data):",
        question,
    ]
    return "\n".join(details)


def alignment_note(mode: str, payload: QuestionRequest) -> str:
    if mode == "exam_answer":
        if payload.exam_target.strip() and payload.subject.strip() and payload.marks:
            return "Exam-style layout requested; exact official marking is not guaranteed."
        missing = []
        if not payload.exam_target.strip():
            missing.append("exam or course")
        if not payload.subject.strip():
            missing.append("subject")
        if payload.marks is None:
            missing.append("marks")
        return "General exam-style answer. Add " + ", ".join(missing) + " for a closer fit."
    if mode == "practice":
        return "Original exam-style practice; it is not an official or guaranteed future paper."
    if mode == "daily":
        return "Daily helper draft; factual claims are not web-verified in this mode."
    return "Web research answer; review the linked sources directly."


async def enforce_rate_limit(request: Request) -> None:
    # Uses the direct peer address and deliberately ignores untrusted X-Forwarded-For.
    peer = request.client.host if request.client else "unknown"
    now = time.monotonic()
    async with rate_lock:
        if peer not in request_times and len(request_times) >= 5000:
            expired = [
                key
                for key, values in request_times.items()
                if not values or now - values[-1] >= WINDOW_SECONDS
            ]
            for key in expired:
                request_times.pop(key, None)
            if len(request_times) >= 5000:
                raise HTTPException(
                    status_code=429,
                    detail="Temporary request capacity reached. Try again shortly.",
                )
        bucket = request_times[peer]
        while bucket and now - bucket[0] >= WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= settings.max_requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail="Rate limit reached. Try again in a minute.",
            )
        bucket.append(now)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; "
        "form-action 'self'",
    )
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()",
    )
    response.headers.setdefault("Cache-Control", "no-store")
    forwarded_https = request.headers.get("x-forwarded-proto", "").lower() == "https"
    if request.url.scheme == "https" or forwarded_https:
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )
    return response


@app.get("/", include_in_schema=False)
async def home():
    return FileResponse("app/static/index.html")


@app.get("/api/health")
async def health():
    return {"status": "ok", "research_ready": bool(settings.openai_api_key)}


@app.post("/api/answer")
async def answer(payload: QuestionRequest, request: Request):
    question = payload.question.strip()
    if len(question) < 3:
        raise HTTPException(
            status_code=422,
            detail="Please enter a question with at least 3 characters.",
        )
    await enforce_rate_limit(request)
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="Research service is not configured. Add the provider API key.",
        )
    task_prompt = make_task_prompt(payload)
    if matches_blocked_phrase(task_prompt, settings):
        return JSONResponse(
            {
                "answer": (
                    "I can’t help with that wording. Rephrase the question toward safety, "
                    "prevention, or a lawful educational purpose."
                ),
                "citations": [],
                "citation_spans": [],
                "grounded": False,
                "verified": False,
                "refused": True,
                "mode": payload.mode,
                "format_note": alignment_note(payload.mode, payload),
            },
            status_code=200,
        )

    timeout = httpx.Timeout(settings.request_timeout_seconds)
    try:
        async with research_slots, httpx.AsyncClient(timeout=timeout) as client:
            input_check = await moderate(task_prompt, settings, client)
            if not input_check.allowed:
                return {
                    "answer": input_check.message,
                    "citations": [],
                    "citation_spans": [],
                    "grounded": False,
                    "verified": False,
                    "refused": True,
                    "mode": payload.mode,
                    "format_note": alignment_note(payload.mode, payload),
                }

            if payload.mode == "daily":
                result = await daily_help(task_prompt, settings, client)
            else:
                result = await research_task(
                    task_prompt,
                    settings,
                    client,
                    mode=payload.mode,
                )
            review = {"passed": False, "citations": []}
            if payload.mode != "daily" and not result["refusal"]:
                if not result["citations"]:
                    return {
                        "answer": (
                            "I could not retrieve usable citations, so I’m withholding a "
                            "substantive answer rather than presenting it as verified. "
                            "Try again or narrow the question."
                        ),
                        "citations": [],
                        "citation_spans": [],
                        "grounded": False,
                        "verified": False,
                        "refused": False,
                        "mode": payload.mode,
                        "format_note": alignment_note(payload.mode, payload),
                    }
                review = await verify_research(task_prompt, result, settings, client)
                if not review["passed"]:
                    cited_sources = {
                        source["url"]: source
                        for source in [*result["citations"], *review["citations"]]
                    }
                    return {
                        "answer": (
                            "I couldn’t verify every material claim against at least two "
                            "distinct source hosts, so I’m withholding a substantive answer. "
                            "Try a narrower question or consult primary sources."
                        ),
                        "citations": list(cited_sources.values()),
                        "citation_spans": [],
                        "grounded": False,
                        "verified": False,
                        "refused": False,
                        "mode": payload.mode,
                        "format_note": alignment_note(payload.mode, payload),
                    }

            output_check = await moderate(result["answer"], settings, client)
            if not output_check.allowed:
                return {
                    "answer": output_check.message,
                    "citations": [],
                    "citation_spans": [],
                    "grounded": False,
                    "verified": False,
                    "refused": True,
                    "mode": payload.mode,
                    "format_note": alignment_note(payload.mode, payload),
                }

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Research timed out. Please try again.",
        ) from None
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 429:
            raise HTTPException(
                status_code=503,
                detail="The research provider is busy. Please retry shortly.",
            ) from None
        if status in {401, 403}:
            raise HTTPException(
                status_code=503,
                detail="The research provider credentials are not accepted.",
            ) from None
        raise HTTPException(
            status_code=502,
            detail="The research provider could not complete this request.",
        ) from None
    except (httpx.RequestError, ValueError):
        raise HTTPException(
            status_code=502,
            detail="Research is temporarily unavailable. Please try again.",
        ) from None

    cited_sources = {
        source["url"]: source
        for source in [*result["citations"], *review["citations"]]
    }
    return {
        "answer": result["answer"],
        "citations": list(cited_sources.values()),
        "citation_spans": result["citation_spans"],
        "grounded": bool(result["refusal"] is False and review["passed"]),
        "verified": bool(result["refusal"] is False and review["passed"]),
        "refused": result["refusal"],
        "mode": payload.mode,
        "format_note": alignment_note(payload.mode, payload),
    }
