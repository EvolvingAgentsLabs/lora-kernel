"""A calculator the student calls, and the loop that answers it.

WHY THIS EXISTS. Distillation transferred the teacher's chain step for step and
the student still scored 1/40, because it computed pi/4 times 0.22 squared as
0.037006 when it is 0.038013 — and every later value inherited that **[ran]**
`results/P6-withdrawal-20260908/`. The physics was right. The arithmetic was not.

So the student stops computing and starts **calling**:

    3. Reynolds number: Re = rho v D / mu = <calc>998*1.1706*0.22/0.0008</calc>

The harness evaluates what is inside the tags and feeds the value back, exactly
as `ARCHITECTURE.md` describes the kernel adapter doing with action tokens. This
is that idea at its smallest: one tool, needed on every line of every chain.

THE EVALUATOR IS NOT `eval`. An expression is parsed to an AST and walked, with
arithmetic operators and a fixed set of maths functions allowed and nothing else
— no names, no attributes, no calls outside the whitelist. A sandbox that runs a
model's text through the interpreter is not a sandbox.
"""

from __future__ import annotations

import ast
import math
import re

CALL = re.compile(r"<calc>(.*?)</calc>", re.S)
OPEN = "<calc>"
CLOSE = "</calc>"

_FUNCS = {
    "sqrt": math.sqrt, "log": math.log, "log10": math.log10, "log2": math.log2,
    "exp": math.exp, "abs": abs, "sin": math.sin, "cos": math.cos,
    "tan": math.tan, "atan": math.atan, "pow": pow, "round": round,
    "min": min, "max": max,
}
_CONSTS = {"pi": math.pi, "e": math.e}

_BIN = {
    ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b,
    ast.Pow: lambda a, b: a ** b, ast.Mod: lambda a, b: a % b,
}


class CalcError(ValueError):
    pass


def _walk(node):
    if isinstance(node, ast.Expression):
        return _walk(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise CalcError(f"constant {node.value!r} is not a number")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        return _BIN[type(node.op)](_walk(node.left), _walk(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        v = _walk(node.operand)
        return v if isinstance(node.op, ast.UAdd) else -v
    if isinstance(node, ast.Name) and node.id in _CONSTS:
        return _CONSTS[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id in _FUNCS and not node.keywords:
        return _FUNCS[node.func.id](*[_walk(a) for a in node.args])
    raise CalcError(f"{type(node).__name__} is not allowed")


def evaluate(expr: str) -> float:
    """One arithmetic expression, or a CalcError. Never `eval`."""
    expr = expr.strip().rstrip("=").strip()
    # LaTeX leaks in from a teacher that writes in maths notation.
    expr = (expr.replace("\\times", "*").replace("\\cdot", "*")
                .replace("\\pi", "pi").replace("^", "**").replace(",", ""))
    if not expr:
        raise CalcError("empty expression")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise CalcError(f"unparseable: {e.msg}") from e
    # A TOOL MUST FAIL INWARDS. log10 of a negative raises ValueError, division
    # by zero raises its own, and a large power raises OverflowError — and any of
    # them escaping killed the evaluation arm mid-run [ran] 2026-09-08. The model
    # is allowed to ask for nonsense; the harness is not allowed to die of it.
    try:
        v = _walk(tree)
    except CalcError:
        raise
    except (ValueError, ZeroDivisionError, OverflowError, TypeError) as e:
        raise CalcError(f"{type(e).__name__}: {e}") from e
    if not isinstance(v, (int, float)) or not math.isfinite(v):
        raise CalcError(f"result {v!r} is not a finite number")
    return float(v)


def fill(text: str) -> tuple[str, int, int]:
    """Replace every `<calc>expr</calc>` with `<calc>expr</calc>= value`.

    Used on the teacher's own chains so the corpus shows the student what a
    call looks like AND what came back. Returns (text, calls, failures).
    """
    calls = fails = 0

    def one(m):
        nonlocal calls, fails
        calls += 1
        try:
            return f"{OPEN}{m.group(1)}{CLOSE}= {evaluate(m.group(1)):.6g}"
        except CalcError:
            fails += 1
            return m.group(0)

    return CALL.sub(one, text), calls, fails


def generate_with_tool(gen_step, system: str, user: str, max_calls: int = 12,
                       max_new_tokens: int = 900) -> tuple[str, int]:
    """Generate, stopping at every `</calc>`, answering it, and continuing.

    `gen_step(system, user, prefix, stop)` must return the continuation after
    `prefix`. The loop is the harness: the model emits a call, a process answers
    it, the model carries on — which is the whole shape of the kernel adapter,
    with one tool instead of many.
    """
    out, used = "", 0
    for _ in range(max_calls + 1):
        chunk = gen_step(system, user, out, CLOSE)
        # Trust the stop string only as far as it goes: whatever the generator
        # produced past the first `</calc>` is the model guessing the answer it
        # was told not to compute, and keeping it would put a second value in
        # the chain.
        if CLOSE in chunk:
            chunk = chunk[:chunk.index(CLOSE) + len(CLOSE)]
        out += chunk
        if CLOSE not in chunk:
            break
        # THE LAST CALL, NOT THE FIRST IN A WINDOW. Searching the final 600
        # characters returned the first match inside it, which from step two
        # onwards is an EARLIER call that was already answered — so the loop
        # re-evaluated an old expression and appended its value again, corrupting
        # every chain after its first line [ran] 2026-09-08.
        matches = list(CALL.finditer(out))
        if not matches:
            break
        m = matches[-1]
        if out[m.end():].lstrip().startswith("="):
            break                      # already answered: nothing left to do
        used += 1
        try:
            out += f"= {evaluate(m.group(1)):.6g}\n"
        except CalcError as e:
            # The failure is shown to the model rather than hidden: a tool that
            # answers wrong silently is worse than one that says it cannot.
            out += f"= ERROR: {e}\n"
    return out, used
