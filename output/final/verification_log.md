# Verification log

Run after the final push, 2026-10-08 data set. Live state = mock Shopify and Amazon APIs read over HTTP.

## Checks performed

| # | Check | Method | Result |
|---|---|---|---|
| 1 | Supplier MAPs | Re-opened all three scans (Hartley and Greensprout at 220 dpi; Oakfield rotated 90 degrees and zoomed) and the Hartley MAP update at 250 dpi. Transcribed the MAP column a second time, separately from supplier_map.csv, into `independent_check.py` and compared | All 31 part refs match, including the "no MAP" entries. Trade and RRP columns were never used. The 5 updated Hartley MAPs match the update scan |
| 2 | Barcode check digits | Every master `correct_barcode` (32), every Sage / Shopify / Amazon barcode involved, using a separate EAN-13 implementation (mod-10 on the digit sums) | 32 of 32 valid and unique. Invalid in the sources: Sage NHG-1002-L ...055, Shopify NHG-3005-L ...222, four Sage values in scientific notation, and the NHG-3006/3007 shared barcode. All corrected |
| 3 | Prices and quantities recomputed from the rules | `sync/independent_check.py`: does not import rules.py or build.py; exact Fraction arithmetic, its own charm, tier, pack and kit logic. Compared master (gross, MAP, Shopify price, barcode, available, active, FBA fulfillable), all 30 feed rows, crosswalk codes, sage_updates | phase1: 334 checks, 0 mismatches. final: 617 checks, 0 mismatches |
| 4 | Sensitivity of check 3 | Mutation test: changed one MAP (OGS-RB-1) in a copy of the checker | The checker reported 3 mismatches, so it can fail |
| 5 | Live Shopify vs final files | `sync/live_check.py` re-reads all 24 products / 33 variants via the paginated API: SKU, price, barcode, inventory, product status | 152 checks, 0 mismatches |
| 6 | Live Amazon vs final feed | `GET /sp/listings/{sku}` for all 30 listings: price, min, max, quantity, channel | 150 checks, 0 mismatches. FBA listings have quantity null (never sent) |
| 7 | Live state again, independently | `independent_check.py final --live` reads the live APIs with its own HTTP code and compares to its own expected values | 617 checks, 0 mismatches |
| 8 | Unit tests | `python3 -m unittest discover sync/tests` | 29 tests, OK |

## Mismatches found along the way and what changed

| Stage | Mismatch / error | Cause | Fix |
|---|---|---|---|
| First push | 31 Shopify inventory calls returned HTTP 422 "location_id and a valid inventory_item_id are required" | My client sent inventory_item_id as a string (read from the CSV) | shopify.py now casts ids to integers; added a unit test (`test_inventory_ids_sent_as_integers`); re-pushed, 0 rejections |
| First push | 30 HTTP 429 responses during phase 1 and 3 in the final push | Rate limit (4 calls/s) | Handled by the client: waits Retry-After and retries; every call is in push_log.csv |
| First push | Amazon feed F50000 (30 rows) | Report: processed 30, successful 30, errors 0 | No row errors. Final feed F50001 (8 changed rows): also 0 errors |
| Live check | 6 mismatches on FBA listings (channel) | My check expected "FBA", the API labels it "AFN" | Corrected the check; FBA quantity is now checked to be null |
| Unit tests | 1 failure | Header name case differs in urllib (X-amz-access-token) | Made the test case-insensitive |
| Final build | Provenance changed when I first rebuilt from the already-corrected live Shopify state (barcode source for NHG-3007 flipped amazon to shopify; crosswalk methods turned into plain "sku"; exceptions listed no fixes) | build.py took identity and "current" values from one pull | build.py now takes the original pull for matching and provenance and the later live pull only for the current values; rebuilt, reran every check |
| Reports | changes_report.md showed a zero quantity as "(blank)" | Falsy-value formatting | Fixed and regenerated |
| Documents | source_audit.md first said 17 supplier MAPs and 14 codes not on Amazon | Miscount | Corrected to 18 and 8 |
| Client note | Said NHG-2003 was also changed on Amazon | It has no Amazon listing | Corrected |

No unresolved mismatch remains.

## Final live-check result

- Shopify: 24 products (23 active, 1 archived duplicate), 33 variants. 152 checks, 0 mismatches.
- Amazon UK: 30 listings (19 merchant-fulfilled single, 4 multipacks, 6 FBA, 1 orphan). 150 checks, 0 mismatches.
- Final live Shopify units: 736. Amazon merchant-fulfilled quantity: 546 packs/units (FBA not sent; 80 units fulfillable at Amazon per the 8 Oct report).

## Test output

```
test_submit_poll_report_errors (test_clients.Feeds.test_submit_poll_report_errors) ... ok
test_summary_errors_never_swallowed (test_clients.Feeds.test_summary_errors_never_swallowed) ... ok
test_follows_all_pages (test_clients.Pagination.test_follows_all_pages) ... ok
test_link_header_parsing (test_clients.Pagination.test_link_header_parsing) ... ok
test_422_reported_clearly (test_clients.Retry429.test_422_reported_clearly) ... ok
test_gives_up (test_clients.Retry429.test_gives_up) ... ok
test_honours_retry_after_then_succeeds (test_clients.Retry429.test_honours_retry_after_then_succeeds) ... ok
test_inventory_ids_sent_as_integers (test_clients.Retry429.test_inventory_ids_sent_as_integers) ... ok
test_just_above_x99 (test_rules.Charm.test_just_above_x99) ... ok
test_mid_and_small (test_rules.Charm.test_mid_and_small) ... ok
test_x00_goes_to_x99 (test_rules.Charm.test_x00_goes_to_x99) ... ok
test_x995_goes_up_to_next (test_rules.Charm.test_x995_goes_up_to_next) ... ok
test_x99_stays (test_rules.Charm.test_x99_stays) ... ok
test_check_digit_calc (test_rules.CheckDigit.test_check_digit_calc) ... ok
test_damaged_and_wrong_length (test_rules.CheckDigit.test_damaged_and_wrong_length) ... ok
test_invalid_check_digit (test_rules.CheckDigit.test_invalid_check_digit) ... ok
test_mangled_detection (test_rules.CheckDigit.test_mangled_detection) ... ok
test_valid (test_rules.CheckDigit.test_valid) ... ok
test_fba (test_rules.Prices.test_fba) ... ok
test_fee_tiers_boundaries (test_rules.Prices.test_fee_tiers_boundaries) ... ok
test_gross_half_up (test_rules.Prices.test_gross_half_up) ... ok
test_limits (test_rules.Prices.test_limits) ... ok
test_multipack (test_rules.Prices.test_multipack) ... ok
test_shopify_price_map (test_rules.Prices.test_shopify_price_map) ... ok
test_single_amazon (test_rules.Prices.test_single_amazon) ... ok
test_available_floor (test_rules.Stock.test_available_floor) ... ok
test_channel_qty (test_rules.Stock.test_channel_qty) ... ok
test_kit (test_rules.Stock.test_kit) ... ok
test_sku_parsing (test_rules.Stock.test_sku_parsing) ... ok
----------------------------------------------------------------------
Ran 29 tests in 1.028s
OK
```
