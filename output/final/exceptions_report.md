# Exceptions report

Everything below needs the client's attention.

## 1. Orphans (no Sage item)

| Channel | Identifier | Title | Barcode | Action taken |
|---|---|---|---|---|
| amazon | NHG-0999 | Wooden Dibber (Beech) | 5060123499995 | Amazon: current price kept, quantity 0, no min/max |

Client decision: create a Sage record or remove the listing.

## 2. Inactive items

| Stock code | Title | Variant | In stock | Action taken |
|---|---|---|---|---|
| NHG-1001-RED | Classic Watering Can 9L | Red | 4 | Shopify qty 0, Amazon MFN qty 0; product stays active (other variants live) |
| NHG-3003-S | Hanging Bird Feeder | Small | 26 | Shopify qty 0, Amazon MFN qty 0; product stays active (other variants live) |

## 3. Stock problems

| Stock code | In stock | Allocated | Available | Issue |
|---|---|---|---|---|
| NHG-3001 | 1 | 2 | 0 | allocated exceeds stock (available floored to 0) |
| NHG-KIT-01 | 0 | 0 | 0 | kit: Sage shows 0, computed available 0 from components |

## 4. Sage barcode corrections (see sage_updates.csv)

| Stock code | Old | New | Source |
|---|---|---|---|
| NHG-1002-L | 5060123400055 | 5060123400052 | shopify (invalid check digit) |
| NHG-1005 | 5.06012E+12 | 5060123400083 | shopify (damaged (scientific notation)) |
| NHG-3002-SGE | 5.06012E+12 | 5060123400168 | shopify (damaged (scientific notation)) |
| NHG-3004 | 5.06012E+12 | 5060123400199 | shopify (damaged (scientific notation)) |
| NHG-3007 | 5060123400243 | 5060123400250 | amazon (shared with another stock code) |
| NHG-3011 | 5.06012E+12 | 5060123400304 | shopify (damaged (scientific notation)) |

Shopify barcodes corrected live: NHG-3007 (blank -> 5060123400250), NHG-3005-L (5060123400222 -> 5060123400229)

## 5. Duplicate Shopify product

| Product id | Variant id | Sage code | Status before | Status now |
|---|---|---|---|---|
| 7207485414573 | 7405677289514 | NHG-3006 | draft | archived |

The `active` product carries the real item; the other is set to `archived`. Its price/barcode/stock were not touched.

## 6. Weight mismatches (Shopify grams vs Sage UNIT_WEIGHT x 1000; grams not pushed)

None found: every matched Shopify variant's grams equals Sage UNIT_WEIGHT x 1000.

## 7. Other points

- Variants whose Shopify SKU differed from the Sage code (fixed live): NHG-3009-2M ('NHG-3009-2m'), NHG-2003 ('nhg-2003'), NHG-1004 ('NHG 1004'), NHG-3005-XL ('NHG3005XL'), NHG-1002-S ('nhg1002-s'), NHG-3003-L ('blank').
- Auto-generated Amazon SKUs matched by EAN: 7K-QX2M-R4LD→NHG-1003, 9B-HT4N-77PC→NHG-3004, 2M-ZK8W-05TJ→NHG-3007, 5R-LP3C-K9VE→NHG-3011.
- Items with no MAP (priced at gross): NHG-1003, NHG-2004, NHG-3001, NHG-3003-S, NHG-3003-L, NHG-3005-S, NHG-3005-M, NHG-3005-L, NHG-3005-XL, NHG-3007, NHG-3008, NHG-3010, NHG-3011, NHG-KIT-01.
- NHG-KIT-01 has no supplier part reference; no MAP.
