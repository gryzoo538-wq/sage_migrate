# Changes report: phase 1 to final

Inputs applied: stocktake 2026-10-07 (6 codes), Hartley MAP update (5 supplier refs, effective 10 Oct), NHG-3003-S discontinued (inactive), FBA report of 2026-10-08.
Shopify and Amazon values are compared as read live after each push. Amazon values come from the verified feed files. Any field not listed did not change.

## Sage code (38 changes)

| Item | Field | Phase 1 | Final | Cause |
|---|---|---|---|---|
| NHG-1001-BLU | map | 22.99 | 24.99 | MAP update (Hartley, effective 10 Oct) |
| NHG-1001-BLU | shopify_price | 22.99 | 24.99 | MAP update (MAP now above gross) |
| NHG-1001-BLU | fba_fulfillable | 18 | 15 | FBA refresh (report of 2026-10-08) |
| NHG-1001-BLU | notes | MAP raised price (gross 18.00 -> MAP 22.99) | MAP raised price (gross 18.00 -> MAP 24.99) | derived from the changes above |
| NHG-1001-GRN | map | 22.99 | 24.99 | MAP update (Hartley, effective 10 Oct) |
| NHG-1001-GRN | shopify_price | 22.99 | 24.99 | MAP update (MAP now above gross) |
| NHG-1001-GRN | qty_in_stock | 11 | 9 | stocktake (counted figure replaces QTY_IN_STOCK) |
| NHG-1001-GRN | available | 11 | 9 | stocktake (counted 9) |
| NHG-1001-GRN | notes | MAP raised price (gross 18.00 -> MAP 22.99) | MAP raised price (gross 18.00 -> MAP 24.99) | derived from the changes above |
| NHG-1001-RED | map | 22.99 | 24.99 | MAP update (Hartley, effective 10 Oct) |
| NHG-1001-RED | shopify_price | 22.99 | 24.99 | MAP update (MAP now above gross) |
| NHG-1001-RED | notes | MAP raised price (gross 18.00 -> MAP 22.99); inactive: channel qty 0 | MAP raised price (gross 18.00 -> MAP 24.99); inactive: channel qty 0 | derived from the changes above |
| NHG-1002-S | map | 13.99 | 15.49 | MAP update (Hartley, effective 10 Oct) |
| NHG-1002-S | shopify_price | 13.99 | 15.49 | MAP update (MAP now above gross) |
| NHG-1002-S | fba_fulfillable | 0 | 12 | FBA refresh (report of 2026-10-08) |
| NHG-1002-S | notes | MAP raised price (gross 12.48 -> MAP 13.99); Shopify SKU 'nhg1002-s' fixed (normalised sku match) | MAP raised price (gross 12.48 -> MAP 15.49); Shopify SKU 'nhg1002-s' fixed (normalised sku match) | derived from the changes above |
| NHG-1004 | map | 14.99 | 16.99 | MAP update (Hartley, effective 10 Oct) |
| NHG-1004 | shopify_price | 14.99 | 16.99 | MAP update (MAP now above gross) |
| NHG-1004 | notes | MAP raised price (gross 13.44 -> MAP 14.99); Shopify SKU 'NHG 1004' fixed (normalised sku match) | MAP raised price (gross 13.44 -> MAP 16.99); Shopify SKU 'NHG 1004' fixed (normalised sku match) | derived from the changes above |
| NHG-2003 | qty_in_stock | 120 | 118 | stocktake (counted figure replaces QTY_IN_STOCK) |
| NHG-2003 | available | 120 | 118 | stocktake (counted 118) |
| NHG-3001 | qty_in_stock | 16 | 1 | stocktake (counted figure replaces QTY_IN_STOCK) |
| NHG-3001 | available | 14 | 0 | stocktake (counted 1) |
| NHG-3001 | notes | (blank) | over-allocated (allocated > in stock) | derived from the changes above |
| NHG-3002-GRY | qty_in_stock | 5 | 14 | stocktake (counted figure replaces QTY_IN_STOCK) |
| NHG-3002-GRY | available | 0 | 7 | stocktake (counted 14) |
| NHG-3002-GRY | fba_fulfillable | 22 | 20 | FBA refresh (report of 2026-10-08) |
| NHG-3002-GRY | notes | MAP raised price (gross 4.92 -> MAP 5.99); over-allocated (allocated > in stock) | MAP raised price (gross 4.92 -> MAP 5.99) | derived from the changes above |
| NHG-3003-S | active | 1 | 0 | discontinuation (NHG-3003-S) |
| NHG-3003-S | notes | (blank) | inactive: channel qty 0 | derived from the changes above |
| NHG-3003-L | fba_fulfillable | 9 | 0 | FBA refresh (report of 2026-10-08) |
| NHG-3005-M | fba_fulfillable | 31 | 28 | FBA refresh (report of 2026-10-08) |
| NHG-3008 | qty_in_stock | -2 | 15 | stocktake (counted figure replaces QTY_IN_STOCK) |
| NHG-3008 | available | 0 | 3 | stocktake (counted 15) |
| NHG-3008 | notes | negative stock in Sage; over-allocated (allocated > in stock) | (blank) | derived from the changes above |
| NHG-3009-2M | qty_in_stock | 3 | 2 | stocktake (counted figure replaces QTY_IN_STOCK) |
| NHG-3009-2M | available | 3 | 2 | stocktake (counted 2) |
| NHG-KIT-01 | available | 14 | 0 | knock-on: kit component NHG-3001 stocktake (counted 1, allocated 2, available 0) drives the kit to 0 |

## Shopify variant (13 changes)

| Item | Field | Phase 1 | Final | Cause |
|---|---|---|---|---|
| NHG-3009-2M (7478466587125) | inventory_quantity | 1 | 0 | stocktake (counted 2) |
| NHG-3002-GRY (7647269521150) | inventory_quantity | 0 | 5 | stocktake (counted 14) |
| NHG-1001-BLU (7138647298850) | price | 22.99 | 24.99 | MAP update |
| NHG-1001-GRN (7977078717789) | price | 22.99 | 24.99 | MAP update |
| NHG-1001-GRN (7977078717789) | inventory_quantity | 9 | 7 | stocktake (counted 9) |
| NHG-1001-RED (7941387867381) | price | 22.99 | 24.99 | MAP update |
| NHG-2003 (7348172876410) | inventory_quantity | 118 | 116 | stocktake (counted 118) |
| NHG-KIT-01 (7008550457600) | inventory_quantity | 12 | 0 | knock-on: kit component NHG-3001 stocktake (counted 1, allocated 2, available 0) drives the kit to 0 |
| NHG-1004 (7426252788255) | price | 14.99 | 16.99 | MAP update |
| NHG-1002-S (7557103970529) | price | 13.99 | 15.49 | MAP update |
| NHG-3003-S (7093004658745) | inventory_quantity | 24 | 0 | discontinuation (NHG-3003-S now inactive) |
| NHG-3008 (7988501357586) | inventory_quantity | 0 | 1 | stocktake (counted 15) |
| NHG-3001 (7245115304831) | inventory_quantity | 12 | 0 | stocktake (counted 1) |

## Shopify product (0 changes)

No changes.

## Amazon listing (26 changes)

| Item | Field | Phase 1 | Final | Cause |
|---|---|---|---|---|
| NHG-1001-BLU (NHG-1001-BLU) | price | 24.99 | 26.99 | MAP update (Amazon price/limits follow the Shopify price, MAP floor) |
| NHG-1001-BLU (NHG-1001-BLU) | minimum-seller-allowed-price | 22.99 | 24.99 | MAP update (Amazon price/limits follow the Shopify price, MAP floor) |
| NHG-1001-BLU (NHG-1001-BLU) | maximum-seller-allowed-price | 49.98 | 53.98 | MAP update (Amazon price/limits follow the Shopify price, MAP floor) |
| NHG-1001-BLU-FBA (NHG-1001-BLU) | price | 28.99 | 30.99 | MAP update (Amazon price/limits follow the Shopify price, MAP floor) |
| NHG-1001-BLU-FBA (NHG-1001-BLU) | minimum-seller-allowed-price | 22.99 | 24.99 | MAP update (Amazon price/limits follow the Shopify price, MAP floor) |
| NHG-1001-BLU-FBA (NHG-1001-BLU) | maximum-seller-allowed-price | 57.98 | 61.98 | MAP update (Amazon price/limits follow the Shopify price, MAP floor) |
| NHG-1001-GRN (NHG-1001-GRN) | price | 24.99 | 26.99 | MAP update (Amazon price/limits follow the Shopify price, MAP floor) |
| NHG-1001-GRN (NHG-1001-GRN) | minimum-seller-allowed-price | 22.99 | 24.99 | MAP update (Amazon price/limits follow the Shopify price, MAP floor) |
| NHG-1001-GRN (NHG-1001-GRN) | maximum-seller-allowed-price | 49.98 | 53.98 | MAP update (Amazon price/limits follow the Shopify price, MAP floor) |
| NHG-1001-GRN (NHG-1001-GRN) | quantity | 9 | 7 | stocktake (counted 9) |
| NHG-1001-RED (NHG-1001-RED) | price | 24.99 | 26.99 | MAP update (Amazon price/limits follow the Shopify price, MAP floor) |
| NHG-1001-RED (NHG-1001-RED) | minimum-seller-allowed-price | 22.99 | 24.99 | MAP update (Amazon price/limits follow the Shopify price, MAP floor) |
| NHG-1001-RED (NHG-1001-RED) | maximum-seller-allowed-price | 49.98 | 53.98 | MAP update (Amazon price/limits follow the Shopify price, MAP floor) |
| NHG-1002-S (NHG-1002-S) | price | 15.99 | 16.99 | MAP update (Amazon price/limits follow the Shopify price, MAP floor) |
| NHG-1002-S (NHG-1002-S) | minimum-seller-allowed-price | 13.99 | 15.49 | MAP update (Amazon price/limits follow the Shopify price, MAP floor) |
| NHG-1002-S (NHG-1002-S) | maximum-seller-allowed-price | 31.98 | 33.98 | MAP update (Amazon price/limits follow the Shopify price, MAP floor) |
| NHG-1002-S-FBA (NHG-1002-S) | price | 17.99 | 19.99 | MAP update (Amazon price/limits follow the Shopify price, MAP floor) |
| NHG-1002-S-FBA (NHG-1002-S) | minimum-seller-allowed-price | 13.99 | 15.49 | MAP update (Amazon price/limits follow the Shopify price, MAP floor) |
| NHG-1002-S-FBA (NHG-1002-S) | maximum-seller-allowed-price | 35.98 | 39.98 | MAP update (Amazon price/limits follow the Shopify price, MAP floor) |
| NHG-3003-S (NHG-3003-S) | quantity | 24 | 0 | discontinuation (NHG-3003-S now inactive) |
| NHG-KIT-01 (NHG-KIT-01) | quantity | 12 | 0 | knock-on: kit component NHG-3001 stocktake (counted 1, allocated 2, available 0) drives the kit to 0 |
| NHG-1001-BLU-FBA (NHG-1001-BLU) | fba_fulfillable (report only, not sent) | 18 | 15 | FBA refresh |
| NHG-1002-S-FBA (NHG-1002-S) | fba_fulfillable (report only, not sent) | 0 | 12 | FBA refresh |
| NHG-3002-GRY-FBA (NHG-3002-GRY) | fba_fulfillable (report only, not sent) | 22 | 20 | FBA refresh |
| NHG-3003-L-FBA (NHG-3003-L) | fba_fulfillable (report only, not sent) | 9 | 0 | FBA refresh |
| NHG-3005-M-FBA (NHG-3005-M) | fba_fulfillable (report only, not sent) | 31 | 28 | FBA refresh |

