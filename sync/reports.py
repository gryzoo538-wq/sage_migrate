"""Generate exceptions_report.md and channel_summary.md from a build directory (master, crosswalk, feed, shopify updates)."""
import csv
import os
import sys
from decimal import Decimal as D

sys.path.insert(0, os.path.dirname(__file__))
import rules  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rd(path, **kw):
    with open(path, newline="") as f:
        return list(csv.DictReader(f, **kw))


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def generate(d, sage_path, title_suffix="", orig_updates=None):
    master = rd(os.path.join(d, "master_products.csv"))
    upd = rd(os.path.join(d, "shopify_updates.csv"))
    oupd = rd(orig_updates) if orig_updates else upd  # first-delivery view: what was wrong in the source data
    cross = rd(os.path.join(d, "crosswalk.csv"))
    feed = rd(os.path.join(d, "amazon_price_quantity.txt"), delimiter="\t")
    sage = {r["STOCK_CODE"]: r for r in rd(sage_path)}
    M = {m["stock_code"]: m for m in master}

    # ---------------- channel summary ----------------
    ship = [u for u in upd if u["new_status"] != "archived"]
    status_counts = {}
    prod_status = {}
    for u in upd:
        prod_status[u["product_id"]] = u["new_status"]
    for s in prod_status.values():
        status_counts[s] = status_counts.get(s, 0) + 1
    shop_units = sum(int(u["new_inventory"]) for u in upd if u["new_status"] == "active" and u["stock_code"] and "duplicate" not in u["note"])
    shop_units_all = sum(int(u["new_inventory"]) for u in upd if "duplicate" not in u["note"])
    codes = {r["stock_code"]: r for r in cross if r["channel"] == "amazon"}
    fba_rows = [f for f in feed if f["fulfillment-channel"] == "AMAZON_EU"]
    mfn = [f for f in feed if f["fulfillment-channel"] == "DEFAULT"]
    orphans = [f for f in mfn if codes[f["sku"]]["stock_code"] == "ORPHAN"] if False else [
        f for f in mfn if next(c for c in cross if c["channel"] == "amazon" and c["identifier"] == f["sku"])["stock_code"] == "ORPHAN"]
    orph_skus = {f["sku"] for f in orphans}
    packs = {c["identifier"]: int(c["pack_qty"]) for c in cross if c["channel"] == "amazon"}
    singles = [f for f in mfn if f["sku"] not in orph_skus and packs[f["sku"]] == 1]
    multis = [f for f in mfn if f["sku"] not in orph_skus and packs[f["sku"]] > 1]
    mfn_units = sum(int(f["quantity"] or 0) for f in mfn)
    single_units = sum(int(f["quantity"] or 0) for f in singles)
    multi_units = sum(int(f["quantity"] or 0) for f in multis)
    multi_item_units = sum(int(f["quantity"] or 0) * packs[f["sku"]] for f in multis)
    fba_units = 0
    for m in master:
        for q in (m["fba_fulfillable"].split(";") if m["fba_fulfillable"] else []):
            fba_units += int(q)
    zero_shop = [u["stock_code"] for u in upd if "duplicate" not in u["note"] and int(u["new_inventory"]) == 0]
    map_rows = [m for m in master if m["map"] and D(m["map"]) > D(m["gross_price"])]
    s = ["# Channel summary%s\n" % title_suffix,
         "## Shopify (store, location 7001)\n",
         "- Products: %d (%s)" % (len(prod_status), ", ".join("%d %s" % (v, k) for k, v in sorted(status_counts.items()))),
         "- Variants: %d (%d mapped to Sage codes live and updated; %d on the archived duplicate product, left untouched)" % (
             len(upd), len(upd) - sum(1 for u in upd if "duplicate" in u["note"]), sum(1 for u in upd if "duplicate" in u["note"])),
         "- Total units offered (sum of inventory on the %d non-duplicate variants): **%d**" % (
             len(upd) - sum(1 for u in upd if "duplicate" in u["note"]), shop_units_all),
         "  - of which on `active` products: %d" % shop_units,
         "- Variants at zero stock: %s\n" % (", ".join(zero_shop) or "none"),
         "## Amazon UK (one feed row per listing: %d)\n" % len(feed),
         table(["Listing type", "Listings", "Units offered"], [
             ["Merchant-fulfilled, single unit", len(singles), single_units],
             ["Merchant-fulfilled, multipack (units = packs)", len(multis), "%d packs (= %d single items)" % (multi_units, multi_item_units)],
             ["FBA (Amazon holds stock; no quantity sent)", len(fba_rows), "%d fulfillable at Amazon (FBA report, not sent)" % fba_units],
             ["Orphan (no Sage item; quantity 0)", len(orphans), 0]]),
         "- Total merchant-fulfilled quantity sent in the feed: **%d** packs/units across %d listings (FBA excluded)\n" % (mfn_units, len(mfn)),
         "## Items where MAP set the Shopify price (MAP > gross)\n",
         table(["Stock code", "Net", "Gross", "MAP", "Shopify price"],
               [[m["stock_code"], m["net_price"], m["gross_price"], m["map"], m["shopify_price"]] for m in map_rows]),
         "%d of %d Sage items are MAP-priced; items with a MAP no higher than gross keep gross: %s.\n" % (
             len(map_rows), len(master), ", ".join(m["stock_code"] for m in master if m["map"] and D(m["map"]) <= D(m["gross_price"])) or "none")]
    open(os.path.join(d, "channel_summary.md"), "w").write("\n".join(s))

    # ---------------- exceptions ----------------
    e = ["# Exceptions report%s\n", "Everything below needs the client's attention.\n"]
    e[0] = e[0] % title_suffix
    orph = [c for c in cross if c["stock_code"] == "ORPHAN"]
    e.append("## 1. Orphans (no Sage item)\n")
    e.append(table(["Channel", "Identifier", "Title", "Barcode", "Action taken"],
                   [[c["channel"], c["identifier"], c["product_title"], c["barcode"], "Amazon: current price kept, quantity 0, no min/max" if c["channel"] == "amazon" else ""] for c in orph]) if orph else "None.\n")
    e.append("Client decision: create a Sage record or remove the listing.\n")
    e.append("## 2. Inactive items\n")
    inact = [m for m in master if m["active"] == "0"]
    e.append(table(["Stock code", "Title", "Variant", "In stock", "Action taken"], [
        [m["stock_code"], m["title"], m["variant"], m["qty_in_stock"], "Shopify qty 0, Amazon MFN qty 0%s" % ("; product set to draft (all variants inactive)" if any(u["stock_code"] == m["stock_code"] and u["new_status"] == "draft" for u in upd) else "; product stays active (other variants live)")] for m in inact]) if inact else "None.\n")
    e.append("## 3. Stock problems\n")
    probs = []
    for m in master:
        iss = []
        if int(m["qty_in_stock"]) < 0:
            iss.append("negative stock in Sage")
        if m["stock_code"] not in rules.KIT_COMPONENTS and int(m["qty_allocated"]) > int(m["qty_in_stock"]):
            iss.append("allocated exceeds stock (available floored to 0)")
        if m["stock_code"] in rules.KIT_COMPONENTS:
            iss.append("kit: Sage shows %s, computed available %s from components" % (m["qty_in_stock"], m["available"]))
        if iss:
            probs.append([m["stock_code"], m["qty_in_stock"], m["qty_allocated"], m["available"], "; ".join(iss)])
    e.append(table(["Stock code", "In stock", "Allocated", "Available", "Issue"], probs) if probs else "None.\n")
    e.append("## 4. Sage barcode corrections (see sage_updates.csv)\n")
    su = rd(os.path.join(d, "sage_updates.csv"))
    e.append(table(["Stock code", "Old", "New", "Source"], [[r["STOCK_CODE"], r["OLD_VALUE"], r["NEW_VALUE"], r["SOURCE"]] for r in su]) if su else "None.\n")
    sh_fix = [u for u in oupd if u["current_barcode"] != u["new_barcode"]]
    e.append("Shopify barcodes corrected live: %s\n" % (", ".join("%s (%s -> %s)" % (u["stock_code"], u["current_barcode"] or "blank", u["new_barcode"]) for u in sh_fix) or "none"))
    e.append("## 5. Duplicate Shopify product\n")
    dups = [u for u in oupd if "duplicate" in u["note"]]
    e.append(table(["Product id", "Variant id", "Sage code", "Status before", "Status now"],
                   [[u["product_id"], u["variant_id"], u["stock_code"], u["current_status"], u["new_status"]] for u in dups]) if dups else "None.\n")
    e.append("The `active` product carries the real item; the other is set to `archived`. Its price/barcode/stock were not touched.\n")
    e.append("## 6. Weight mismatches (Shopify grams vs Sage UNIT_WEIGHT x 1000; grams not pushed)\n")
    wm = [m for m in master if "weight mismatch" in m["notes"]]
    e.append(table(["Stock code", "Detail"], [[m["stock_code"], [n for n in m["notes"].split("; ") if "weight" in n][0]] for m in wm]) if wm else "None found: every matched Shopify variant's grams equals Sage UNIT_WEIGHT x 1000.\n")
    e.append("## 7. Other points\n")
    e.append("- Variants whose Shopify SKU differed from the Sage code (fixed live): %s." % ", ".join(
        "%s ('%s')" % (u["stock_code"], u["current_sku"] or "blank") for u in oupd if u["current_sku"] != u["new_sku"] and "duplicate" not in u["note"]))
    e.append("- Auto-generated Amazon SKUs matched by EAN: %s." % ", ".join(c["identifier"] + "→" + c["stock_code"] for c in cross if c["channel"] == "amazon" and c["match_method"] == "product-id"))
    nomap = [m["stock_code"] for m in master if not m["map"]]
    e.append("- Items with no MAP (priced at gross): %s." % ", ".join(nomap))
    e.append("- NHG-KIT-01 has no supplier part reference; no MAP.")
    open(os.path.join(d, "exceptions_report.md"), "w").write("\n".join(e) + "\n")


if __name__ == "__main__":
    generate(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "sage_stock_export.csv"),
             orig_updates=sys.argv[3] if len(sys.argv) > 3 else None)
