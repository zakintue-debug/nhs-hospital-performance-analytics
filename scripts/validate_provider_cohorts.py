"""Recompute provider cohorts by stable code; no third-party dependencies."""
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

def analyse(path, attendance, over, min_months):
    groups = defaultdict(list)
    keys = set()
    for row in csv.DictReader(path.open(encoding="utf-8-sig")):
        key = (row["Org Code"], row["Month"])
        if key in keys:
            raise ValueError(f"Duplicate provider-month: {key}")
        keys.add(key)
        a, o = float(row[attendance]), float(row[over])
        if not (math.isfinite(a) and math.isfinite(o) and 0 <= o <= a):
            raise ValueError(f"Invalid counts: {key}")
        groups[row["Org Code"]].append((row["Month"], row["Org name"], a, o))
    providers = []
    for org, rows in groups.items():
        active = [r for r in rows if r[2] > 0]
        if len(active) < min_months:
            continue
        total = sum(r[2] for r in active)
        providers.append(dict(org_code=org, name=max(rows)[1], months=len(active),
                              attendances=total, performance=100*(1-sum(r[3] for r in active)/total)))
    xs = [p["attendances"]/p["months"] for p in providers]
    ys = [p["performance"] for p in providers]
    if len(xs) < 2:
        corr = None
    else:
        mx, my = sum(xs)/len(xs), sum(ys)/len(ys)
        den = math.sqrt(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))
        corr = sum((x-mx)*(y-my) for x,y in zip(xs,ys))/den if den else None
    return dict(provider_count=len(providers), correlation_mean_monthly_attendance_vs_weighted_performance=corr,
                top_10=sorted(providers, key=lambda p:(-p["attendances"],p["org_code"]))[:10])

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=Path(__file__).resolve().parents[1]/"data/processed")
    p.add_argument("--min-months", type=int, default=24)
    args=p.parse_args()
    if args.min_months < 1:
        p.error("--min-months must be positive")
    print(json.dumps(dict(scope="Non-booked attendance columns; positive-attendance months; stable organisation code",
        min_months=args.min_months,
        all_departments=analyse(args.data/"ae_provider_month.csv","Total A&E Attendances","Total Over 4 Hours",args.min_months),
        type1=analyse(args.data/"ae_type1_provider_month.csv","Type 1 Attendances","Type 1 Over 4 Hours",args.min_months)),indent=2))

if __name__ == "__main__":
    main()
