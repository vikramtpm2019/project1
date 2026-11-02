# Generate synthetic contracts, usage events and invoices for September 2026.
#
# Everything here is made up. Anomalies are planted on purpose so we can check
# that the SQL finds every one of them (see ANSWER_KEY at the bottom).
 
import csv
import random
from datetime import date, timedelta

random.seed(42)
import os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT, exist_ok=True)

PERIOD_START, PERIOD_END = date(2026, 9, 1), date(2026, 9, 30)

# customer_id, name, included_units, unit_overage_rate, monthly_fee, contract_end
contracts = [
    ("C001", "North Labs",   100000, 0.020, 2500, "2027-03-31"),
    ("C002", "Bird Retail",   50000, 0.025, 1500, "2027-06-30"),
    ("C003", "Cedar Health",     200000, 0.015, 4200, "2027-01-31"),
    ("C004", "Delta Freight",     80000, 0.020, 2000, "2026-09-15"),  # ends mid-period
    ("C005", "Ever Media",    60000, 0.030, 1800, "2027-09-30"),
    ("C006", "Fox Bank",    150000, 0.018, 3600, "2027-02-28"),
    ("C007", "Granite Systems",   40000, 0.025, 1200, "2027-04-30"),
    ("C008", "Harbor Tiles",      70000, 0.022, 1900, "2027-08-31"),
]

with open(f"{OUT}/contracts.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["customer_id", "customer_name", "included_units",
                "overage_rate", "monthly_fee", "contract_end"])
    w.writerows(contracts)

# Daily usage per customer, around a typical daily volume.
typical_daily = {"C001": 3200, "C002": 1500, "C003": 6400, "C004": 2500,
                 "C005": 1900, "C006": 4800, "C007": 1200, "C008": 2300}

events = []
n = 0
d = PERIOD_START
while d <= PERIOD_END:
    for cust, base in typical_daily.items():
        n += 1
        units = int(random.gauss(base, base * 0.08))
        events.append([f"E{n:05d}", cust, d.isoformat(), units, "meter"])
    d += timedelta(days=1)

# ---- planted anomalies --------------------------------------------------
# 1. Duplicate event (same event_id loaded twice) for C002 on Sep 10
dup = next(e for e in events if e[1] == "C002" and e[2] == "2026-09-10")
events.append(list(dup))
# 2. Spike: C005 on Sep 18 is ~10x normal
for e in events:
    if e[1] == "C005" and e[2] == "2026-09-18":
        e[3] = e[3] * 10
# 3. Usage after contract end: C004 keeps sending usage after Sep 15 (already in
#    the loop above, since we generate all 30 days)
# 4. Negative units: C007 on Sep 22
for e in events:
    if e[1] == "C007" and e[2] == "2026-09-22":
        e[3] = -900
# 5. Gap: C006 has no usage Sep 12-14
events = [e for e in events
          if not (e[1] == "C006" and "2026-09-12" <= e[2] <= "2026-09-14")]
# 6. Usage with no contract: unknown customer C099
for day in ("2026-09-05", "2026-09-06", "2026-09-07"):
    n += 1
    events.append([f"E{n:05d}", "C099", day, 1800, "meter"])

with open(f"{OUT}/usage_events.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["event_id", "customer_id", "usage_date", "units", "source"])
    w.writerows(events)

# ---- invoices: computed correctly, then two deliberately wrong -----------
seen = set()
totals = {}
for eid, cust, day, units, src in events:
    if eid in seen:
        continue  # a correct invoice would not count the duplicate
    seen.add(eid)
    totals[cust] = totals.get(cust, 0) + units

invoices = []
for cust, name, incl, rate, fee, end in contracts:
    units = totals.get(cust, 0)
    # correct billing: only count usage up to the contract end date
    if end < PERIOD_END.isoformat():
        counted, units = set(), 0
        for e in events:
            if e[1] == cust and e[2] <= end and e[0] not in counted:
                counted.add(e[0])
                units += e[3]
    overage = max(0, units - incl)
    amount = round(fee + overage * rate, 2)
    invoices.append([f"INV-{cust}-202609", cust, "2026-09", units, amount])

# Planted billing errors
for inv in invoices:
    if inv[1] == "C003":
        inv[4] = round(inv[4] - 380.00, 2)       # under-billed
    if inv[1] == "C001":
        inv[4] = round(inv[4] * 1.07, 2)         # over-billed by 7%

with open(f"{OUT}/invoices.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["invoice_id", "customer_id", "period", "billed_units",
                "billed_amount"])
    w.writerows(invoices)

ANSWER_KEY = """
Planted anomalies (the SQL must find all of these):
 1. Duplicate event       C002  Sep 10
 2. Usage spike (~10x)    C005  Sep 18
 3. Usage after end       C004  after 2026-09-15
 4. Negative units        C007  Sep 22
 5. Missing days          C006  Sep 12-14
 6. No contract           C099  Sep 5-7
 7. Under-billed invoice  C003  (-380.00)
 8. Over-billed invoice   C001  (+7%)
"""
with open(f"{OUT}/ANSWER_KEY.txt", "w") as f:
    f.write(ANSWER_KEY)
print(f"events={len(events)} invoices={len(invoices)}")
