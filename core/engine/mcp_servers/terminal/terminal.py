from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable


@dataclass
class _Buffer:
    cols: int
    rows: int
    screen: list[list[str]]
    cursor_x: int = 0
    cursor_y: int = 0
    saved_cursor: tuple[int, int] = (0, 0)
    scrollback: deque[str] | None = None

    @classmethod
    def create(cls, cols: int, rows: int, with_scrollback: bool) -> "_Buffer":
        return cls(
            cols=cols,
            rows=rows,
            screen=[[" "] * cols for _ in range(rows)],
            scrollback=deque(maxlen=5000) if with_scrollback else None,
        )

    def clear(self) -> None:
        self.screen = [[" "] * self.cols for _ in range(self.rows)]
        self.cursor_x = 0
        self.cursor_y = 0

    def resize(self, cols: int, rows: int) -> None:
        new_screen = [[" "] * cols for _ in range(rows)]
        copy_rows = min(rows, self.rows)
        copy_cols = min(cols, self.cols)
        for r in range(copy_rows):
            for c in range(copy_cols):
                new_screen[r][c] = self.screen[r][c]
        self.cols = cols
        self.rows = rows
        self.screen = new_screen
        self.cursor_x = min(self.cursor_x, max(0, cols - 1))
        self.cursor_y = min(self.cursor_y, max(0, rows - 1))

    def _scroll(self) -> None:
        if self.scrollback is not None:
            self.scrollback.append("".join(self.screen[0]).rstrip())
        self.screen.pop(0)
        self.screen.append([" "] * self.cols)
        self.cursor_y = self.rows - 1

    def line_feed(self) -> None:
        if self.cursor_y >= self.rows - 1:
            self._scroll()
        else:
            self.cursor_y += 1

    def put_char(self, ch: str) -> None:
        if self.cursor_y < 0 or self.cursor_y >= self.rows:
            return
        if self.cursor_x < 0:
            self.cursor_x = 0
        if self.cursor_x >= self.cols:
            self.cursor_x = 0
            self.line_feed()
        self.screen[self.cursor_y][self.cursor_x] = ch
        self.cursor_x += 1
        if self.cursor_x >= self.cols:
            self.cursor_x = 0
            self.line_feed()

    def get_lines(self, include_scrollback: bool) -> list[str]:
        lines = []
        if include_scrollback and self.scrollback is not None:
            lines.extend(self.scrollback)
        lines.extend("".join(line).rstrip() for line in self.screen)
        return lines


class TerminalState:
    def __init__(self, cols: int, rows: int, writer: Callable[[str], None]) -> None:
        self.cols = cols
        self.rows = rows
        self._writer = writer
        self._normal = _Buffer.create(cols, rows, with_scrollback=True)
        self._alternate = _Buffer.create(cols, rows, with_scrollback=False)
        self.active_buffer = "normal"
        self._mode = "normal"
        self._csi_data = ""

    @property
    def _buf(self) -> _Buffer:
        return self._alternate if self.active_buffer == "alternate" else self._normal

    def resize(self, cols: int, rows: int) -> None:
        self.cols = cols
        self.rows = rows
        self._normal.resize(cols, rows)
        self._alternate.resize(cols, rows)

    def feed(self, text: str) -> None:
        for ch in text:
            self._feed_char(ch)

    def _feed_char(self, ch: str) -> None:
        if self._mode == "normal":
            self._normal_char(ch)
            return
        if self._mode == "esc":
            if ch == "[":
                self._mode = "csi"
                self._csi_data = ""
                return
            self._mode = "normal"
            return
        if self._mode == "csi":
            if "\x40" <= ch <= "\x7e":
                self._handle_csi(self._csi_data, ch)
                self._mode = "normal"
                self._csi_data = ""
            else:
                self._csi_data += ch

    def _normal_char(self, ch: str) -> None:
        b = self._buf
        if ch == "\x1b":
            self._mode = "esc"
            return
        if ch == "\r":
            b.cursor_x = 0
            return
        if ch == "\n":
            b.line_feed()
            return
        if ch == "\b":
            b.cursor_x = max(0, b.cursor_x - 1)
            return
        if ch == "\t":
            target = ((b.cursor_x // 8) + 1) * 8
            b.cursor_x = min(target, b.cols - 1)
            return
        if ord(ch) >= 0x20 and ch != "\x7f":
            b.put_char(ch)

    def _parse_params(self, raw: str) -> tuple[bool, list[int]]:
        private = raw.startswith("?")
        body = raw[1:] if private else raw
        if not body:
            return private, []
        return private, [int(x) if x else 0 for x in body.split(";")]

    def _handle_csi(self, raw: str, final: str) -> None:
        b = self._buf
        private, params = self._parse_params(raw)
        p1 = params[0] if params else 0

        if final == "A":
            b.cursor_y = max(0, b.cursor_y - max(1, p1))
        elif final == "B":
            b.cursor_y = min(b.rows - 1, b.cursor_y + max(1, p1))
        elif final == "C":
            b.cursor_x = min(b.cols - 1, b.cursor_x + max(1, p1))
        elif final == "D":
            b.cursor_x = max(0, b.cursor_x - max(1, p1))
        elif final in ("H", "f"):
            row = (params[0] if len(params) > 0 and params[0] else 1) - 1
            col = (params[1] if len(params) > 1 and params[1] else 1) - 1
            b.cursor_y = min(max(0, row), b.rows - 1)
            b.cursor_x = min(max(0, col), b.cols - 1)
        elif final == "G":
            col = (p1 if p1 else 1) - 1
            b.cursor_x = min(max(0, col), b.cols - 1)
        elif final == "d":
            row = (p1 if p1 else 1) - 1
            b.cursor_y = min(max(0, row), b.rows - 1)
        elif final == "J":
            mode = p1
            if mode in (0, 2, 3):
                b.clear()
        elif final == "K":
            mode = p1
            if mode == 0:
                for i in range(b.cursor_x, b.cols):
                    b.screen[b.cursor_y][i] = " "
            elif mode == 1:
                for i in range(0, b.cursor_x + 1):
                    b.screen[b.cursor_y][i] = " "
            elif mode == 2:
                for i in range(0, b.cols):
                    b.screen[b.cursor_y][i] = " "
        elif final == "P":
            count = max(1, p1)
            row = b.screen[b.cursor_y]
            del row[b.cursor_x : b.cursor_x + count]
            row.extend([" "] * count)
        elif final == "@":
            count = max(1, p1)
            row = b.screen[b.cursor_y]
            for _ in range(count):
                row.insert(b.cursor_x, " ")
                row.pop()
        elif final == "s":
            b.saved_cursor = (b.cursor_x, b.cursor_y)
        elif final == "u":
            b.cursor_x, b.cursor_y = b.saved_cursor
        elif final == "n":
            if p1 == 5:
                self._writer("\x1b[0n")
            elif p1 == 6:
                self._writer(f"\x1b[{b.cursor_y + 1};{b.cursor_x + 1}R")
        elif final in ("h", "l") and private:
            if 1049 in params:
                if final == "h":
                    self.active_buffer = "alternate"
                    self._alternate.clear()
                else:
                    self.active_buffer = "normal"

    def snapshot(self, include_scrollback: bool) -> dict:
        b = self._buf
        return {
            "lines": b.get_lines(include_scrollback),
            "cursorPosition": {"x": b.cursor_x, "y": b.cursor_y},
            "terminalSize": {"cols": self.cols, "rows": self.rows},
            "activeBuffer": self.active_buffer,
        }
