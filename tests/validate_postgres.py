"""Run against a disposable local PostgreSQL DB using libpq PG* settings."""
import io
from pathlib import Path

import pandas as pd
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "sql"
DATA = ROOT / "data/processed"
TOL = 1e-9


def load(cursor, table, columns):
    rows = pd.read_csv(DATA / (table + ".csv"))
    subset = rows[list(columns)].rename(columns=columns)
    definitions = ["month date", "org_code text"] + [c + " bigint" for c in subset.columns[2:]]
    cursor.execute(f"CREATE TEMP TABLE {table} ({', '.join(definitions)}, PRIMARY KEY(month, org_code))")
    buffer = io.StringIO()
    subset.to_csv(buffer, index=False, header=False)
    buffer.seek(0)
    cursor.copy_expert(f"COPY {table} FROM STDIN WITH CSV", buffer)
    subset.columns = ["month", "code", "volume", "over4"]
    return subset


def reference(data, minimum):
    stats = data.groupby("code").agg(months=("month", "size"), volume=("volume", "sum"), over4=("over4", "sum"))
    stats = stats[stats.months >= minimum].copy()
    stats["mean_volume"] = stats.volume / stats.months
    stats["performance"] = 100 * (1 - stats.over4 / stats.volume)
    return stats


def verify(cursor, frames, start, end, minimum):
    active = {k: df[df.month.between(start, end) & (df.volume > 0)] for k, df in frames.items()}
    keys = active["all"][["month", "code"]].merge(active["type1"][["month", "code"]], validate="one_to_one")
    cohorts = dict(active)
    for k, df in active.items():
        cohorts["matched_" + k] = df.merge(keys, validate="one_to_one")
    for name, rows in cohorts.items():
        ref = reference(rows, minimum)
        cursor.execute("""SELECT org_code, months, attendances, breaches, mean_volume, performance_pct
                          FROM pg_temp.provider_metrics(%s,%s,%s) WHERE cohort=%s
                          ORDER BY attendances DESC, org_code""", (start, end, minimum, name))
        actual = cursor.fetchall()
        ordered = ref.reset_index().sort_values(["volume", "code"], ascending=[False, True])
        assert [r[0] for r in actual] == list(ordered.code)
        for (_, months, volume, over4, mean, pct), row in zip(actual, ordered.itertuples()):
            assert (months, volume, over4) == (row.months, row.volume, row.over4)
            assert abs(float(mean)-row.mean_volume) < TOL and abs(float(pct)-row.performance) < TOL
        cursor.execute("""SELECT corr(mean_volume,performance_pct) FROM pg_temp.provider_metrics(%s,%s,%s)
                          WHERE cohort=%s""", (start, end, minimum, name))
        r = cursor.fetchone()[0]
        assert abs(r-ref.mean_volume.corr(ref.performance)) < TOL
        print(start, end, name, len(ref), sum(ref.months), f"{r:.9f}")
        if name == "type1":
            print("Top 10:", " ".join(ordered.code.head(10)))


def statements(path):
    # These reporting files contain simple SELECT statements. Ignore line comments.
    sql = "\n".join(line for line in path.read_text().splitlines() if not line.lstrip().startswith("--"))
    return [s for s in sql.split(";") if s.strip()]


def main():
    with psycopg2.connect("") as db, db.cursor() as cur:
        cur.execute("SELECT version()")
        print(cur.fetchone()[0])
        base = {"Month": "month", "Org Code": "org_code"}
        a = load(cur, "ae_provider_month", {**base, "Total A&E Attendances": "total_ae_attendances",
                                           "Total Over 4 Hours": "total_over_four_hours"})
        t = load(cur, "ae_type1_provider_month", {**base, "Type 1 Attendances": "type_1_attendances",
                                                 "Type 1 Over 4 Hours": "type_1_over_four_hours"})
        ranking, correlation = statements(SQL / "04_provider_analysis.sql")
        cur.execute(ranking)
        rows = cur.fetchall()
        ref = reference(a[a.volume > 0], 1).reset_index().sort_values(["volume", "code"], ascending=[False, True])
        assert [(r[0], r[1]) for r in rows] == list(zip(ref.code.head(10), ref.volume.head(10)))
        cur.execute(correlation)
        count, r = cur.fetchone()
        assert count == 121 and abs(r-0.03778078860917567) < TOL
        cur.execute((SQL / "05_period_cohorts.sql").read_text())
        summary, top = statements(SQL / "06_provider_benchmarks.sql")
        cur.execute(summary)
        metrics = cur.fetchall()
        assert [(name, n, months) for name, n, months, _ in metrics] == [
            ("all", 180, 5174), ("matched_all", 121, 3507), ("matched_type1", 121, 3507), ("type1", 121, 3507)]
        cur.execute(top)
        assert [r[0] for r in cur.fetchall()] == "RRK RAJ RM3 RYR R0A R1H RAL RDU RWE RTG".split()
        for start, end, months in [("2024-04-01", "2026-08-01", 24), ("2024-04-01", "2024-04-01", 1)]:
            verify(cur, {"all": a, "type1": t}, start, end, months)


if __name__ == "__main__":
    main()
