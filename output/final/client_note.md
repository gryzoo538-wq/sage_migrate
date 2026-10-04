Hi Ruth,

Thank you for the update. Everything in your 8 October email has been applied and pushed to Shopify and Amazon UK, and I checked both channels afterwards: every price, quantity, barcode, SKU and status matches the files.

**What changed**
- **Stocktake (7 Oct):** the counted figures replaced Sage's quantities for six codes. NHG-1001-GRN is now 9 (Amazon qty 7, Shopify 7), NHG-3002-GRY 14 (Shopify 5), NHG-3008 15 (Shopify 1), NHG-2003 118 (Shopify 116; not listed on Amazon), NHG-3009-2M 2 (Shopify 0) and NHG-3001 1.
- **NHG-3001 and the Herb Starter Kit:** NHG-3001 is counted at 1 but has 2 allocated, so none is available. That takes the Herb Starter Kit (NHG-KIT-01) to 0 on both channels, because it needs one of each component. Please check the allocation on NHG-3001.
- **Hartley MAP update (effective 10 Oct):** the Classic Watering Cans (Blue, Green, Red) are now £24.99 on Shopify and £26.99 on Amazon (FBA Blue £30.99). Bypass Secateurs Small is £15.49 on Shopify and £16.99 on Amazon (FBA £19.99). The Long-Handled Bulb Planter is £16.99 on Shopify (it isn't on Amazon). Amazon minimum prices follow the new MAPs.
- **NHG-3003-S (Small Hanging Bird Feeder):** treated as inactive, so its quantity is 0 on Shopify and Amazon. The product stays live because the Large size is still active.
- **FBA report (8 Oct):** loaded for reporting only. Amazon holds FBA stock, so no FBA quantities were sent.

**What was pushed:** 13 Shopify updates (prices and stock) and one Amazon feed (8 listings), all accepted with no errors.

**What needs your action in Sage**
1. Correct these barcodes (details in `sage_updates.csv`): NHG-1002-L to 5060123400052, NHG-1005 to 5060123400083, NHG-3002-SGE to 5060123400168, NHG-3004 to 5060123400199, NHG-3007 to 5060123400250 (it shared NHG-3006's barcode), and NHG-3011 to 5060123400304. Four were damaged by Excel (shown as 5.06012E+12), so please fix them in Sage itself rather than re-saving the export through Excel.
2. Check the NHG-3001 allocation (see above). Please also mark NHG-3003-S inactive in Sage, since the channels already treat it that way.
3. Decide what to do with the Amazon listing NHG-0999 "Wooden Dibber (Beech)", which has no Sage item. It is set to quantity 0 until you decide.
4. The duplicate Shopify product "Slate Plant Labels - 10 Pack" has been archived. You can delete it in Shopify if you like.

The full list of changes is in `changes_report.md`, and everything else that needs attention is in `exceptions_report.md`.

Kind regards
