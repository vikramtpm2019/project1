-- Exception checks for usage-to-invoice review (SQLite syntax).
-- Tables loaded by run_checks.py: contracts, usage_events, invoices

-- CHECK 1: duplicate events (same event_id loaded more than once)
SELECT 'DUPLICATE_EVENT' AS check_name, customer_id, usage_date AS detail_date,
       'event ' || event_id || ' appears ' || COUNT(*) || ' times' AS detail
FROM usage_events
GROUP BY event_id, customer_id, usage_date
HAVING COUNT(*) > 1;

-- CHECK 2: usage for a customer with no contract
SELECT 'NO_CONTRACT', u.customer_id, MIN(u.usage_date),
       SUM(u.units) || ' units on ' || COUNT(*) || ' days, no contract on file'
FROM usage_events u
LEFT JOIN contracts c ON c.customer_id = u.customer_id
WHERE c.customer_id IS NULL
GROUP BY u.customer_id;

-- CHECK 3: usage dated after the contract ended
SELECT 'USAGE_AFTER_END', u.customer_id, MIN(u.usage_date),
       COUNT(*) || ' days of usage after ' || c.contract_end
FROM usage_events u
JOIN contracts c ON c.customer_id = u.customer_id
WHERE u.usage_date > c.contract_end
GROUP BY u.customer_id, c.contract_end;

-- CHECK 4: negative or zero units
SELECT 'NEGATIVE_UNITS', customer_id, usage_date, 'units = ' || units
FROM usage_events
WHERE units <= 0;

-- CHECK 5: spikes, using a window function for each customer's median-ish baseline
-- Baseline = average of the customer's OTHER days (leave-one-out), so the spike
-- itself cannot inflate its own baseline. The detail states the baseline and the
-- excess, so nobody downstream has to guess "normal" usage.
WITH daily AS (
    SELECT customer_id, usage_date, units,
           (SUM(units) OVER (PARTITION BY customer_id) - units) * 1.0 /
           (COUNT(*) OVER (PARTITION BY customer_id) - 1) AS baseline
    FROM (SELECT DISTINCT event_id, customer_id, usage_date, units FROM usage_events)
    WHERE units > 0
)
SELECT 'SPIKE', customer_id, usage_date,
       units || ' units vs baseline ' || CAST(baseline AS INT) ||
       ' (' || ROUND(units * 1.0 / baseline, 1) || 'x), excess ' ||
       CAST(units - baseline AS INT) || ' units'
FROM daily
WHERE units > 3 * baseline;

-- CHECK 6: missing days (gaps between consecutive usage dates), using LAG
WITH dated AS (
    SELECT DISTINCT customer_id, usage_date FROM usage_events
),
gaps AS (
    SELECT customer_id, usage_date,
           LAG(usage_date) OVER (PARTITION BY customer_id ORDER BY usage_date) AS prev_date
    FROM dated
)
SELECT 'MISSING_DAYS', customer_id, prev_date,
       CAST(julianday(usage_date) - julianday(prev_date) - 1 AS INT) ||
       ' missing day(s) between ' || prev_date || ' and ' || usage_date
FROM gaps
WHERE prev_date IS NOT NULL
  AND julianday(usage_date) - julianday(prev_date) > 1;

-- CHECK 7: invoice does not match recomputed amount from contract terms
WITH clean_usage AS (
    SELECT u.customer_id, SUM(u.units) AS units
    FROM (SELECT DISTINCT event_id, customer_id, usage_date, units FROM usage_events) u
    JOIN contracts c ON c.customer_id = u.customer_id
    WHERE u.usage_date <= c.contract_end AND u.units > 0
    GROUP BY u.customer_id
),
expected AS (
    SELECT c.customer_id, cu.units AS clean_units, c.included_units,
           c.monthly_fee +
           MAX(0, cu.units - c.included_units) * c.overage_rate AS expected_amount
    FROM contracts c
    JOIN clean_usage cu ON cu.customer_id = c.customer_id
)
SELECT 'INVOICE_MISMATCH', i.customer_id, i.period,
       'billed ' || i.billed_amount || ' vs expected ' || ROUND(e.expected_amount, 2) ||
       ' (diff ' || ROUND(i.billed_amount - e.expected_amount, 2) || '), clean usage ' ||
       e.clean_units || ' units vs ' || e.included_units || ' included, billed units ' ||
       i.billed_units
FROM invoices i
JOIN expected e ON e.customer_id = i.customer_id
WHERE ABS(i.billed_amount - e.expected_amount) > 1.00;
