"""Program families, drawn per case, so there is a corpus and nothing to memorise.

WHY THIS EXISTS, AND IT IS A HOLE IN THE FIRST DEFINITION. `reference.py` holds
fifteen hand-written programs. That is an evaluation set; it is not a training corpus,
and **step zero — does a base model with the right adapter work — could not be run on
it at all.** Fifteen programs train nothing.

AND HAND-WRITTEN PROGRAMS CARRY THE OTHER RISK TOO. `crc32` with the standard
polynomial is in every model's training data, which is P42's ceiling: the base scored
0.815 where the adapter scored 0.825, and no treatment could have shown anything. P15
measured the same thing from the other side — a suite whose values could be recalled
was answered **27/30 without calling the tools at all**, and only a handbook drawn per
case made the experiment measure anything.

SO EVERY PROGRAM IS DRAWN. A family fixes the *shape* — a CRC over a byte string, a
xorshift with three shift amounts — and the instance fixes the **constants**: this
polynomial, these shifts, this input. The expected output did not exist before the
case was generated, so it cannot be recalled; what can be learned is **how the shape
is completed**, which is the thing an expert is for.

THE SAME FAMILY IN THREE LANGUAGES PRINTS THE SAME STRING. That is asserted per
instance rather than assumed, because a family whose languages disagree makes every
cross-language number meaningless.
"""

from __future__ import annotations

import random

LANGUAGES = ("python", "javascript", "c")


#: Structural choices drawn per instance. P54 measured that varying only the
#: CONSTANTS leaves one skeleton per (family, cut point): 197 completions collapsed
#: to **6** distinct shapes with the numbers blanked, so an adapter that recognises
#: which of six applies reaches 1.000 without computing anything **[ran]**. What has
#: to vary is what gets WRITTEN, not what gets substituted into it.
CRC_NAMES = [("reg", "byte", "crc"), ("acc", "b", "checksum"),
             ("state", "octet", "compute"), ("h", "ch", "digest"),
             ("value", "c", "crc_of")]
XS_NAMES = [("next_value", "t"), ("step", "tmp"), ("advance", "u"),
            ("pull", "s"), ("emit", "v")]


def _crc(data: bytes, poly: int, init: int, final: int) -> int:
    crc = init
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (poly if crc & 1 else 0)
    return (crc ^ final) & 0xFFFFFFFF


def crc_family(rng: random.Random) -> dict:
    """A reflected CRC-32 with a drawn polynomial over a drawn string."""
    # DRAWN FROM A LARGE SPACE, NOT A LIST OF FIVE. A pool of 5 polynomials x 3
    # inits x 2 finals is 30 combinations, so across 200 programs each one recurs
    # about seven times and the completion recurs with it — which is why P53's
    # adapter could memorise one tail and score 1.000 on held-out cases. The
    # arithmetic does not care whether the polynomial is a standard one; the
    # program is still deterministic and still verified by execution.
    poly = rng.randrange(1, 2 ** 32) | 1
    init = rng.randrange(0, 2 ** 32)
    final = rng.randrange(0, 2 ** 32)
    word = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz-") for _ in range(rng.randrange(5, 14)))
    answer = _crc(word.encode(), poly, init, final)
    reg, byte, fn = rng.choice(CRC_NAMES)
    # `while` and `for` produce genuinely different tails for the same algorithm.
    loop = rng.choice(["for", "while"])
    inner_py = (f"        for _ in range(8):" if loop == "for"
                else f"        k = 0\n        while k < 8:")
    step_py = ("            " if loop == "for" else "            ")
    tail_py = "" if loop == "for" else "\n            k += 1"
    return {
        "family": "crc", "answer": str(answer),
        # The literals this instance drew. A completion that contains none of them
        # is the same text for every instance of the family, which is what P53
        # measured: 180 of 180 held-out completions already in the training set.
        "varies": [f"0x{poly:08X}", f"0x{init:08X}", f"0x{final:08X}", word,
                   reg, fn],
        "spec": (f"a reflected CRC-32 with polynomial 0x{poly:08X}, initial value "
                 f"0x{init:08X} and final xor 0x{final:08X}, computed bit by bit "
                 f"(no lookup table)"),
        "python": f'''\
# Reflected CRC-32: polynomial 0x{poly:08X}, init 0x{init:08X}, final xor 0x{final:08X}.
DATA = b"{word}"

def {fn}(data):
    {reg} = 0x{init:08X}
    for {byte} in data:
        {reg} ^= {byte}
{inner_py}
{step_py}{reg} = ({reg} >> 1) ^ (0x{poly:08X} if {reg} & 1 else 0){tail_py}
    return ({reg} ^ 0x{final:08X}) & 0xFFFFFFFF

print({fn}(DATA))
''',
        "javascript": f'''\
// Reflected CRC-32: polynomial 0x{poly:08X}, init 0x{init:08X}, final xor 0x{final:08X}.
const DATA = Buffer.from("{word}");

function crc(data) {{
  let reg = 0x{init:08X} >>> 0;
  for (const byte of data) {{
    reg = (reg ^ byte) >>> 0;
    for (let k = 0; k < 8; k++) {{
      reg = (reg & 1) ? ((reg >>> 1) ^ 0x{poly:08X}) >>> 0 : reg >>> 1;
    }}
  }}
  return ((reg ^ 0x{final:08X}) >>> 0);
}}

console.log(crc(DATA));
''',
        "c": f'''\
/* Reflected CRC-32: polynomial 0x{poly:08X}, init 0x{init:08X}, final xor 0x{final:08X}. */
#include <stdio.h>
#include <stdint.h>
#include <string.h>

static uint32_t crc(const unsigned char *data, size_t n) {{
    uint32_t reg = 0x{init:08X}u;
    for (size_t i = 0; i < n; i++) {{
        reg ^= data[i];
        for (int k = 0; k < 8; k++)
            reg = (reg & 1) ? ((reg >> 1) ^ 0x{poly:08X}u) : (reg >> 1);
    }}
    return reg ^ 0x{final:08X}u;
}}

int main(void) {{
    const char *s = "{word}";
    printf("%u\\n", crc((const unsigned char *)s, strlen(s)));
    return 0;
}}
''',
    }


def _xorshift(seed, a, b, c, n):
    x, y, z, w = seed
    M = 0xFFFFFFFF
    out = []
    for _ in range(n):
        t = (x ^ ((x << a) & M)) & M
        x, y, z = y, z, w
        w = ((w ^ (w >> c)) ^ (t ^ (t >> b))) & M
        out.append(w)
    return out


def xorshift_family(rng: random.Random) -> dict:
    """xorshift128 with drawn shift amounts and a drawn seed."""
    # Same reason: five shift triples is five distinct tails.
    a = rng.randrange(1, 32)
    b = rng.randrange(1, 32)
    c = rng.randrange(1, 32)
    seed = tuple(rng.randrange(1, 2 ** 31) for _ in range(4))
    n = rng.randrange(5, 13)
    answer = " ".join(str(v) for v in _xorshift(seed, a, b, c, n))
    sx, sy, sz, sw = seed
    fn, tmp = rng.choice(XS_NAMES)
    return {
        "family": "xorshift", "answer": answer,
        "varies": [str(sx), str(sy), str(sz), str(sw), f"<< {a}", f">> {b}",
                   f">> {c}", f"({n})", fn, tmp],
        "spec": (f"xorshift128 with shifts {a}, {b} and {c}, printing the first {n} "
                 f"outputs space-separated"),
        "python": f'''\
# xorshift128, shifts {a}, {b}, {c}. Print the first {n} outputs.
M = 0xFFFFFFFF

def make_state():
    return [{sx}, {sy}, {sz}, {sw}]

x, y, z, w = make_state()

def {fn}():
    global x, y, z, w
    {tmp} = (x ^ ((x << {a}) & M)) & M
    x, y, z = y, z, w
    w = ((w ^ (w >> {c})) ^ ({tmp} ^ ({tmp} >> {b}))) & M
    return w

print(" ".join(str({fn}()) for _ in range({n})))
''',
        "javascript": f'''\
// xorshift128, shifts {a}, {b}, {c}. Print the first {n} outputs.
let x, y, z, w;

function makeState() {{
  x = {sx}; y = {sy}; z = {sz}; w = {sw};
}}

makeState();

function nextValue() {{
  const t = (x ^ (x << {a})) >>> 0;
  x = y; y = z; z = w;
  w = ((w ^ (w >>> {c})) ^ (t ^ (t >>> {b}))) >>> 0;
  return w;
}}

const out = [];
for (let i = 0; i < {n}; i++) out.push(nextValue());
console.log(out.join(" "));
''',
        "c": f'''\
/* xorshift128, shifts {a}, {b}, {c}. Print the first {n} outputs. */
#include <stdio.h>
#include <stdint.h>

static uint32_t x, y, z, w;

static void make_state(void) {{
    x = {sx}u; y = {sy}u; z = {sz}u; w = {sw}u;
}}

static uint32_t next_value(void) {{
    uint32_t t = x ^ (x << {a});
    x = y; y = z; z = w;
    w = (w ^ (w >> {c})) ^ (t ^ (t >> {b}));
    return w;
}}

int main(void) {{
    make_state();
    for (int i = 0; i < {n}; i++)
        printf("%u%s", next_value(), i == {n} - 1 ? "\\n" : " ");
    return 0;
}}
''',
    }


FAMILIES = {"crc": crc_family, "xorshift": xorshift_family}


def draw(rng: random.Random, family: str | None = None) -> dict:
    name = family or rng.choice(sorted(FAMILIES))
    return FAMILIES[name](rng)
