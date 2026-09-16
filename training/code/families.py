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


def _crc(data: bytes, poly: int, init: int, final: int) -> int:
    crc = init
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (poly if crc & 1 else 0)
    return (crc ^ final) & 0xFFFFFFFF


def crc_family(rng: random.Random) -> dict:
    """A reflected CRC-32 with a drawn polynomial over a drawn string."""
    poly = rng.choice([0xEDB88320, 0x82F63B78, 0xEB31D82E, 0xD5828281, 0x9823B6E1])
    init = rng.choice([0xFFFFFFFF, 0x00000000, 0xA5A5A5A5])
    final = rng.choice([0xFFFFFFFF, 0x00000000])
    word = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz-") for _ in range(rng.randrange(5, 14)))
    answer = _crc(word.encode(), poly, init, final)
    return {
        "family": "crc", "answer": str(answer),
        "spec": (f"a reflected CRC-32 with polynomial 0x{poly:08X}, initial value "
                 f"0x{init:08X} and final xor 0x{final:08X}, computed bit by bit "
                 f"(no lookup table)"),
        "python": f'''\
# Reflected CRC-32: polynomial 0x{poly:08X}, init 0x{init:08X}, final xor 0x{final:08X}.
POLY = 0x{poly:08X}
INIT = 0x{init:08X}
FINAL = 0x{final:08X}
DATA = b"{word}"

def crc(data):
    reg = INIT
    for byte in data:
        reg ^= byte
        for _ in range(8):
            reg = (reg >> 1) ^ (POLY if reg & 1 else 0)
    return (reg ^ FINAL) & 0xFFFFFFFF

print(crc(DATA))
''',
        "javascript": f'''\
// Reflected CRC-32: polynomial 0x{poly:08X}, init 0x{init:08X}, final xor 0x{final:08X}.
const POLY = 0x{poly:08X};
const INIT = 0x{init:08X};
const FINAL = 0x{final:08X};
const DATA = Buffer.from("{word}");

function crc(data) {{
  let reg = INIT >>> 0;
  for (const byte of data) {{
    reg = (reg ^ byte) >>> 0;
    for (let k = 0; k < 8; k++) {{
      reg = (reg & 1) ? ((reg >>> 1) ^ POLY) >>> 0 : reg >>> 1;
    }}
  }}
  return ((reg ^ FINAL) >>> 0);
}}

console.log(crc(DATA));
''',
        "c": f'''\
/* Reflected CRC-32: polynomial 0x{poly:08X}, init 0x{init:08X}, final xor 0x{final:08X}. */
#include <stdio.h>
#include <stdint.h>
#include <string.h>

#define POLY 0x{poly:08X}u
#define INIT 0x{init:08X}u
#define FINAL 0x{final:08X}u

static uint32_t crc(const unsigned char *data, size_t n) {{
    uint32_t reg = INIT;
    for (size_t i = 0; i < n; i++) {{
        reg ^= data[i];
        for (int k = 0; k < 8; k++)
            reg = (reg & 1) ? ((reg >> 1) ^ POLY) : (reg >> 1);
    }}
    return reg ^ FINAL;
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
    a, b, c = rng.choice([(11, 8, 19), (13, 17, 5), (5, 14, 1), (9, 7, 23), (15, 4, 21)])
    seed = tuple(rng.randrange(1, 2 ** 31) for _ in range(4))
    n = rng.choice([6, 8, 10])
    answer = " ".join(str(v) for v in _xorshift(seed, a, b, c, n))
    sx, sy, sz, sw = seed
    return {
        "family": "xorshift", "answer": answer,
        "spec": (f"xorshift128 with shifts {a}, {b} and {c}, printing the first {n} "
                 f"outputs space-separated"),
        "python": f'''\
# xorshift128, shifts {a}, {b}, {c}. Print the first {n} outputs.
M = 0xFFFFFFFF
x, y, z, w = {sx}, {sy}, {sz}, {sw}

def next_value():
    global x, y, z, w
    t = (x ^ ((x << {a}) & M)) & M
    x, y, z = y, z, w
    w = ((w ^ (w >> {c})) ^ (t ^ (t >> {b}))) & M
    return w

print(" ".join(str(next_value()) for _ in range({n})))
''',
        "javascript": f'''\
// xorshift128, shifts {a}, {b}, {c}. Print the first {n} outputs.
let x = {sx}, y = {sy}, z = {sz}, w = {sw};

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

static uint32_t x = {sx}u, y = {sy}u, z = {sz}u, w = {sw}u;

static uint32_t next_value(void) {{
    uint32_t t = x ^ (x << {a});
    x = y; y = z; z = w;
    w = (w ^ (w >> {c})) ^ (t ^ (t >> {b}));
    return w;
}}

int main(void) {{
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
