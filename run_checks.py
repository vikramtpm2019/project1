# Load the CSVs into SQLite, run every check in checks.sql, write exceptions.csv.

import csv
import os
import sqlite3
import sys

base = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
con = sqlite3.connect(":memory:")

for table in ("contracts", "usage_events", "invoices"):
    with open(f"{base}/data/{table}.csv") as f:
        rows = list(csv.reader(f))
    cols = rows[0]
    con.execute(f"CREATE TABLE {table} ({', '.join(c + ' NUMERIC' if c in ('units','billed_units','billed_amount','included_units','overage_rate','monthly_fee') else c + ' TEXT' for c in cols)})")
    con.executemany(f"INSERT INTO {table} VALUES ({','.join('?' * len(cols))})", rows[1:])

sql = open(f"{base}/checks.sql").read()
statements = [s.strip() for s in sql.split(";") if "SELECT" in s]

out = []
for s in statements:
    out.extend(con.execute(s).fetchall())

with open(f"{base}/data/exceptions.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["check_name", "customer_id", "detail_date", "detail"])
    w.writerows(out)

for row in out:
    print(" | ".join(str(x) for x in row))
print(f"\n{len(out)} exceptions found")
