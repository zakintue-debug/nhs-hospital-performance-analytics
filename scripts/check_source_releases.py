"""Recheck the pinned NHS release comparison with locally downloaded CSVs.

Pass a directory containing YYYY-MM.csv for each row of docs/source-reconciliation.csv.
Each URL and SHA-256 identifies the provider release used. No files are overwritten.
"""
import argparse
import calendar
import csv
import hashlib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
MEASURES = {
    "attendances": ["A&E attendances Type 1", "A&E attendances Type 2", "A&E attendances Other A&E Department"],
    "over4": ["Attendances over 4hrs Type 1", "Attendances over 4hrs Type 2", "Attendances over 4hrs Other Department"],
    "admissions_via_ae": ["Emergency admissions via A&E - Type 1", "Emergency admissions via A&E - Type 2",
                          "Emergency admissions via A&E - Other A&E department"],
    "type1_attendances": ["A&E attendances Type 1"],
    "type1_over4": ["Attendances over 4hrs Type 1"],
    "booked_attendances": ["A&E attendances Booked Appointments " + t for t in ("Type 1", "Type 2", "Other Department")],
    "booked_over4": ["Attendances over 4hrs Booked Appointments " + t for t in ("Type 1", "Type 2", "Other Department")],
}


def check(directory):
    keys = ["Month", "Org Code"]
    all_depts = pd.read_csv(DATA / "ae_provider_month.csv").set_index(keys, verify_integrity=True)
    type1 = pd.read_csv(DATA / "ae_type1_provider_month.csv").set_index(keys, verify_integrity=True)
    assert all_depts.index.sort_values().equals(type1.index.sort_values())
    portfolio = all_depts[["Total A&E Attendances", "Total Over 4 Hours", "Admissions via A&E"]].join(
        type1[["Type 1 Attendances", "Type 1 Over 4 Hours"]])
    measures = list(MEASURES)[:5]
    portfolio.columns = measures
    monthly = pd.read_csv(DATA / "ae_monthly_summary.csv").set_index("Month", verify_integrity=True)
    with (ROOT / "docs/source-reconciliation.csv").open() as manifest:
        rows = list(csv.DictReader(manifest))
    assert [r["month"] for r in rows] == list(pd.date_range("2024-04-01", "2026-08-01", freq="MS").strftime("%Y-%m"))
    for r in rows:
        month = r["month"]
        path = directory / (month + ".csv")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == r["sha256"], f"Release differs: {month}"
        df = pd.read_csv(path)
        is_total = df[["Period", "Org Code", "Org name"]].apply(lambda col: col.str.strip().str.upper().eq("TOTAL")).any(axis=1)
        assert is_total.sum() == 1
        date = pd.Timestamp(month + "-01")
        period = f"MSITAE-{calendar.month_name[date.month].upper()}-{date.year}"
        assert set(df.loc[~is_total, "Period"].str.strip().str.upper()) == {period}
        for field, cols in MEASURES.items():
            counts = df[cols].apply(pd.to_numeric, errors="raise")
            assert counts.notna().all().all()
            df[field] = counts.sum(axis=1)
            expected = int(r[field if field.startswith("booked") else "official_" + field])
            assert df.loc[is_total, field].item() == df.loc[~is_total, field].sum() == expected
        source = df.loc[~is_total].set_index("Org Code", verify_integrity=True)[measures]
        processed = portfolio.loc[month + "-01"]
        assert len(source) == int(r["source_codes"]) and len(processed) == int(r["portfolio_codes"])
        assert sorted(processed.index.difference(source.index)) == r["only_portfolio"].split()
        assert sorted(source.index.difference(processed.index)) == r["only_source"].split()
        common = processed.index.intersection(source.index)
        assert (processed.loc[common] != source.loc[common]).any(axis=1).sum() == int(r["changed_common_codes"])
        for field in measures:
            assert processed[field].sum() - source[field].sum() == int(r["delta_portfolio_minus_source_" + field])
        assert list(processed.sum()[:3]) == list(monthly.loc[month + "-01", ["Attendances", "Over 4 Hours", "Admissions via A&E"]])
    print(f"Verified {len(rows)} pinned releases, their provider rows, total rows and portfolio differences.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    check(parser.parse_args().directory)
