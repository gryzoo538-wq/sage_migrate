# Source audit (phase 1)

Sources: `sage_stock_export.csv` (32 stock codes), Shopify Admin API (24 products / 33 variants, read over 3 pages of `limit=10` via Link headers), `amazon_all_listings_report.txt` (30 listings), `amazon_fba_inventory_report.txt` (6 FBA rows), three supplier scans. Rules cited are sections of `channel_rules.md`.

## Sage 50 export

| # | Problem | Evidence | Resolution |
|---|---|---|---|
| S1 | Barcode destroyed by Excel (scientific notation) | `5.06012E+12` on NHG-1005, NHG-3002-SGE, NHG-3004, NHG-3011 (digits are unrecoverable from Sage) | Rule 2: mangled barcodes are not usable. Shopify's barcode is valid (check digit OK) and Amazon's product-id agrees for all four, so Shopify wins: 5060123400083, ...168, ...199, ...304. Sage correction listed in sage_updates.csv |
| S2 | Invalid check digit | NHG-1002-L Sage `5060123400055` (check digit should be 2). Shopify and Amazon both hold `5060123400052`, which is valid | Rule 2: Sage invalid, so Shopify barcode (confirmed by Amazon) used; Sage correction listed |
| S3 | Barcode shared by two stock codes | NHG-3006 and NHG-3007 both `5060123400243` | Rule 2: a shared barcode is disqualified for both. NHG-3006: Shopify `...243` is valid and Amazon agrees, so it stays `...243` (Sage value happens to be right, no Sage change). NHG-3007: Shopify blank, Amazon product-id `5060123400250` valid (listing 2M-ZK8W-05TJ and NHG-3007-X2), so `...250`; Sage correction listed |
| S4 | Negative stock | NHG-3008 QTY_IN_STOCK = -2, allocated 12 | Rule 3: available floored at 0, channel qty 0; exception reported |
| S5 | Over-allocated stock | NHG-3002-GRY in stock 5, allocated 7; NHG-3008 as above | available = 0 (floored); exception reported |
| S6 | Kit stock figure unusable | NHG-KIT-01 shows 0 in stock / 0 allocated, but components have stock | Rule 3: kit available = min(NHG-2001 130, NHG-2002 90, NHG-2003 120, NHG-3001 14) = 14 |
| S7 | Inactive item | NHG-1001-RED INACTIVE_FLAG = 1, 4 in stock; still has Shopify stock 35 and Amazon qty 25 (see below) | Rule 3: Shopify qty 0, Amazon MFN qty 0. Other variants of the product are active, so the product stays `active` |
| S8 | Truncated descriptions (30-char limit) | NHG-2005 "GROW YOUR OWN: A BEGINNER'S GU", NHG-3006 "SLATE PLANT LABELS (PACK OF 10" | Titles taken from Shopify instead |
| S9 | File format | CRLF line endings, descriptions upper-cased; no BOM or duplicate stock codes | Parsed with csv, all fields trimmed |
| S10 | Kit has no supplier part ref | NHG-KIT-01 SUPPLIER_A/C and SUPPLIER_PART_REF blank | No MAP; priced at gross |

Weights: no other problems. All stock codes have a weight and tax code.

## Shopify

| # | Problem | Evidence | Resolution |
|---|---|---|---|
| H1 | SKU format differences (5) | `nhg-2003`, `NHG 1004`, `nhg1002-s`, `NHG3005XL`, `NHG-3009-2m` | Rule 1/6: matched after normalising (upper-case, letters+digits only); SKU pushed as the exact Sage code |
| H2 | Blank SKU | Variant 7787581156926 (Hanging Bird Feeder, Large) has no SKU, barcode `5060123400182` | Rule 1: matched by barcode to NHG-3003-L (Sage and Amazon NHG-3003-L-FBA agree); SKU set to NHG-3003-L |
| H3 | Duplicate product | Products 7817656209959 (`active`, "Slate Plant Labels (Pack of 10)") and 7207485414573 (`draft`, "Slate Plant Labels - 10 Pack") both carry SKU NHG-3006 and barcode `...243` | Rule 1: the active product is the real one; the other is set to `archived`. Its values are left untouched |
| H4 | Invalid barcode | NHG-3005-L Shopify `5060123400222` (check digit should be 9). Sage `...229` is valid and unshared | Rule 2: Sage wins; Shopify corrected to `5060123400229` |
| H5 | Missing barcode | NHG-3007 variant 7638410713307 has an empty barcode | Set to `5060123400250` (see S3) |
| H6 | Prices out of line with Sage/MAP | e.g. NHG-1001-BLU 19.00, GRN 18.00, RED 17.50 (should all be 22.99 under the Hartley MAP); NHG-3004 29.80 vs MAP 34.99; NHG-1003 11.44 vs gross 11.94 | Rule 4: price = max(gross, MAP), all 32 variants set |
| H7 | Stock out of line with Sage | e.g. NHG-1001-RED 35 (inactive), NHG-3002-GRY 27 (Sage available 0), NHG-3008 12 (Sage -2), NHG-1005 3 vs 6 available | Rule 3: set from Sage |
| H8 | Inactive item selling | NHG-1001-RED active with stock 35 | Qty set to 0 |
| H9 | Weight mismatches | Compared grams with UNIT_WEIGHT x 1000 for every matched variant: none differ (the duplicate product also matches) | None to report |
| H10 | Shared barcode | Both NHG-3006 products carry the same barcode (the duplicate) | Resolved by archiving the duplicate |

Pagination note: 24 products across 3 pages (10/10/4); every variant belongs to a product that returned a Link-header page.

## Amazon (All Listings + FBA reports)

| # | Problem | Evidence | Resolution |
|---|---|---|---|
| A1 | Auto-generated seller SKUs (4) | `7K-QX2M-R4LD` (EAN ...069), `9B-HT4N-77PC` (...199), `2M-ZK8W-05TJ` (...250), `5R-LP3C-K9VE` (...304) | Rule 1: matched by product-id to the correct barcode of NHG-1003, NHG-3004, NHG-3007, NHG-3011 (this needs the corrected barcodes: Sage is mangled/shared for the last three) |
| A2 | Orphan listing | NHG-0999 "Wooden Dibber (Beech)", EAN 5060123499995 (valid), no Sage item | Rule 4: current price 4.99 sent, quantity 0, no min/max |
| A3 | Inactive item still selling | NHG-1001-RED merchant-fulfilled, qty 25 | Quantity 0 |
| A4 | Barcode conflict | NHG-1002-L listing carries `...052` while Sage has `...055` | See S2 |
| A5 | SKU suffixes | `-FBA` (6 listings), `-X3` (NHG-2001, 2002, 3006), `-X2` (NHG-3007) | Rule 1 parsing; pack size used for price/qty |
| A6 | Prices/limits wrong or missing | e.g. NHG-1001-BLU 19.80 vs rule 24.99; all listings lack min/max | Rules 4/5 applied to every listing |
| A7 | Report is a stale snapshot | The live listing API returned different values from the report before the first push (NHG-1001-BLU live 9.99 / qty 4 vs report 19.80 / qty 22) | The feed is generated from the rules, not from reported values (except the orphan price, which the rule takes from the report) |
| A8 | FBA quantities | FBA listings have blank quantity in the listings report; the FBA report holds fulfillable stock (18, 0, 5, 22, 9, 31) | Never sent; reported in master `fba_fulfillable` (NHG-1002-S-FBA is 0 fulfillable) |
| A9 | Sage items with no Amazon listing | 8 stock codes are not on Amazon | Not an error (nothing to push) |

## Supplier scans

All three scans were read visually. Oakfield (OAKF03) is rotated 90 degrees (read after rotating clockwise). Each scan has Trade ex VAT, RRP and MAP columns; only MAP is used, and "—" means no MAP. Details in supplier_map.csv (31 part refs; 18 with a MAP).
