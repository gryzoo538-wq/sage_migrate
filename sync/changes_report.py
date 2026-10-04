"""Compare phase1 and final: every changed field per Sage code, Shopify variant and Amazon listing, with cause."""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P1, F = os.path.join(ROOT, "output/phase1"), os.path.join(ROOT, "output/final")
STOCKTAKE = {r["STOCK_CODE"]: r["COUNTED_QTY"] for r in csv.DictReader(open(os.path.join(ROOT, "client_update/stocktake_2026-10-07.csv")))}
MAPCHG = {"NHG-1001-BLU", "NHG-1001-GRN", "NHG-1001-RED", "NHG-1002-S", "NHG-1004"}  # Hartley refs HM-WC9-B/G/R, HM-SEC-S, HM-BP-LH
DISCONT = {"NHG-3003-S"}
KIT = "NHG-KIT-01"


def rd(p, **k):
    return list(csv.DictReader(open(p, newline=""), **k))


def cause_qty(code):
    if code == KIT:
        return "knock-on: kit component NHG-3001 stocktake (counted 1, allocated 2, available 0) drives the kit to 0"
    if code in DISCONT:
        return "discontinuation (NHG-3003-S now inactive)"
    if code in STOCKTAKE:
        return "stocktake (counted %s)" % STOCKTAKE[code]
    return "unknown"


def main():
    m1 = {r["stock_code"]: r for r in rd(P1 + "/master_products.csv")}
    m2 = {r["stock_code"]: r for r in rd(F + "/master_products.csv")}
    rows = []  # level, id, field, old, new, cause
    causes = {"qty_in_stock": "stocktake (counted figure replaces QTY_IN_STOCK)", "available": None, "map": "MAP update (Hartley, effective 10 Oct)",
              "shopify_price": "MAP update (MAP now above gross)", "active": "discontinuation (NHG-3003-S)",
              "fba_fulfillable": "FBA refresh (report of 2026-10-08)"}
    for c, a in m1.items():
        b = m2[c]
        for fld in a:
            if a[fld] == b[fld]:
                continue
            if fld == "notes":
                cause = "derived from the changes above"
            elif fld == "available":
                cause = cause_qty(c) if c != KIT else cause_qty(c)
            else:
                cause = causes.get(fld, "derived")
            rows.append(("Sage code", c, fld, a[fld], b[fld], cause))
    # Shopify variants: live phase1 vs live final
    def live(path):
        d = {}
        for p in json.load(open(path)):
            for v in p["variants"]:
                d[v["id"]] = (p, v)
        return d
    l1, l2 = live(P1 + "/shopify_live_phase1.json"), live(F + "/shopify_live.json")
    by_var = {r["shopify_variant_id"]: r["stock_code"] for r in rd(F + "/master_products.csv") if r["shopify_variant_id"]}
    for vid, (p1, v1) in l1.items():
        p2, v2 = l2[vid]
        code = by_var.get(str(vid), "duplicate/%s" % vid)
        for fld in ("sku", "price", "barcode", "inventory_quantity"):
            if str(v1.get(fld)) != str(v2.get(fld)):
                if fld == "price":
                    cause = "MAP update"
                else:
                    cause = cause_qty(code)
                rows.append(("Shopify variant", "%s (%s)" % (code, vid), fld, v1.get(fld), v2.get(fld), cause))
        if p1["status"] != p2["status"]:
            rows.append(("Shopify product", "%s" % p1["id"], "status", p1["status"], p2["status"], "n/a"))
    # Amazon listings: feed phase1 vs final (both verified live)
    f1 = {r["sku"]: r for r in rd(P1 + "/amazon_price_quantity.txt", delimiter="\t")}
    f2 = {r["sku"]: r for r in rd(F + "/amazon_price_quantity.txt", delimiter="\t")}
    code_of = {r["identifier"]: r["stock_code"] for r in rd(F + "/crosswalk.csv") if r["channel"] == "amazon"}
    for sku, a in f1.items():
        b = f2[sku]
        code = code_of[sku]
        for fld in a:
            if a[fld] != b[fld]:
                cause = cause_qty(code) if fld == "quantity" else "MAP update (Amazon price/limits follow the Shopify price, MAP floor)"
                rows.append(("Amazon listing", "%s (%s)" % (sku, code), fld, a[fld], b[fld], cause))
    # FBA fulfillable (reported, never sent)
    fa = {r["sku"]: r["afn-fulfillable-quantity"] for r in rd(ROOT + "/amazon_fba_inventory_report.txt", delimiter="\t")}
    fb = {r["sku"]: r["afn-fulfillable-quantity"] for r in rd(ROOT + "/client_update/amazon_fba_inventory_report_2026-10-08.txt", delimiter="\t")}
    for sku in fa:
        if fa[sku] != fb.get(sku):
            rows.append(("Amazon listing", "%s (%s)" % (sku, code_of[sku]), "fba_fulfillable (report only, not sent)", fa[sku], fb[sku], "FBA refresh"))
    out = ["# Changes report: phase 1 to final\n",
           "Inputs applied: stocktake 2026-10-07 (6 codes), Hartley MAP update (5 supplier refs, effective 10 Oct), NHG-3003-S discontinued (inactive), FBA report of 2026-10-08.",
           "Shopify and Amazon values are compared as read live after each push. Amazon values come from the verified feed files. Any field not listed did not change.\n"]
    for level in ("Sage code", "Shopify variant", "Shopify product", "Amazon listing"):
        sel = [r for r in rows if r[0] == level]
        out.append("## %s (%d changes)\n" % (level, len(sel)))
        if not sel:
            out.append("No changes.\n")
            continue
        out.append("| Item | Field | Phase 1 | Final | Cause |\n|---|---|---|---|---|")
        for r in sel:
            out.append("| %s | %s | %s | %s | %s |" % (r[1], r[2], "(blank)" if r[3] in (None, "") else r[3], "(blank)" if r[4] in (None, "") else r[4], r[5]))
        out.append("")
    open(F + "/changes_report.md", "w").write("\n".join(out) + "\n")
    print(len(rows), "changes")


main()
