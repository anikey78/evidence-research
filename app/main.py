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
from app.research import research, verify_research
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
    description="A web research assistant with source citations and safety checks.",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.hostnames)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=settings.max_question_chars)


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
    if matches_blocked_phrase(question, settings):
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
            },
            status_code=200,
        )

    timeout = httpx.Timeout(settings.request_timeout_seconds)
    try:
        async with research_slots, httpx.AsyncClient(timeout=timeout) as client:
            input_check = await moderate(question, settings, client)
            if not input_check.allowed:
                return {
                    "answer": input_check.message,
                    "citations": [],
                    "citation_spans": [],
                    "grounded": False,
                    "verified": False,
                    "refused": True,
                }

            result = await research(question, settings, client)
            review = {"passed": False, "citations": []}
            if not result["refusal"]:
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
                    }
                review = await verify_research(question, result, settings, client)
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
    }
