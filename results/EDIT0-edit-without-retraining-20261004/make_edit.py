"""EDIT0 — writes knowledge-edit/hazwaste-regs (a copy of knowledge/hazwaste-regs with ONE number changed in each of 17
supporting statements, nothing else) and questions_edit.jsonl (PAGE0's 17 rows, same questions, the new value as the
check token, the old one recorded as `stale`). Run from the repo root. Rows chosen before any edit run: the member right
on them in both top-8 records (PAGE0, FMT0), and every answer a plain quantity (no year, ZIP, form or page number, no
number also spelled in words)."""
import json
import re
import shutil
from pathlib import Path

SRC, DST = Path("knowledge/hazwaste-regs"), Path("knowledge-edit/hazwaste-regs")
R = Path("results/EDIT0-edit-without-retraining-20261004")
ROWS = ["page0-one-hop-02", "page0-one-hop-03", "page0-one-hop-04", "page0-one-hop-05", "page0-one-hop-09",
        "page0-vsqg-lqg-16", "page0-vsqg-sqg-17", "page0-satellite-lqg-19", "page0-sqg-satellite-21",
        "page0-category-cleanout-24", "page0-manifest-marking-29", "page0-electronic-manifest-30",
        "page0-import-conditions-35", "page0-episodic-petition-37", "page0-contingency-arrangements-38",
        "page0-coordinator-procedures-39", "page0-lmp-cleanout-removal-40"]

def new_answer(answer: str, old: list, new: list) -> str:
    """The row's answer with each old value replaced by its edited one — the oracle writes this line."""
    for o, n in zip(old, new):
        answer = re.sub(rf"(?<![\d.,]){o}(?![\d.,])", n, answer)
    return answer


if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
rows = {json.loads(l)["case_id"]: json.loads(l) for l in open("results/PAGE0-page-top-20261002/questions.jsonl")}
out, edits = [], []
for cid in ROWS:
    r = rows[cid]
    page, anchor = r["support"]
    f = DST / "wiki" / (page.rsplit("/", 1)[1] + ".md")
    lines = f.read_text().splitlines(keepends=True)
    i = next(j for j, l in enumerate(lines) if l.startswith(f"§{anchor} "))
    page_text = "".join(lines)
    new_tokens = []
    line = lines[i]
    for t in r["check"]["tokens"]:
        v = int(t)
        n = v + max(1, round(v * 0.3))
        while re.search(rf"(?<![\d.]){n}(?![\d.])", page_text) or str(n) in r["question"]:
            n += 1
        line, k = re.subn(rf"(?<![\d.,]){t}(?![\d.,])", str(n), line)
        assert k >= 1, (cid, t)
        new_tokens.append(str(n))
        edits.append({"case_id": cid, "statement": f"{page}#{anchor}", "old": t, "new": str(n), "occurrences": k})
    lines[i] = line
    f.write_text("".join(lines))
    out.append({**r, "case_id": cid.replace("page0-", "edit0-"), "check": {**r["check"], "tokens": new_tokens},
                "stale": r["check"]["tokens"], "answer": new_answer(r["answer"], r["check"]["tokens"], new_tokens)})
(R / "questions_edit.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out))
(R / "edits.json").write_text(json.dumps(edits, indent=1))
print(f"[edit0] {len(out)} rows, {len(edits)} numbers changed in {len({e['statement'] for e in edits})} statements")
