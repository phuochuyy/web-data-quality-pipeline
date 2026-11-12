# Web Data Quality Report

Generated: 2026-11-12 09:01 UTC · Overall: **✅ PASS** · 17 pass / 0 warn / 0 fail

## Quality checks

| Status | Table | Check | Dimension | Observed | Expected |
|---|---|---|---|---|---|
| ✅ PASS | raw_books | row_count | volume | 100 | >= 20 |
| ✅ PASS | raw_books | not_null:title | completeness | 0 missing (0.0%) | <= 1% missing |
| ✅ PASS | raw_books | not_null:url | completeness | 0 missing (0.0%) | <= 1% missing |
| ✅ PASS | raw_books | not_null:price_gbp | completeness | 0 missing (0.0%) | <= 1% missing |
| ✅ PASS | raw_books | not_null:rating | completeness | 0 missing (0.0%) | <= 1% missing |
| ✅ PASS | raw_books | unique:url | uniqueness | 0 duplicate rows | 0 |
| ✅ PASS | raw_books | price_positive | validity | 0 invalid rows | price_gbp > 0 |
| ✅ PASS | raw_books | rating_1_to_5 | validity | 0 invalid rows | 1..5 |
| ✅ PASS | raw_books | freshness | freshness | last scrape 0:00:28 ago | < 26h old |
| ✅ PASS | raw_books | row_count_vs_history | anomaly | 100 vs avg 100 (+0%) | within ±30% |
| ✅ PASS | raw_books | outliers:price_gbp | anomaly | 0 values with \|z\| > 3.0 | 0 |
| ✅ PASS | raw_quotes | row_count | volume | 50 | >= 10 |
| ✅ PASS | raw_quotes | not_null:text | completeness | 0 missing (0.0%) | <= 1% missing |
| ✅ PASS | raw_quotes | not_null:author | completeness | 0 missing (0.0%) | <= 1% missing |
| ✅ PASS | raw_quotes | unique:text, author | uniqueness | 0 duplicate rows | 0 |
| ✅ PASS | raw_quotes | freshness | freshness | last scrape 0:00:23 ago | < 26h old |
| ✅ PASS | raw_quotes | row_count_vs_history | anomaly | 50 vs avg 50 (+0%) | within ±30% |

## Latest data

- Books: **100** unique titles, avg price £34.56 (min £10.16, max £58.11), 100.0% in stock

### Books by rating

| Rating | Books |
|---|---|
| 1 | 22 |
| 2 | 19 |
| 3 | 22 |
| 4 | 18 |
| 5 | 19 |

### Top authors (quotes)

| Author | Quotes |
|---|---|
| Albert Einstein | 8 |
| J.K. Rowling | 6 |
| Marilyn Monroe | 6 |
| Bob Marley | 3 |
| Dr. Seuss | 3 |

### Top tags (quotes)

| Tag | Quotes |
|---|---|
| inspirational | 9 |
| love | 9 |
| life | 8 |
| humor | 5 |
| books | 4 |

## Recent loads

| Run | Source | Rows | Loaded at (UTC) |
|---|---|---|---|
| 20261112T090111Z | books | 100 | 2026-11-12 09:01 |
| 20261112T090111Z | quotes | 50 | 2026-11-12 09:01 |
| 20261112T090030Z | books | 100 | 2026-11-12 09:00 |
| 20261112T090030Z | quotes | 50 | 2026-11-12 09:00 |
