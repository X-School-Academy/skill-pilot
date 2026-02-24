from __future__ import annotations

SPECIAL_KEYS: dict[str, str] = {
    "enter": "\r",
    "tab": "\t",
    "shift+tab": "\x1b[Z",
    "escape": "\x1b",
    "backspace": "\x7f",
    "delete": "\x1b[3~",
    "space": " ",
    "insert": "\x1b[2~",
    "up": "\x1b[A",
    "down": "\x1b[B",
    "right": "\x1b[C",
    "left": "\x1b[D",
    "shift+up": "\x1b[1;2A",
    "shift+down": "\x1b[1;2B",
    "shift+right": "\x1b[1;2C",
    "shift+left": "\x1b[1;2D",
    "alt+up": "\x1b[1;3A",
    "alt+down": "\x1b[1;3B",
    "alt+right": "\x1b[1;3C",
    "alt+left": "\x1b[1;3D",
    "ctrl+up": "\x1b[1;5A",
    "ctrl+down": "\x1b[1;5B",
    "ctrl+right": "\x1b[1;5C",
    "ctrl+left": "\x1b[1;5D",
    "home": "\x1b[H",
    "end": "\x1b[F",
    "pageup": "\x1b[5~",
    "pagedown": "\x1b[6~",
    "f1": "\x1bOP",
    "f2": "\x1bOQ",
    "f3": "\x1bOR",
    "f4": "\x1bOS",
    "f5": "\x1b[15~",
    "f6": "\x1b[17~",
    "f7": "\x1b[18~",
    "f8": "\x1b[19~",
    "f9": "\x1b[20~",
    "f10": "\x1b[21~",
    "f11": "\x1b[23~",
    "f12": "\x1b[24~",
}
for _i in range(26):
    _ch = chr(ord("a") + _i)
    SPECIAL_KEYS[f"ctrl+{_ch}"] = chr(_i + 1)
    SPECIAL_KEYS[f"alt+{_ch}"] = f"\x1b{_ch}"

TMUX_SPECIAL_KEYS = {
    "enter": "Enter",
    "tab": "Tab",
    "escape": "Escape",
    "backspace": "BSpace",
    "delete": "DC",
    "space": "Space",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "shift+up": "S-Up",
    "shift+down": "S-Down",
    "shift+left": "S-Left",
    "shift+right": "S-Right",
    "alt+up": "M-Up",
    "alt+down": "M-Down",
    "alt+left": "M-Left",
    "alt+right": "M-Right",
    "ctrl+up": "C-Up",
    "ctrl+down": "C-Down",
    "ctrl+left": "C-Left",
    "ctrl+right": "C-Right",
    "home": "Home",
    "end": "End",
    "pageup": "PageUp",
    "pagedown": "PageDown",
}
for _i in range(1, 13):
    TMUX_SPECIAL_KEYS[f"f{_i}"] = f"F{_i}"
for _i in range(26):
    _ch = chr(ord("a") + _i)
    TMUX_SPECIAL_KEYS[f"ctrl+{_ch}"] = f"C-{_ch}"
    TMUX_SPECIAL_KEYS[f"alt+{_ch}"] = f"M-{_ch}"

INTERACTIVE_ALWAYS = {
    "top",
    "htop",
    "vim",
    "nvim",
    "less",
    "more",
    "man",
    "tmux",
    "screen",
}
INTERACTIVE_WHEN_NO_ARGS = {
    "bash",
    "zsh",
    "sh",
    "fish",
    "python",
    "python3",
    "ipython",
    "node",
}
TTY_ERROR_PATTERNS = [
    r"not a tty",
    r"no tty",
    r"tty required",
    r"requires a tty",
    r"inappropriate ioctl for device",
    r"input device is not a tty",
    r"the input device is not a tty",
    r"cannot open /dev/tty",
]
