"""Reference implementations, one per (algorithm, language), and what they print.

WHY CODE COMPLETION IS THE RIGHT PREDICATE. Everything this architecture does rests
on a prediction aligning with a target's, and C9 measured what breaks that: identical
answers scored **0.00** across formats while different answers scored 0.44 within one
**[ran]**. Layout dominated. **A code prefix has already fixed the layout** — the
indentation, the names, the style are in the prompt — so the continuation is
constrained by the algorithm rather than by a convention nobody agreed on.

And it fixes the deepest problem in `docs/REPORT.md`: *a generated suite cannot
contain a difficulty its author did not think of*. Here the difficulty is **where the
implementation is cut**, which comes from the algorithm, not from us. The verifier is
**execution**, which is the strongest one this project has ever had — not a
definition, not a judge.

WHICH ALGORITHMS, AND WHY NOT ONLY THE DFT. Four properties decide a candidate:

    exact output          floats need a tolerance, and a tolerance is a dial
                          nobody chooses that moves every number
    specified constants   the continuation is pinned by the algorithm
    real language variation  otherwise the experts are one expert
    NOT the most memorised  P42: the base scored 0.815 where the adapter scored 0.825

The DFT scores **two of four**: its constants and its language variation are fine,
but it emits floats and it is one of the most reproduced snippets in existence. Both
are the failure modes this project has already paid for. So it is kept — as the
candidate to *measure* rather than to assume — beside three that score better, and
the base's own profile decides. `levenshtein` is in for the opposite reason: it is
deliberately the most canonical, a **ceiling control** in the sense P42 taught.

SAFETY. Completions are executed. That happens on a disposable rented VM, never here,
and the runner passes no network and a fixed timeout.
"""

from __future__ import annotations

LANGUAGES = ("python", "javascript", "c")
ALGORITHMS = ("crc32", "xorshift128", "base32", "levenshtein", "dft")

#: What each algorithm is, in the words the prompt uses. Precise enough that the
#: continuation is determined, which is the whole point of the predicate.
SPEC = {
    "crc32": "CRC-32 (IEEE 802.3, reflected, polynomial 0xEDB88320, init 0xFFFFFFFF, "
             "final xor 0xFFFFFFFF), table-driven",
    "xorshift128": "xorshift128 (Marsaglia), 32-bit state x,y,z,w with shifts 11, 8, 19",
    "base32": "Base32 encoding, RFC 4648 alphabet A-Z2-7 with '=' padding",
    "levenshtein": "Levenshtein edit distance, classic dynamic programme",
    "dft": "the naive discrete Fourier transform, printing magnitudes",
}

#: (algorithm, language) -> (source, expected stdout). Every one of these is executed
#: by `tests/test_reference.py`; a reference that does not run is not a reference.
REFERENCE: dict[tuple[str, str], tuple[str, str]] = {}


REFERENCE[("crc32", "python")] = ('''\
# CRC-32, IEEE 802.3 reflected, polynomial 0xEDB88320.
DATA = b"lora-kernel"

def make_table():
    table = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ (0xEDB88320 if c & 1 else 0)
        table.append(c)
    return table

TABLE = make_table()

def crc32(data):
    crc = 0xFFFFFFFF
    for byte in data:
        crc = TABLE[(crc ^ byte) & 0xFF] ^ (crc >> 8)
    return crc ^ 0xFFFFFFFF

print(crc32(DATA))
''', None)

REFERENCE[("crc32", "javascript")] = ('''\
// CRC-32, IEEE 802.3 reflected, polynomial 0xEDB88320.
const DATA = Buffer.from("lora-kernel");

function makeTable() {
  const table = [];
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let k = 0; k < 8; k++) {
      c = (c & 1) ? ((c >>> 1) ^ 0xEDB88320) : (c >>> 1);
    }
    table.push(c >>> 0);
  }
  return table;
}

const TABLE = makeTable();

function crc32(data) {
  let crc = 0xFFFFFFFF;
  for (const byte of data) {
    crc = (TABLE[(crc ^ byte) & 0xFF] ^ (crc >>> 8)) >>> 0;
  }
  return (crc ^ 0xFFFFFFFF) >>> 0;
}

console.log(crc32(DATA));
''', None)

REFERENCE[("crc32", "c")] = ('''\
/* CRC-32, IEEE 802.3 reflected, polynomial 0xEDB88320. */
#include <stdio.h>
#include <stdint.h>
#include <string.h>

static uint32_t TABLE[256];

static void make_table(void) {
    for (uint32_t i = 0; i < 256; i++) {
        uint32_t c = i;
        for (int k = 0; k < 8; k++)
            c = (c & 1) ? ((c >> 1) ^ 0xEDB88320u) : (c >> 1);
        TABLE[i] = c;
    }
}

static uint32_t crc32(const unsigned char *data, size_t n) {
    uint32_t crc = 0xFFFFFFFFu;
    for (size_t i = 0; i < n; i++)
        crc = TABLE[(crc ^ data[i]) & 0xFF] ^ (crc >> 8);
    return crc ^ 0xFFFFFFFFu;
}

int main(void) {
    const char *s = "lora-kernel";
    make_table();
    printf("%u\\n", crc32((const unsigned char *)s, strlen(s)));
    return 0;
}
''', None)


REFERENCE[("xorshift128", "python")] = ('''\
# xorshift128 (Marsaglia), 32-bit state, shifts 11, 8, 19.
M = 0xFFFFFFFF

class Xorshift128:
    def __init__(self, x, y, z, w):
        self.x, self.y, self.z, self.w = x, y, z, w

    def next(self):
        t = (self.x ^ ((self.x << 11) & M)) & M
        self.x, self.y, self.z = self.y, self.z, self.w
        self.w = (self.w ^ (self.w >> 19)) ^ (t ^ (t >> 8))
        self.w &= M
        return self.w

rng = Xorshift128(123456789, 362436069, 521288629, 88675123)
print(" ".join(str(rng.next()) for _ in range(8)))
''', None)

REFERENCE[("xorshift128", "javascript")] = ('''\
// xorshift128 (Marsaglia), 32-bit state, shifts 11, 8, 19.
class Xorshift128 {
  constructor(x, y, z, w) { this.x = x; this.y = y; this.z = z; this.w = w; }
  next() {
    let t = (this.x ^ (this.x << 11)) >>> 0;
    this.x = this.y; this.y = this.z; this.z = this.w;
    this.w = ((this.w ^ (this.w >>> 19)) ^ (t ^ (t >>> 8))) >>> 0;
    return this.w;
  }
}

const rng = new Xorshift128(123456789, 362436069, 521288629, 88675123);
const out = [];
for (let i = 0; i < 8; i++) out.push(rng.next());
console.log(out.join(" "));
''', None)

REFERENCE[("xorshift128", "c")] = ('''\
/* xorshift128 (Marsaglia), 32-bit state, shifts 11, 8, 19. */
#include <stdio.h>
#include <stdint.h>

static uint32_t x = 123456789u, y = 362436069u, z = 521288629u, w = 88675123u;

static uint32_t next_value(void) {
    uint32_t t = x ^ (x << 11);
    x = y; y = z; z = w;
    w = (w ^ (w >> 19)) ^ (t ^ (t >> 8));
    return w;
}

int main(void) {
    for (int i = 0; i < 8; i++)
        printf("%u%s", next_value(), i == 7 ? "\\n" : " ");
    return 0;
}
''', None)

REFERENCE[("levenshtein", "python")] = ('''\
# Levenshtein edit distance, classic dynamic programme.
PAIRS = [("kitten", "sitting"), ("flaw", "lawn"), ("lora", "kernel"),
         ("", "abc"), ("same", "same")]

def distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

print(" ".join(str(distance(a, b)) for a, b in PAIRS))
''', None)

REFERENCE[("levenshtein", "javascript")] = ('''\
// Levenshtein edit distance, classic dynamic programme.
const PAIRS = [["kitten", "sitting"], ["flaw", "lawn"], ["lora", "kernel"],
               ["", "abc"], ["same", "same"]];

function distance(a, b) {
  let prev = [];
  for (let j = 0; j <= b.length; j++) prev.push(j);
  for (let i = 1; i <= a.length; i++) {
    const cur = [i];
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      cur.push(Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost));
    }
    prev = cur;
  }
  return prev[b.length];
}

console.log(PAIRS.map(([a, b]) => distance(a, b)).join(" "));
''', None)

REFERENCE[("levenshtein", "c")] = ('''\
/* Levenshtein edit distance, classic dynamic programme. */
#include <stdio.h>
#include <string.h>

static int min3(int a, int b, int c) {
    int m = a < b ? a : b;
    return m < c ? m : c;
}

static int distance(const char *a, const char *b) {
    int la = (int)strlen(a), lb = (int)strlen(b);
    int prev[256], cur[256];
    for (int j = 0; j <= lb; j++) prev[j] = j;
    for (int i = 1; i <= la; i++) {
        cur[0] = i;
        for (int j = 1; j <= lb; j++) {
            int cost = a[i - 1] == b[j - 1] ? 0 : 1;
            cur[j] = min3(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost);
        }
        for (int j = 0; j <= lb; j++) prev[j] = cur[j];
    }
    return prev[lb];
}

int main(void) {
    const char *pairs[5][2] = {{"kitten", "sitting"}, {"flaw", "lawn"},
                               {"lora", "kernel"}, {"", "abc"}, {"same", "same"}};
    for (int i = 0; i < 5; i++)
        printf("%d%s", distance(pairs[i][0], pairs[i][1]), i == 4 ? "\\n" : " ");
    return 0;
}
''', None)


REFERENCE[("base32", "python")] = ('''\
# Base32, RFC 4648 alphabet, '=' padding.
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
INPUTS = [b"", b"f", b"fo", b"foo", b"foob", b"fooba", b"foobar"]

def encode(data):
    out = []
    for i in range(0, len(data), 5):
        chunk = data[i:i + 5]
        n = int.from_bytes(chunk + b"\\x00" * (5 - len(chunk)), "big")
        digits = [(n >> (35 - 5 * k)) & 31 for k in range(8)]
        keep = (len(chunk) * 8 + 4) // 5
        out.append("".join(ALPHABET[d] for d in digits[:keep]))
        out.append("=" * (8 - keep))
    return "".join(out)

print(" ".join(encode(x) or "-" for x in INPUTS))
''', None)

REFERENCE[("base32", "javascript")] = ('''\
// Base32, RFC 4648 alphabet, '=' padding.
const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
const INPUTS = ["", "f", "fo", "foo", "foob", "fooba", "foobar"];

function encode(data) {
  const bytes = Buffer.from(data);
  let out = "";
  for (let i = 0; i < bytes.length; i += 5) {
    const chunk = bytes.slice(i, i + 5);
    const padded = Buffer.concat([chunk, Buffer.alloc(5 - chunk.length)]);
    let n = 0n;
    for (const b of padded) n = (n << 8n) | BigInt(b);
    const digits = [];
    for (let k = 0; k < 8; k++)
      digits.push(Number((n >> BigInt(35 - 5 * k)) & 31n));
    const keep = Math.floor((chunk.length * 8 + 4) / 5);
    out += digits.slice(0, keep).map((d) => ALPHABET[d]).join("");
    out += "=".repeat(8 - keep);
  }
  return out;
}

console.log(INPUTS.map((x) => encode(x) || "-").join(" "));
''', None)

REFERENCE[("base32", "c")] = ('''\
/* Base32, RFC 4648 alphabet, '=' padding. */
#include <stdio.h>
#include <string.h>
#include <stdint.h>

static const char *ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

static void encode(const unsigned char *data, size_t n, char *out) {
    size_t o = 0;
    for (size_t i = 0; i < n; i += 5) {
        size_t len = n - i < 5 ? n - i : 5;
        uint64_t v = 0;
        for (size_t k = 0; k < 5; k++)
            v = (v << 8) | (k < len ? data[i + k] : 0);
        size_t keep = (len * 8 + 4) / 5;
        for (size_t k = 0; k < 8; k++)
            out[o++] = k < keep ? ALPHABET[(v >> (35 - 5 * k)) & 31] : '=';
    }
    out[o] = 0;
}

int main(void) {
    const char *inputs[7] = {"", "f", "fo", "foo", "foob", "fooba", "foobar"};
    char buf[64];
    for (int i = 0; i < 7; i++) {
        encode((const unsigned char *)inputs[i], strlen(inputs[i]), buf);
        printf("%s%s", buf[0] ? buf : "-", i == 6 ? "\\n" : " ");
    }
    return 0;
}
''', None)

REFERENCE[("dft", "python")] = ('''\
# Naive discrete Fourier transform, magnitudes rounded to 4 decimals.
import cmath

SIGNAL = [1.0, 2.0, 3.0, 4.0, 4.0, 3.0, 2.0, 1.0]

def dft(x):
    n = len(x)
    out = []
    for k in range(n):
        acc = 0j
        for t in range(n):
            acc += x[t] * cmath.exp(-2j * cmath.pi * k * t / n)
        out.append(abs(acc))
    return out

print(" ".join("%.4f" % v for v in dft(SIGNAL)))
''', None)

REFERENCE[("dft", "javascript")] = ('''\
// Naive discrete Fourier transform, magnitudes rounded to 4 decimals.
const SIGNAL = [1.0, 2.0, 3.0, 4.0, 4.0, 3.0, 2.0, 1.0];

function dft(x) {
  const n = x.length;
  const out = [];
  for (let k = 0; k < n; k++) {
    let re = 0, im = 0;
    for (let t = 0; t < n; t++) {
      const a = (-2 * Math.PI * k * t) / n;
      re += x[t] * Math.cos(a);
      im += x[t] * Math.sin(a);
    }
    out.push(Math.sqrt(re * re + im * im));
  }
  return out;
}

console.log(dft(SIGNAL).map((v) => v.toFixed(4)).join(" "));
''', None)

REFERENCE[("dft", "c")] = ('''\
/* Naive discrete Fourier transform, magnitudes rounded to 4 decimals. */
#include <stdio.h>
#include <math.h>

static const double SIGNAL[8] = {1.0, 2.0, 3.0, 4.0, 4.0, 3.0, 2.0, 1.0};

int main(void) {
    int n = 8;
    for (int k = 0; k < n; k++) {
        double re = 0.0, im = 0.0;
        for (int t = 0; t < n; t++) {
            double a = -2.0 * M_PI * k * t / n;
            re += SIGNAL[t] * cos(a);
            im += SIGNAL[t] * sin(a);
        }
        printf("%.4f%s", sqrt(re * re + im * im), k == n - 1 ? "\\n" : " ");
    }
    return 0;
}
''', None)
