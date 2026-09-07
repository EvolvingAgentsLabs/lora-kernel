"""Read the run directory back and say what it licenses.

Every number here is read from `cases/*.json`, never from a run's stdout. The
report deliberately refuses to print α on its own: the promotion decision is made
on α AND the verified score of the same configuration, and α has been
anti-correlated with expertise before.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from alpha.cases import parse_answer


def semantic(drafter_answer: str, target_answer: str) -> tuple[bool, float] | None:
    """Does the candidate say what the target said — as an answer, not as text.

    THIS IS THE PROMOTION CRITERION, decided 2026-09-07 (EXPERIMENT_PLAN.md §11)
    after character agreement was measured scoring a correct compact answer 0.00
    and an indented copy of the same answer 1.00. Both answers are parsed and
    compared as sets, so item order, whitespace, indentation and a markdown fence
    are all incapable of moving the number.

    None when either side did not produce the declared shape: a model that
    answered nothing parseable has no answer to agree with, and scoring that as
    either 0 or 1 invents a fact.
    """
    a, b = parse_answer(drafter_answer), parse_answer(target_answer)
    if a is None or b is None:
        return None
    if not a and not b:
        return True, 1.0
    tp = len(a & b)
    precision = tp / len(a) if a else 0.0
    recall = tp / len(b) if b else 0.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return a == b, round(f1, 3)


def load(run_dir: Path) -> tuple[dict, list[dict]]:
    config = json.loads((run_dir / "config.json").read_text())
    records = [json.loads(p.read_text())
               for p in sorted((run_dir / "cases").glob("*.json"))]
    return config, records


def _region_agreement(rs: list[dict], name: str) -> float | None:
    vals = [t[0] for t in (semantic(r["drafters"][name]["own_answer"], r["target"]["answer"])
                           for r in rs) if t is not None]
    return round(sum(vals) / len(vals), 4) if vals else None


def summarise(config: dict, records: list[dict]) -> dict:
    if not records:
        return {"error": "no cases on disk"}
    names = list(records[0]["drafters"].keys())
    out = {
        "run": {**config, "cases_on_disk": len(records)},
        "target_verified_pass": sum(r["target"]["verified"]["passed"] for r in records),
        "target_parse_failures": sum(not r["target"]["verified"]["parsed"] for r in records),
        "drafters": {},
        "by_region": {},
    }

    for n in names:
        rows = [r["drafters"][n] for r in records]
        a0 = [x["alpha_at_0"] for x in rows]
        mid = [x["alpha_mid_mean"] for x in rows if x.get("alpha_mid_mean") is not None]
        restarts = [x["restarted_fraction"] for x in rows
                    if x.get("restarted_fraction") is not None]
        sem = [semantic(x["own_answer"], r["target"]["answer"])
               for x, r in zip(rows, records)]
        sem_ok = [t for t in sem if t is not None]
        ac = [x["alpha_at_0_content"] for x in rows if x.get("alpha_at_0_content") is not None]
        ca = [x["content_agreement"] for x in rows if x.get("content_agreement") is not None]
        out["drafters"][n] = {
            # -- the promotion criterion (§11) --
            "same_answer_as_target_rate": (
                round(sum(t[0] for t in sem_ok) / len(sem_ok), 4) if sem_ok else None),
            "answer_f1_vs_target": (
                round(statistics.fmean(t[1] for t in sem_ok), 4) if sem_ok else None),
            "unparseable_either_side": len(sem) - len(sem_ok),
            # -- character acceptance, kept beside it and only comparable
            #    within one model family (C9) --
            "alpha_at_0": round(statistics.fmean(a0), 4),
            "alpha_content": round(statistics.fmean(ac), 4) if ac else None,
            "content_agreement": round(statistics.fmean(ca), 4) if ca else None,
            "format_absent": len(rows) - len(ac),
            "same_answer_as_target": sum(bool(x.get("same_answer")) for x in rows),
            "alpha_at_0_sd": round(statistics.pstdev(a0), 4) if len(a0) > 1 else 0.0,
            "agreement_fraction": round(
                statistics.fmean(x["agreement_fraction"] for x in rows), 4),
            "alpha_mid": round(statistics.fmean(mid), 4) if mid else None,
            "verified_pass": sum(x["verified"]["passed"] for x in rows),
            "verified_f1_mean": round(statistics.fmean(x["verified"]["f1"] for x in rows), 3),
            "parse_failures": sum(not x["verified"]["parsed"] for x in rows),
            "empty_answers": sum(not x["own_answer"].strip() for x in rows),
            "thought_chars_mean": round(
                statistics.fmean(x.get("thought_chars", 0) for x in rows), 1),
            "restarted_fraction": round(statistics.fmean(restarts), 3) if restarts else None,
        }

    regions = defaultdict(list)
    for r in records:
        regions[r["region"]].append(r)
    for region, rs in sorted(regions.items()):
        out["by_region"][region] = {
            "n": len(rs),
            "target_verified_pass": sum(r["target"]["verified"]["passed"] for r in rs),
            "drafters": {
                n: {
                    "alpha_at_0": round(
                        statistics.fmean(r["drafters"][n]["alpha_at_0"] for r in rs), 4),
                    "agreement": _region_agreement(rs, n),
                    "verified_pass": sum(r["drafters"][n]["verified"]["passed"] for r in rs),
                } for n in names
            },
        }

    # The claim the whole architecture rests on: does ordering candidates by
    # acceptance reproduce ordering them by verified quality? With this many
    # candidates a correlation coefficient would be theatre — the orderings
    # themselves are the finding.
    def _rank_key(n):
        # The promotion criterion ranks. Character acceptance does not rank
        # anything while C9 stands — it is reported, not obeyed.
        d = out["drafters"][n]
        return -(d["same_answer_as_target_rate"] or 0.0)

    by_alpha = sorted(names, key=_rank_key)
    by_verified = sorted(names, key=lambda n: -out["drafters"][n]["verified_pass"])
    # A tie in verified quality is not a disagreement about ordering. Reporting
    # it as one manufactures a failed test out of an untestable one.
    verified_vals = {out["drafters"][n]["verified_pass"] for n in names}
    comparable = len(verified_vals) == len(names)
    out["ordering"] = {
        "criterion": "semantic answer agreement with the target (EXPERIMENT_PLAN.md §11)",
        "comparable": comparable,
        "by_agreement": by_alpha,
        "by_alpha_chars": sorted(
            names, key=lambda n: -(out["drafters"][n]["alpha_content"] or 0.0)),
        "by_alpha": by_alpha,
        "by_verified": by_verified,
        "agree": (by_alpha == by_verified) if comparable else None,
        "per_region_agree": {
            region: (sorted(names, key=lambda n: -(v["drafters"][n]["agreement"] or 0.0))
                     == sorted(names, key=lambda n: -v["drafters"][n]["verified_pass"]))
            for region, v in out["by_region"].items()
        },
    }

    # Instrument health, reported before any conclusion is drawn from the run.
    spread = ([(out["drafters"][n]["alpha_content"]
                if out["drafters"][n]["alpha_content"] is not None
                else out["drafters"][n]["alpha_at_0"]) for n in names] or [0.0])
    restarts = [out["drafters"][n]["restarted_fraction"] for n in names
                if out["drafters"][n]["restarted_fraction"] is not None]
    out["health"] = {
        "alpha_dispersion": round(max(spread) - min(spread), 4),
        "worst_restarted_fraction": max(restarts) if restarts else None,
        "target_thought_chars_mean": round(
            statistics.fmean(r["target"].get("thought_chars", 0) for r in records), 1),
        "target_answer_chars_mean": round(
            statistics.fmean(len(r["target"]["answer"]) for r in records), 1),
        "headroom_target_minus_best_drafter":
            out["target_verified_pass"] - max(
                out["drafters"][n]["verified_pass"] for n in names),
    }
    return out


def render(s: dict) -> str:
    if "error" in s:
        return s["error"]
    r, n = s["run"], s["run"]["cases_on_disk"]
    lines = [
        f"target        {r['target']}",
        f"cases         {n} from {r['split']}   w={r['window_chars']}ch  "
        f"positions={r['positions']}  prompt={r['prompt_hash']}",
        f"target score  {s['target_verified_pass']}/{n} verified "
        f"({s['target_parse_failures']} unparseable)",
        "",
        "PROMOTION CRITERION — semantic answer agreement with the target (§11)",
        f"{'drafter':<26}{'same answer':>13}{'answer f1':>11}"
        f"{'verified':>11}{'f1 vs truth':>13}{'unparseable':>12}",
    ]
    for name, d in s["drafters"].items():
        sa = "n/a" if d["same_answer_as_target_rate"] is None else f"{d['same_answer_as_target_rate']:.3f}"
        af = "n/a" if d["answer_f1_vs_target"] is None else f"{d['answer_f1_vs_target']:.3f}"
        lines.append(
            f"{name:<26}{sa:>13}{af:>11}{d['verified_pass']:>8}/{n:<2}"
            f"{d['verified_f1_mean']:>13.2f}{d['unparseable_either_side']:>12}")
    worst = max((d["unparseable_either_side"] for d in s["drafters"].values()),
                default=0)
    if worst:
        lines += ["", "!! agreement EXCLUDES cases where a side produced no parseable "
                  "answer, so a model that often answers nothing looks like a good "
                  "agreer. Read the criterion beside the unparseable column, always — "
                  "and note that this is exactly the failure harness.lora exists to "
                  "repair (C11)."]
    lines += ["", "character acceptance — reported, never obeyed (C9):"]
    for name, d in s["drafters"].items():
        ac = "n/a" if d["alpha_content"] is None else f"{d['alpha_content']:.3f}"
        lines.append(f"  {name:<26}α@0={d['alpha_at_0']:.3f}  payload={ac}"
                     f"  layout-identical answers={d['same_answer_as_target']}/{n}")
    lines += ["", "by region (answer agreement / verified pass):"]
    for region, v in s["by_region"].items():
        cells = "  ".join(
            f"{k.split(':')[-1]}={'n/a' if x['agreement'] is None else format(x['agreement'], '.2f')}"
            f"/{x['verified_pass']}"
            for k, x in v["drafters"].items())
        lines.append(f"  {region:<10} n={v['n']:<3} target={v['target_verified_pass']}  {cells}")
    o, h = s["ordering"], s["health"]
    lines += [
        "",
        f"ordering by agreement {' > '.join(x.split(':')[-1] for x in o['by_agreement'])}",
        f"ordering by verified  {' > '.join(x.split(':')[-1] for x in o['by_verified'])}",
        (f"they agree: {o['agree']}   per region: {o['per_region_agree']}"
         if o["comparable"] else
         "not comparable: the candidates tie on verified quality, so there is no "
         "ordering for the criterion to reproduce"),
        f"(ordering by character α would have said: "
        f"{' > '.join(x.split(':')[-1] for x in o['by_alpha_chars'])} — kept visible "
        f"because S6's win condition is whether pinning the format makes these two agree)",
        "",
        f"health: α dispersion {h['alpha_dispersion']:.3f} "
        f"(no dispersion = nothing to route on)",
        f"        headroom target−best drafter "
        f"{h['headroom_target_minus_best_drafter']:+d} of {n} "
        f"(≈0 = this suite cannot show a withdrawal gap)",
        f"        target emits {h['target_thought_chars_mean']:.0f} chars of thinking "
        f"before {h['target_answer_chars_mean']:.0f} chars of answer",
        ("        mid-answer α not measured (positions=1)"
         if h["worst_restarted_fraction"] is None else
         f"        worst prefill restart rate {h['worst_restarted_fraction']:.2f} "
         f"— above 0 the mid-answer α is the instrument, not the model"),
    ]
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python3 -m alpha.report <run-dir>", file=sys.stderr)
        return 1
    run_dir = Path(sys.argv[1])
    config, records = load(run_dir)
    s = summarise(config, records)
    (run_dir / "report.json").write_text(json.dumps(s, indent=2))
    print(render(s))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
