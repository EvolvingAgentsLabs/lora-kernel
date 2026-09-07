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


def load(run_dir: Path) -> tuple[dict, list[dict]]:
    config = json.loads((run_dir / "config.json").read_text())
    records = [json.loads(p.read_text())
               for p in sorted((run_dir / "cases").glob("*.json"))]
    return config, records


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
        ac = [x["alpha_at_0_content"] for x in rows if x.get("alpha_at_0_content") is not None]
        ca = [x["content_agreement"] for x in rows if x.get("content_agreement") is not None]
        out["drafters"][n] = {
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
                    "verified_pass": sum(r["drafters"][n]["verified"]["passed"] for r in rs),
                } for n in names
            },
        }

    # The claim the whole architecture rests on: does ordering candidates by
    # acceptance reproduce ordering them by verified quality? With this many
    # candidates a correlation coefficient would be theatre — the orderings
    # themselves are the finding.
    def _rank_key(n):
        d = out["drafters"][n]
        # Order by the payload metric when it exists; the raw one is format.
        return -(d["alpha_content"] if d["alpha_content"] is not None else d["alpha_at_0"])

    by_alpha = sorted(names, key=_rank_key)
    by_verified = sorted(names, key=lambda n: -out["drafters"][n]["verified_pass"])
    out["ordering"] = {
        "by_alpha": by_alpha,
        "by_verified": by_verified,
        "agree": by_alpha == by_verified,
        "per_region_agree": {
            region: (sorted(names, key=lambda n: -v["drafters"][n]["alpha_at_0"])
                     == sorted(names, key=lambda n: -v["drafters"][n]["verified_pass"]))
            # NOTE: per-region rows carry only the raw α, so this line and the
            # overall one can disagree about the same run. Neither is
            # interpretable while C9 stands — see the caveat printed below.
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
        f"{'drafter':<26}{'α@0':>7}{'α payload':>11}{'payload agr':>13}"
        f"{'identical':>11}{'verified':>10}{'f1':>7}",
    ]
    for name, d in s["drafters"].items():
        ac = "    n/a" if d["alpha_content"] is None else f"{d['alpha_content']:>7.3f}"
        ca = "      n/a" if d["content_agreement"] is None else f"{d['content_agreement']:>9.3f}"
        lines.append(
            f"{name:<26}{d['alpha_at_0']:>7.3f}{ac:>11}{ca:>13}"
            f"{d['same_answer_as_target']:>8}/{n:<2}"
            f"{d['verified_pass']:>7}/{n:<2}{d['verified_f1_mean']:>7.2f}")
    lines += ["", "by region (α mean / verified pass):"]
    for region, v in s["by_region"].items():
        cells = "  ".join(
            f"{k.split(':')[-1]}={x['alpha_at_0']:.2f}/{x['verified_pass']}"
            for k, x in v["drafters"].items())
        lines.append(f"  {region:<10} n={v['n']:<3} target={v['target_verified_pass']}  {cells}")
    o, h = s["ordering"], s["health"]
    lines += [
        "",
        f"ordering by α        {' > '.join(x.split(':')[-1] for x in o['by_alpha'])}",
        f"ordering by verified {' > '.join(x.split(':')[-1] for x in o['by_verified'])}",
        f"they agree: {o['agree']}   per region: {o['per_region_agree']}",
        "NOT INTERPRETABLE while C9 stands: character agreement measures layout, "
        "so an ordering by α can match the ordering by quality for reasons that "
        "have nothing to do with quality. See EXPERIMENT_PLAN.md §11.",
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
