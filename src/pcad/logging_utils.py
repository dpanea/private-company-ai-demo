from __future__ import annotations

import logging
import os
import sys


RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
COLORS = {
    "DEBUG": "\033[36m",
    "INFO": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[35m",
    "CLI": "\033[36m",
    "AGENT": "\033[35m",
    "API": "\033[94m",
    "INGESTION": "\033[95m",
    "LLM": "\033[92m",
    "RETRIEVAL": "\033[34m",
    "POSTGRES": "\033[33m",
    "CONFIG": "\033[90m",
    "APP": "\033[37m",
}


class ComponentFormatter(logging.Formatter):
    def __init__(self, *, use_color: bool) -> None:
        super().__init__(datefmt="%Y-%m-%dT%H:%M:%S%z")
        self.use_color = use_color
        self._last_component: str | None = None

    def format(self, record: logging.LogRecord) -> str:
        component = _component_for_logger(record.name)
        timestamp = self.formatTime(record, self.datefmt)
        level = _pad(record.levelname, 7)
        name = _short_logger_name(record.name)
        message = record.getMessage()
        separator = ""
        if component != self._last_component:
            separator = self._separator(component)
            self._last_component = component
        if self.use_color:
            level = f"{COLORS.get(record.levelname, '')}{level}{RESET}"
            badge = f"{COLORS.get(component, '')}{BOLD}{_pad(component, 10)}{RESET}"
            timestamp = f"{DIM}{timestamp}{RESET}"
            name = f"{DIM}{name}{RESET}"
        else:
            badge = _pad(component, 10)
        line = f"{timestamp} {level} {badge} {name} {message}"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return separator + line

    def _separator(self, component: str) -> str:
        label = f" {component} "
        line = f"\n{label.center(88, '-')}\n"
        if not self.use_color:
            return line
        return f"\n{COLORS.get(component, '')}{BOLD}{label.center(88, '-')}{RESET}\n"


def configure_logging(level: str = "INFO", color: bool | str | None = None) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    use_color = _resolve_color(color)
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        root.addHandler(handler)
    root.setLevel(numeric_level)
    for handler in root.handlers:
        handler.setLevel(numeric_level)
        if isinstance(handler, logging.StreamHandler):
            if isinstance(handler.formatter, ComponentFormatter):
                handler.formatter.use_color = use_color
            else:
                handler.setFormatter(ComponentFormatter(use_color=use_color))


def _resolve_color(color: bool | str | None) -> bool:
    if isinstance(color, bool):
        return color
    raw = color if color is not None else os.environ.get("LOG_COLOR", "auto")
    mode = str(raw).lower()
    if mode in {"1", "true", "yes", "always"}:
        return True
    if mode in {"0", "false", "no", "never"}:
        return False
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stderr.isatty()


def _component_for_logger(name: str) -> str:
    if not name.startswith("pcad"):
        return "APP"
    parts = name.split(".")
    module = parts[1] if len(parts) > 1 else "app"
    return {
        "agent": "AGENT",
        "api": "API",
        "cli": "CLI",
        "config": "CONFIG",
        "db": "POSTGRES",
        "ingestion": "INGESTION",
        "llm": "LLM",
        "migrations": "POSTGRES",
        "retrieval": "RETRIEVAL",
    }.get(module, "APP")


def _short_logger_name(name: str) -> str:
    return name.removeprefix("pcad.")


def _pad(value: str, width: int) -> str:
    return value[:width].ljust(width)
