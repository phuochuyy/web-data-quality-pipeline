# Web Data Quality Report

Generated: 2026-11-12 10:39 UTC · Overall: **⚠️ WARN** · 25 pass / 1 warn / 0 fail

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
| ✅ PASS | raw_books | freshness | freshness | last scrape 0:02:21 ago | < 26h old |
| ✅ PASS | raw_books | row_count_vs_history | anomaly | 100 vs avg 100 (+0%) | within ±30% |
| ✅ PASS | raw_books | outliers:price_gbp | anomaly | 0 values with \|z\| > 3.0 | 0 |
| ✅ PASS | raw_books | not_null:upc | completeness | 0 missing (0.0%) | <= 1% missing |
| ✅ PASS | raw_books | not_null:category | completeness | 0 missing (0.0%) | <= 1% missing |
| ✅ PASS | raw_books | not_null:stock_count | completeness | 0 missing (0.0%) | <= 1% missing |
| ✅ PASS | raw_books | one_upc_per_url | consistency | 100 urls, 100 upcs, 100 pairs | 1:1 |
| ✅ PASS | raw_books | price_listing_eq_detail | consistency | 0 invalid rows | listing price = detail price |
| ✅ PASS | raw_books | title_listing_eq_detail | consistency | 0 invalid rows | listing title = detail title |
| ✅ PASS | raw_books | in_stock_matches_stock_count | consistency | 0 invalid rows | in_stock = (stock_count > 0) |
| ✅ PASS | raw_books | stock_count_non_negative | validity | 0 invalid rows | stock_count >= 0 |
| ⚠️ WARN | raw_books | category_not_placeholder | validity | 14 invalid rows | real category |
| ✅ PASS | raw_quotes | row_count | volume | 50 | >= 10 |
| ✅ PASS | raw_quotes | not_null:text | completeness | 0 missing (0.0%) | <= 1% missing |
| ✅ PASS | raw_quotes | not_null:author | completeness | 0 missing (0.0%) | <= 1% missing |
| ✅ PASS | raw_quotes | unique:text, author | uniqueness | 0 duplicate rows | 0 |
| ✅ PASS | raw_quotes | freshness | freshness | last scrape 0:00:33 ago | < 26h old |
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

### Top categories (books)

| Category | Books | Units in stock | Avg price £ |
|---|---|---|---|
| Sequential Art | 14 | 227 | 31.91 |
| Nonfiction | 12 | 198 | 32.48 |
| Default | 9 | 163 | 26.85 |
| Poetry | 7 | 129 | 36.24 |
| Add a comment | 5 | 80 | 30.34 |

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
| 20261112T103644Z | books | 100 | 2026-11-12 10:38 |
| 20261112T103644Z | quotes | 50 | 2026-11-12 10:38 |
| 20261112T090111Z | books | 100 | 2026-11-12 09:01 |
| 20261112T090111Z | quotes | 50 | 2026-11-12 09:01 |
| 20261112T090030Z | books | 100 | 2026-11-12 09:00 |
| 20261112T090030Z | quotes | 50 | 2026-11-12 09:00 |
