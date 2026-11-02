# Iteration log

## Checker bug (before any model call)
My first number check flagged 17100 as "not in the source data" even though
it was. The cause: CSV commas were gluing neighboring numbers together
(18,17100 read as 1817100). Fix: treat CSV commas as separators.

## Spike check baseline (SQL)
The first spike check averaged each customer's usage including the spike
itself, so C005's planted ~10x day showed as 7.0x. Fix: the baseline is now
the average of the customer's other days (leave-one-out), and the output states
the baseline and excess. C005 now reads 17100 vs baseline 1928 (8.9x), excess
15171 units.

## Prompt v1 (simple)
Asked for: what happened, likely cause, action and owner, per exception.

Result: all 8 exceptions explained, but the checker flagged 6 numbers not in the
source data: 440, 2400, 8750, 14700, 73000, 108750.
- For C005 the model guessed a "normal" daily usage of 2400 and built three
  more numbers on it (14700, 440, 73000).
- For C001 it explained the 175 over-billing as overage and back-calculated
  8750 extra units. The data contradicts this: C001 used 96288 units against
  100000 included, so there was no overage. The model sounded sure and was wrong.

## Changes for v2
- Data side: SQL now supplies the baseline, excess, clean usage, included units
  and billed units, so the model has nothing to guess.
- Prompt side (`prompt_v2.md`): use only numbers in the data, do not compute or
  estimate, write "Cause not determined from this data" when the data does not
  show it, cite the field behind each statement, one owner role, a confidence
  level, and a fixed output format.

## Prompt v2 result
Checker: all 8 exceptions covered, no invented numbers.
- C001: now says overage is not supported (billed units 96288 are below
  included 100000) and points to invoice line items.
- C003: notes that usage does not explain the gap and nothing in the data shows
  a credit or discount.
- Known weakness: every exception is marked Low confidence, even where the data
  directly confirms the problem (for example a duplicate event ID). The prompt
  hedges the cause and the problem together.
