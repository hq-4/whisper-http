from __future__ import annotations

import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Iterable

from pythonjsonlogger import jsonlogger
from rich.console import Console
from rich.logging import RichHandler

from src.framework.config import Settings

JSON_FIELDS: Iterable[str] = (
    "ts",
    "level",
    "name",
    "subsys",
    "guild_id",
    "user_id",
    "msg_id",
    "event",
    "detail",
    "message",
)


class StructuredJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record.setdefault("message", record.getMessage())
        log_record.setdefault("level", record.levelname)
        log_record.setdefault("name", record.name)
        log_record.setdefault("ts", self.format_timestamp(record.created))
        for field in JSON_FIELDS:
            log_record.setdefault(field, None)

    @staticmethod
    def format_timestamp(created: float) -> str:
        local_dt = datetime.fromtimestamp(created).astimezone()
        return local_dt.isoformat(timespec="milliseconds")


def configure_logging(settings: Settings) -> None:
    console = Console(width=120)
    pretty_handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        show_path=False,
        markup=True,
    )
    pretty_handler.set_name("pretty_handler")

    json_handler = RotatingFileHandler(
        settings.logs_file_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    json_handler.set_name("jsonl_handler")
    json_handler.setFormatter(StructuredJsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.log_level)
    root.addHandler(pretty_handler)
    root.addHandler(json_handler)

    _enforce_handler_configuration(root)


def _enforce_handler_configuration(logger: logging.Logger) -> None:
    handler_names = {handler.get_name(): handler for handler in logger.handlers}
    expected_names = {"pretty_handler", "jsonl_handler"}
    if set(handler_names) != expected_names or len(logger.handlers) != 2:
        raise RuntimeError(
            "Logging misconfiguration detected. Expected exactly 'pretty_handler' and 'jsonl_handler'."
        )
