"""
Sets up structured JSON logging configuration for the application.
Logs are written to both console (colored) and a timestamped JSON file in the logs/ directory.

Usage:
    from config.logger import setup_logging
    setup_logging()

    import logging
    logger = logging.getLogger(__name__)
    logger.info("Message", extra={"key": "value"})
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pythonjsonlogger import jsonlogger

load_dotenv()

LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO").upper()
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)
LOG_FILENAME = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json"
LOG_FILEPATH = LOGS_DIR / LOG_FILENAME

_logging_configured = False

NOISY_LOGGERS = [
    "httpcore",
    "httpx",
    "hpack",
    "google_genai",
    "urllib3",
    "asyncio",
    "openai",
    "openai._base_client",
    "multipart",
    "python_multipart",
]

UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


class StructuredJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        log_record["timestamp"] = datetime.now(timezone.utc).isoformat()
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        if "message" not in log_record:
            log_record["message"] = record.getMessage()


class ColoredConsoleFormatter(logging.Formatter):
    RESET = "\033[0m"
    WHITE = "\033[37m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BOLD_RED = "\033[1;31m"

    LEVEL_COLORS = {
        logging.DEBUG: WHITE,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD_RED,
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelno, self.WHITE)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        base_msg = f"{record.levelname}: {timestamp} | {record.name} | {record.getMessage()}"

        standard_attrs = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "exc_info",
            "exc_text",
            "thread",
            "threadName",
            "taskName",
            "message",
        }

        extra_fields = {
            k: v for k, v in record.__dict__.items() if k not in standard_attrs and not k.startswith("_")
        }

        if extra_fields:
            extras_str = " | " + " ".join(f"{k}={v}" for k, v in extra_fields.items())
            base_msg += extras_str

        return f"{color}{base_msg}{self.RESET}"


def _resolve_log_level(level_name: str) -> int:
    return getattr(logging, level_name, logging.INFO)


def _configure_uvicorn_loggers() -> None:
    for logger_name in UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def setup_logging() -> None:
    global _logging_configured

    if _logging_configured:
        return

    log_level = _resolve_log_level(LOGGING_LEVEL)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColoredConsoleFormatter())
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

    file_handler = logging.FileHandler(LOG_FILEPATH, mode="a", encoding="utf-8")
    file_handler.setFormatter(StructuredJsonFormatter())
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    for noisy_logger in NOISY_LOGGERS:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    _configure_uvicorn_loggers()

    _logging_configured = True

    logger = logging.getLogger(__name__)
    logger.info(
        "Logging initialized",
        extra={
            "log_file": str(LOG_FILEPATH),
            "log_level": LOGGING_LEVEL,
        },
    )
