#!/usr/bin/env python3
"""audit_timings.py — Compute cumulative cut times from EDIT and check vs ACT_TRANSITIONS.

Shows where each plan starts/ends in the output timeline, and flags
cuts that are >1.5s off from declared music ACT_TRANSITIONS.

Usage:
    python3 audit_timings.py path/to/my_project.py
"""
import argparse
import ast
import sys
from pathlib import Path


def extract_var(script_path: Path, name: str):
    tree = ast.parse(script_path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    try:
                        return ast.literal_eval(node.value)
                    except Exception:
                        return None
    return None


def fmt_time(t: float) -> str:
    mm = int(t // 60)
    ss = t - mm * 60
    return f"{mm}:{ss:06.3f}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("script", help="Path to my_project.py")
    p.add_argument("--tolerance", type=float, default=1.5,
                   help="Max acceptable drift (s) from ACT_TRANSITIONS peaks")
    args = p.parse_args()

    script = Path(args.script).expanduser().resolve()
    if not script.exists():
        sys.exit(f"❌ Not found: {script}")

    edit = extract_var(script, "EDIT")
    acts = extract_var(script, "ACT_TRANSITIONS") or []

    if not edit:
        sys.exit(f"❌ No EDIT = [...] found")

    print(f"📋 EDIT: {len(edit)} plans · ACT_TRANSITIONS: {acts}\n")

    # Compute cumulative timeline
    print(f"{'#':<4} {'plan':<55} {'start':<11} {'end':<11} {'dur':>7} {'cum':>7}")
    print("-" * 100)
    rows = []
    cum = 0.0
    for i, entry in enumerate(edit, 1):
        fname = entry[0]
        out_dur = entry[2]
        start = cum
        end = cum + out_dur
        rows.append((i, fname, start, end, out_dur))
        print(f"{i:<4} {fname[:55]:<55} {fmt_time(start):<11} {fmt_time(end):<11} "
              f"{out_dur:>7.3f} {end:>7.3f}")
        cum = end

    print(f"\n📊 Total main duration: {cum:.3f}s ({fmt_time(cum)})")

    # Check ACT_TRANSITIONS vs nearest cut
    if not acts:
        print(f"\nℹ  No ACT_TRANSITIONS declared — skipping music sync audit")
        return

    print(f"\n{'='*100}\n🎵 MUSIC SYNC AUDIT (tolerance ±{args.tolerance}s)\n{'='*100}")
    fails = 0
    for act_t in acts:
        # Find nearest cut (start of any plan)
        nearest = min(rows, key=lambda r: abs(r[2] - act_t))
        delta = nearest[2] - act_t
        status = "✅" if abs(delta) <= args.tolerance else "⚠️"
        print(f"  {status} ACT peak at {fmt_time(act_t)}  →  "
              f"nearest cut: plan #{nearest[0]} starts {fmt_time(nearest[2])} "
              f"(delta = {delta:+.3f}s)")
        if abs(delta) > args.tolerance:
            fails += 1

    if fails:
        print(f"\n⚠ {fails} act transitions off-music. Adjust nearby plan durations.")
        sys.exit(1)
    print(f"\n✅ All act transitions within ±{args.tolerance}s of music peaks.")


if __name__ == "__main__":
    main()
