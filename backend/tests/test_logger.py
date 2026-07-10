import logging

import config.logger as logger_module
from config.logger import (
    ColoredConsoleFormatter,
    StructuredJsonFormatter,
    _configure_uvicorn_loggers,
    _resolve_log_level,
    setup_logging,
)


def test_resolve_log_level_uses_valid_level():
    assert _resolve_log_level("DEBUG") == logging.DEBUG
    assert _resolve_log_level("WARNING") == logging.WARNING


def test_resolve_log_level_falls_back_to_info():
    assert _resolve_log_level("NOT_A_LEVEL") == logging.INFO


def test_setup_logging_is_idempotent(reset_logging):
    setup_logging()
    handler_count = len(logging.getLogger().handlers)

    setup_logging()

    assert logger_module._logging_configured is True
    assert len(logging.getLogger().handlers) == handler_count


def test_setup_logging_writes_to_configured_file(reset_logging):
    setup_logging()

    logging.getLogger("tests.logger").info("structured test message")

    log_contents = logger_module.LOG_FILEPATH.read_text(encoding="utf-8")
    assert "structured test message" in log_contents
    assert '"level": "INFO"' in log_contents or '"level":"INFO"' in log_contents


def test_structured_json_formatter_adds_expected_fields():
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="tests.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)

    assert '"message": "hello"' in formatted or '"message":"hello"' in formatted
    assert '"logger": "tests.logger"' in formatted or '"logger":"tests.logger"' in formatted
    assert '"level": "INFO"' in formatted or '"level":"INFO"' in formatted
    assert "timestamp" in formatted


def test_colored_console_formatter_includes_message_and_extras():
    formatter = ColoredConsoleFormatter()
    record = logging.LogRecord(
        name="tests.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.custom_field = "value"

    formatted = formatter.format(record)

    assert "INFO:" in formatted
    assert "tests.logger" in formatted
    assert "hello" in formatted
    assert "custom_field=value" in formatted


def test_configure_uvicorn_loggers_propagate_to_root():
    _configure_uvicorn_loggers()

    for logger_name in logger_module.UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(logger_name)
        assert uvicorn_logger.propagate is True
        assert uvicorn_logger.handlers == []

    assert logging.getLogger("uvicorn.access").level == logging.WARNING
