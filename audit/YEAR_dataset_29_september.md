# The year dataset, 29 September 2026

CLAUDE.md fault 8 said the test data covered July and August 2026 only, so nothing tested
behaviour across many months or across the British Summer Time boundary. This closes it.

## What was built

- `testdata/generate_payloads.py` gained a year mode. With `MSE_TESTDATA_YEAR=1` it adds two
  orders a month from October 2025 to July 2026 and six orders placed where the UTC date and
  the London date differ, at both 2025 and 2026 clock changes and at two month ends, and writes
  to `payloads_year/`. Without the flag its output is byte for byte what it was, which was
  checked by regenerating `payloads/` and `rows.json` and finding no difference.
- `testdata/ingest.py` reads `MSE_PAYLOADS` and writes `MSE_ROWS` when they are set.
- `testdata/load_rows.py` loads a rows file into a database. Nothing did before: `seed.sql`
  was edited by hand and QA fault 6 found it does not load. Loading the ordinary `rows.json`
  into a database built from empty gave 119 ledger entries summing to -£318.24, with 88
  settlement months, the same as the local copy of development.
- `testdata/year_check.py` runs the checks below. It needs a database, so it is not in CI.

The development branch on Neon was not reloaded, because its ledger is append-only and
reloading it needs the owner's approval.

## The run

Against a database built from empty by `migrate.py` and loaded with `rows_year.json`
(46 orders, 13 statements, 233 ledger entries):

```
PASS YBSTEND1: sale dated 2025-10-26 in London, expected 2025-10-26
PASS YBSTEND2: sale dated 2025-10-26 in London, expected 2025-10-26
PASS YOCTEND: sale dated 2025-10-31 in London, expected 2025-10-31
PASS YBSTSTART1: sale dated 2026-03-28 in London, expected 2026-03-28
PASS YBSTSTART2: sale dated 2026-03-30 in London, expected 2026-03-30
PASS YMAREND: sale dated 2026-04-01 in London, expected 2026-04-01
PASS A10: sale dated 2026-08-01 in London, expected 2026-08-01
PASS A11: sale dated 2026-07-31 in London, expected 2026-07-31
PASS the ingester's month agrees with the database's day on all 233 entries
PASS the statement stamped 23:30 UTC on 31 March settles in [(datetime.date(2026, 4, 1),)]
PASS sales basis gross sales: twelve months sum to 197500, the year reads 197500
PASS sales basis net proceeds: twelve months sum to 152493, the year reads 152493
PASS sales basis: kept is unknown in the 9 months with sales before any cost took effect
PASS sales basis: kept is known from July, when the costs took effect
FAIL sales basis: the year's kept is unknown too, rather than a figure that leaves goods out
PASS sales basis: 11 of twelve months hold sales
PASS cash basis gross sales: twelve months sum to 193500, the year reads 193500
PASS cash basis net proceeds: twelve months sum to 148793, the year reads 148793
PASS cash basis: kept is unknown in the 8 months with sales before any cost took effect
PASS cash basis: kept is known from July, when the costs took effect
FAIL cash basis: the year's kept is unknown too, rather than a figure that leaves goods out
PASS cash basis: 10 of twelve months hold sales
20 passed, 2 failed
```

## What passed

Every order placed where UTC and London disagree carries the London date: the two orders
either side of the October clock change both fall on 26 October, 23:30 UTC on 31 October stays
in October because October ends on GMT, and 23:30 UTC on 31 March is 1 April because March ends
on BST. The ingester's month, worked out in Python, agrees with the database's day on all 233
entries. A statement stamped 23:30 UTC on 31 March settles in April. On both bases the twelve
monthly figures for gross sales and net proceeds sum exactly to the year's.

## The finding

Every cost in the dataset takes effect on 1 July 2026. For each month before July the Money
screen's arithmetic says kept is unknown, because the units sold then had no cost in force.
For the year as a whole it gives kept as a figure. The reason is the rule the owner approved
on 28 September: the cost used for a period is the one in force at the period's end. Over a
single month that is close to the cost at the time of sale. Over a year it applies the July
cost to units sold the previous October, before that cost existed.

Two consequences follow. The twelve monthly kept bars on S11 and on the trends cannot sum to the
year's kept figure, which DSH-7 requires. The tax-year set-aside of A30.3 reads kept over the
tax year to date through the same arithmetic, so its profit carries today's cost for every
unit sold since April.

The alternative is the cost in force on the date each unit sold, which is what
`checkReturnItem` already uses for a write-off (A30.2). With it, a month and a year cannot
disagree. Changing the rule is a ruling for the owner, so nothing was changed, and the two
failing checks stay failing until it is made.
