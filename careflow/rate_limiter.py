# ============================================================================
# CareFlow Rate Limiter — 429 RESOURCE_EXHAUSTED 방어
# Defense against Vertex AI 429 RESOURCE_EXHAUSTED errors.
#
# 문제 / Problem:
#   Vertex AI gemini-2.5-flash has a low default RPM quota (~10 RPM for new
#   projects). A single SYMPTOM scenario triggers 15-20+ Gemini calls across
#   the agent chain (root → scope_judge → triage → caregiver), easily
#   exceeding the limit within seconds.
#
# 해결 / Solution:
#   1. Token-bucket rate limiter — spaces out requests to stay under RPM.
#   2. Exponential backoff retry — catches 429s and retries with jitter.
#   3. Monkey-patches google.genai.Client to wrap all generate_content calls.
#
# 사용법 / Usage:
#   import careflow.rate_limiter  # 임포트만 하면 자동 적용
#   # Just importing this module auto-patches the genai Client.
# ============================================================================

from __future__ import annotations

import asyncio
import logging
import os
import random
import time
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration via environment variables
# ---------------------------------------------------------------------------
# Conservative default: 8 RPM leaves headroom below a 10 RPM quota.
# Increase once your quota is raised (e.g., 60 after requesting increase).
MAX_RPM: int = int(os.getenv("CAREFLOW_MAX_RPM", "8"))
MAX_RETRIES: int = int(os.getenv("CAREFLOW_MAX_RETRIES", "5"))
RETRY_BASE_DELAY: float = float(os.getenv("CAREFLOW_RETRY_BASE_DELAY", "2.0"))


# ---------------------------------------------------------------------------
# Token-bucket rate limiter (async-safe)
# ---------------------------------------------------------------------------
class _TokenBucket:
    """Simple token-bucket limiter scoped to RPM.

    Tokens refill at a rate of MAX_RPM per 60 seconds. Each request consumes
    one token. If the bucket is empty, callers await until a token is available.
    """

    def __init__(self, rpm: int) -> None:
        self.rpm = max(rpm, 1)
        self.tokens: float = float(self.rpm)
        self.last_refill: float = time.monotonic()
        self._lock = asyncio.Lock()
        # Also keep a sync lock for sync callers
        self._sync_tokens: float = float(self.rpm)
        self._sync_last_refill: float = time.monotonic()

    async def acquire(self) -> None:
        """Wait until a token is available, then consume one."""
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.tokens = min(
                    float(self.rpm),
                    self.tokens + elapsed * (self.rpm / 60.0),
                )
                self.last_refill = now
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
            # No token available — wait a bit before retrying
            wait = 60.0 / self.rpm
            logger.debug("rate_limiter.wait rpm=%d wait=%.2fs", self.rpm, wait)
            await asyncio.sleep(wait)

    def acquire_sync(self) -> None:
        """Blocking acquire for synchronous callers."""
        while True:
            now = time.monotonic()
            elapsed = now - self._sync_last_refill
            self._sync_tokens = min(
                float(self.rpm),
                self._sync_tokens + elapsed * (self.rpm / 60.0),
            )
            self._sync_last_refill = now
            if self._sync_tokens >= 1.0:
                self._sync_tokens -= 1.0
                return
            wait = 60.0 / self.rpm
            logger.debug("rate_limiter.sync_wait rpm=%d wait=%.2fs", self.rpm, wait)
            time.sleep(wait)


_bucket = _TokenBucket(MAX_RPM)


# ---------------------------------------------------------------------------
# 429 detection helper
# ---------------------------------------------------------------------------
def _is_resource_exhausted(exc: Exception) -> bool:
    """Check if an exception is a 429 / RESOURCE_EXHAUSTED error."""
    exc_str = str(exc).lower()
    if "429" in exc_str or "resource_exhausted" in exc_str or "resource exhausted" in exc_str:
        return True
    # google-genai wraps gRPC status codes
    if hasattr(exc, "code") and getattr(exc, "code", None) == 429:
        return True
    return False


# ---------------------------------------------------------------------------
# Retry wrappers
# ---------------------------------------------------------------------------
def _retry_async(fn):
    """Wrap an async generate_content call with rate limiting + retry."""

    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            await _bucket.acquire()
            try:
                return await fn(*args, **kwargs)
            except Exception as exc:
                if _is_resource_exhausted(exc):
                    last_exc = exc
                    delay = RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(
                        "rate_limiter.429_retry attempt=%d/%d delay=%.1fs error=%s",
                        attempt + 1,
                        MAX_RETRIES + 1,
                        delay,
                        str(exc)[:120],
                    )
                    await asyncio.sleep(delay)
                else:
                    raise
        # All retries exhausted
        logger.error("rate_limiter.429_exhausted after %d retries", MAX_RETRIES + 1)
        raise last_exc  # type: ignore[misc]

    return wrapper


def _retry_sync(fn):
    """Wrap a sync generate_content call with rate limiting + retry."""

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            _bucket.acquire_sync()
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                if _is_resource_exhausted(exc):
                    last_exc = exc
                    delay = RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(
                        "rate_limiter.429_retry_sync attempt=%d/%d delay=%.1fs",
                        attempt + 1,
                        MAX_RETRIES + 1,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    raise
        logger.error("rate_limiter.429_exhausted_sync after %d retries", MAX_RETRIES + 1)
        raise last_exc  # type: ignore[misc]

    return wrapper


# ---------------------------------------------------------------------------
# Monkey-patch google.genai.Client
# ---------------------------------------------------------------------------
_patched = False


def patch_genai_client() -> None:
    """Patch google.genai model classes to add rate limiting + retry.

    This patches the low-level methods that ADK and scope_judge both use,
    so ALL Gemini calls go through the rate limiter automatically.
    """
    global _patched
    if _patched:
        return
    _patched = True

    try:
        from google.genai import models as genai_models

        # Patch the async generate_content on AsyncModels
        if hasattr(genai_models, "AsyncModels"):
            cls = genai_models.AsyncModels
            if hasattr(cls, "generate_content"):
                original = cls.generate_content
                if not getattr(original, "_careflow_patched", False):
                    wrapped = _retry_async(original)
                    wrapped._careflow_patched = True  # type: ignore[attr-defined]
                    cls.generate_content = wrapped  # type: ignore[assignment]
                    logger.info("rate_limiter.patched AsyncModels.generate_content")

        # Patch the sync generate_content on Models
        if hasattr(genai_models, "Models"):
            cls = genai_models.Models
            if hasattr(cls, "generate_content"):
                original = cls.generate_content
                if not getattr(original, "_careflow_patched", False):
                    wrapped = _retry_sync(original)
                    wrapped._careflow_patched = True  # type: ignore[attr-defined]
                    cls.generate_content = wrapped  # type: ignore[assignment]
                    logger.info("rate_limiter.patched Models.generate_content")

        logger.info(
            "rate_limiter.active max_rpm=%d max_retries=%d base_delay=%.1fs",
            MAX_RPM,
            MAX_RETRIES,
            RETRY_BASE_DELAY,
        )
    except ImportError:
        logger.warning("rate_limiter.skip google.genai not installed")
    except Exception as exc:
        logger.warning("rate_limiter.patch_error %s", exc)


# Auto-patch on import
patch_genai_client()
