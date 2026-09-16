"""Run a child process and watch it, instead of reading it afterwards.

WHY THIS EXISTS. `subprocess.run(..., capture_output=True)` holds every line the
child prints until the child exits. A runner that announces `[fluids] 40/140
passed 9` every ten cases therefore says nothing for twenty minutes and then says
everything at once — and CLAUDE.md's rule is that a run whose position is invisible
cannot be stopped early, which is where the money is. The chain watchers were fixed
twice for the same failure at the grep end **[ran]**; this is the other end of it,
where the output never reached the log to be grepped.

It still returns the whole output, because the caller stores it. The difference is
that the terminal sees each line as it lands.
"""

from __future__ import annotations

import subprocess
import sys


def run_streaming(cmd: list[str], keep: int = 400) -> tuple[int, str]:
    """Run `cmd`, echo every line as it arrives, return `(returncode, tail)`.

    `keep` is how many lines are retained for the caller — a scoring run prints
    thousands and the result file wants the end of them, not all of them.
    """
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, bufsize=1)
    lines: list[str] = []
    assert p.stdout is not None
    for line in p.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()      # the VM's log is a file; without this it buffers 8k
        lines.append(line.rstrip("\n"))
        if len(lines) > keep:
            del lines[0]
    p.wait()
    return p.returncode, "\n".join(lines)
