import json
import logging
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import config


LOGGER_NAME = "customer_service_agent"
logger = logging.getLogger(LOGGER_NAME)
_configured = False


def configure_observability() -> None:
    global _configured
    if _configured:
        return

    log_dir = Path(config.log_dir)
    if not log_dir.is_absolute():
        log_dir = config.BASE_DIR / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.setLevel(_log_level(config.log_level))
    logger.propagate = False
    _close_handlers()

    formatter = logging.Formatter("%(message)s")

    file_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if config.log_to_stdout:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    _configured = True


def reset_observability() -> None:
    global _configured
    _close_handlers()
    _configured = False


def log_event(event: str, level: str = "info", **fields: Any) -> None:
    if not _configured:
        configure_observability()

    payload = {
        "ts": int(time.time() * 1000),
        "event": event,
        **{
            key: _safe_value(value)
            for key, value in fields.items()
            if not _looks_secret(key)
        },
    }
    message = json.dumps(payload, ensure_ascii=False, default=str)
    getattr(logger, level.lower(), logger.info)(message)


@contextmanager
def timed_event(event: str, level: str = "info", **fields: Any) -> Iterator[None]:
    started = time.perf_counter()
    try:
        yield
    except Exception as exc:
        log_event(
            event,
            level="error",
            ok=False,
            duration_ms=_duration_ms(started),
            error_type=exc.__class__.__name__,
            error=str(exc),
            **fields,
        )
        raise
    else:
        log_event(
            event,
            level=level,
            ok=True,
            duration_ms=_duration_ms(started),
            **fields,
        )


def elapsed_ms(started: float) -> int:
    return _duration_ms(started)


def monotonic() -> float:
    return time.perf_counter()


def _duration_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _log_level(value: str) -> int:
    return getattr(logging, (value or "INFO").upper(), logging.INFO)


def _close_handlers() -> None:
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()


def _safe_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _safe_value(nested)
            for key, nested in value.items()
            if not _looks_secret(key)
        }
    if isinstance(value, list):
        return [_safe_value(item) for item in value[:20]]
    if isinstance(value, tuple):
        return [_safe_value(item) for item in value[:20]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _looks_secret(key: str) -> bool:
    lowered = key.lower()
    return any(token in lowered for token in ("key", "token", "secret", "authorization"))
