import sys
import termios
import tty

OSC = "\033]"
ST = "\007"  # BEL terminator; you can also use "\033\\"

KITTY_COLOR_KEYS = (
    "foreground",
    "background",
    "selection_foreground",
    "selection_background",
    "cursor",
    "cursor_text",
    "visual_bell",
    *[f"transparent_background_color{n}" for n in range(1, 8)],
    *[str(k) for k in range(16)],
)


def query_colors(keys=KITTY_COLOR_KEYS):
    """
    Query Kitty for the given list of color keys or, by default, all of them.

    Returns a dict mapping each key to its reported value (string).
    """
    # build the query string, e.g. "\033]21;foreground=?;ansi_1=?\007"
    body = ";".join(f"{k}=?" for k in keys)
    query = f"{OSC}21;{body}{ST}"
    sys.stdout.write(query)
    sys.stdout.flush()

    # read response until ST
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        buf = ""
        while True:
            ch = sys.stdin.read(1)
            buf += ch
            # Stop on BEL or ESC \
            if ch == "\007" or buf.endswith("\033\\"):
                break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

    # strip OSC/ST, split into key=val pairs
    # buf will be like "\033]21;foreground=rgb:ff/00/00;ansi_1=#008800\007"
    # remove leading "\033]21;" and trailing BEL/ESC\
    core = buf.lstrip("\033]").lstrip("21;").rstrip("\007").rstrip("\033\\")
    parts = core.split(";")
    result = {}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            if not v:
                result[k] = None
            else:
                result[k] = (
                    int(v[4:6], 16),
                    int(v[7:9], 16),
                    int(v[10:12], 16),
                )
    return result
