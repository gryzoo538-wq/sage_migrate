# Northfield Home & Garden: product data rules for Sage, Shopify and Amazon

Sage 50 is the system of record for stock codes, net sales prices, VAT codes, stock, weights and active status. Shopify is reached only through its API (mock_channels/). Amazon data comes from the report files, and updates go through the Feeds API.

## 1. Matching
- Shopify variant to Sage: compare SKUs after uppercasing and removing everything except letters and digits. If a variant has no SKU, match it by barcode.
- Amazon listing to Sage: strip a trailing `-FBA` and/or `-X<n>` (multipack of n) from the seller SKU and match as above. Listings with auto-generated SKUs are matched by their product-id (EAN) to the correct barcode of a Sage item.
- An Amazon listing that matches no Sage item is an **orphan**.
- If two Shopify products carry the same Sage item, the active product is the real one. Set the other product's status to `archived`.

## 2. Barcodes (EAN-13)
- A barcode is valid only if it is 13 digits with a correct check digit.
- The correct barcode for each Sage item: use the Sage barcode if it is valid, is not mangled (for example by scientific notation) and is not shared with another stock code. Otherwise use the Shopify barcode if valid, otherwise the Amazon product-id if valid. If two sources conflict, the valid barcode that is confirmed by a second source wins.
- List every Sage barcode that needs correcting in sage_updates.csv (STOCK_CODE, FIELD, OLD_VALUE, NEW_VALUE, SOURCE). Correct the Shopify barcode wherever it differs from the correct one.

## 3. Stock
- available = QTY_IN_STOCK − QTY_ALLOCATED, floored at 0. A negative QTY_IN_STOCK is reported as an exception.
- Kit NHG-KIT-01 = 1 × NHG-2001, 1 × NHG-2002, 1 × NHG-2003 and 1 × NHG-3001. Its available stock is the minimum of its components' available stock. Ignore Sage's own figure for the kit.
- Channel quantity = available − 2 (safety buffer), floored at 0. Multipack of n: floor((available − 2) ÷ n), floored at 0.
- Inactive Sage items (INACTIVE_FLAG = 1): Shopify quantity 0 and Amazon merchant-fulfilled quantity 0. If every variant of a Shopify product is inactive, set the product to `draft`.
- FBA listings: Amazon holds the stock. Never send a quantity for them. Report their fulfillable quantity from the FBA inventory report.

## 4. Prices (GBP)
- VAT: T1 = 20 %, T0 = 0 %. Gross = net × (1 + VAT), rounded half-up to 2 decimals.
- MAP (minimum advertised price, incl. VAT) comes from the supplier price lists (scanned), matched on SUPPLIER_PART_REF. "—" means no MAP.
- Shopify price = max(gross, MAP).
- Charm rounding: round **up** to the next price ending in .99 (x.00–x.99 → x.99).
- Amazon merchant-fulfilled, single unit: charm(Shopify price × 1.08).
- Amazon FBA: charm(Shopify price × 1.08 + FBA fee), with the fee taken from fba_fee_tiers.csv by Sage UNIT_WEIGHT (the first tier whose max_weight_kg ≥ the weight).
- Amazon multipack of n: charm(Shopify price × n × 0.92 × 1.08).
- minimum-seller-allowed-price: the MAP for single-unit listings that have one, otherwise the Shopify price. Leave it blank for multipacks. maximum-seller-allowed-price = 2 × the Amazon price.
- Orphans: send their current price from the All Listings report, quantity 0, and blank min/max.

## 5. Amazon feed rows
- handling-time 2 for merchant-fulfilled listings (fulfillment-channel DEFAULT).
- For FBA listings, leave quantity and handling-time blank, with fulfillment-channel AMAZON_EU.
- Every listing in the All Listings report gets exactly one row.

## 6. Shopify
- Each variant's SKU must equal its Sage STOCK_CODE exactly. Fix any that differ, including blanks.
- Set price, barcode and inventory at location 7001 as the rules above give.
- Variant grams = UNIT_WEIGHT × 1000 (report any mismatch; do not push grams).
