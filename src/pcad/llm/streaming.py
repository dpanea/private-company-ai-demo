"""Extract user-visible text from a streaming structured-JSON answer.

The full raw stream is also retained so the final payload can be re-parsed and
its citations validated after streaming completes.
"""

from __future__ import annotations


_ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "\\": "\\",
    '"': '"',
    "/": "/",
    "b": "\b",
    "f": "\f",
}


class StructuredAnswerStreamer:
    EMIT_TEXT_STATUSES = {"answered", "insufficient_evidence"}
    EMIT_MESSAGE_STATUSES = {"needs_account_clarification"}
    SEPARATOR = "\n\n"

    def __init__(self) -> None:
        self._raw: list[str] = []
        self._in_string = False
        self._escape = False
        self._unicode_remain = 0
        self._unicode_buf = ""
        self._after_colon = False
        self._last_key: str | None = None
        self._string_role: str | None = None  # "key" | "status" | "emit" | "ignore"
        self._key_buf: list[str] = []
        self._status_buf: list[str] = []
        self._status: str | None = None
        self._emit_count = 0

    @property
    def raw(self) -> str:
        return "".join(self._raw)

    @property
    def status(self) -> str | None:
        return self._status

    def feed(self, chunk: str) -> str:
        self._raw.append(chunk)
        out: list[str] = []
        for ch in chunk:
            if self._in_string:
                self._handle_in_string(ch, out)
            else:
                self._handle_outside_string(ch, out)
        return "".join(out)

    def _handle_outside_string(self, ch: str, out: list[str]) -> None:
        if ch == '"':
            self._begin_string(out)
            return
        if ch == ":":
            self._after_colon = True
            return
        if ch in ",{}[]":
            self._after_colon = False
            self._last_key = None

    def _begin_string(self, out: list[str]) -> None:
        self._in_string = True
        if not self._after_colon:
            self._string_role = "key"
            self._key_buf = []
            return
        key = self._last_key
        if key == "status":
            self._string_role = "status"
            self._status_buf = []
            return
        if key == "text" and self._status in self.EMIT_TEXT_STATUSES:
            self._string_role = "emit"
            if self._emit_count > 0:
                out.append(self.SEPARATOR)
            return
        if key == "message" and self._status in self.EMIT_MESSAGE_STATUSES:
            self._string_role = "emit"
            if self._emit_count > 0:
                out.append(self.SEPARATOR)
            return
        self._string_role = "ignore"

    def _handle_in_string(self, ch: str, out: list[str]) -> None:
        if self._unicode_remain > 0:
            self._unicode_buf += ch
            self._unicode_remain -= 1
            if self._unicode_remain == 0:
                try:
                    decoded = chr(int(self._unicode_buf, 16))
                except ValueError:
                    decoded = ""
                self._unicode_buf = ""
                self._absorb(decoded, out)
            return
        if self._escape:
            self._escape = False
            if ch == "u":
                self._unicode_remain = 4
                self._unicode_buf = ""
                return
            self._absorb(_ESCAPES.get(ch, ch), out)
            return
        if ch == "\\":
            self._escape = True
            return
        if ch == '"':
            self._end_string()
            return
        self._absorb(ch, out)

    def _absorb(self, ch: str, out: list[str]) -> None:
        if self._string_role == "key":
            self._key_buf.append(ch)
        elif self._string_role == "status":
            self._status_buf.append(ch)
        elif self._string_role == "emit":
            out.append(ch)

    def _end_string(self) -> None:
        self._in_string = False
        role = self._string_role
        self._string_role = None
        if role == "key":
            self._last_key = "".join(self._key_buf)
            return
        if role == "status":
            self._status = "".join(self._status_buf)
        elif role == "emit":
            self._emit_count += 1
        self._after_colon = False
        self._last_key = None
