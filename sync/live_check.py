"""Re-read Shopify (all variants) and every Amazon listing from the live API and compare with the master and feed.

usage: python3 sync/live_check.py --dir output/phase1 [--shopify-json-out F]
"""
import argparse
import csv
import json
import os
import sys
from decimal import Decimal as D

sys.path.insert(0, os.path.dirname(__file__))
from amazon import Amazon  # noqa: E402
from shopify import Shopify  # noqa: E402


def money_eq(a, b):
    try:
        return D(str(a)) == D(str(b))
    except Exception:
        return str(a) == str(b)


def run(d, base="http://127.0.0.1:8770"):
    master = {r["stock_code"]: r for r in csv.DictReader(open(os.path.join(d, "master_products.csv")))}
    upd = list(csv.DictReader(open(os.path.join(d, "shopify_updates.csv"))))
    products = Shopify(base).products()
    json.dump(products, open(os.path.join(d, "shopify_live.json"), "w"), indent=1)
    live = {}
    for p in products:
        for v in p["variants"]:
            live[str(v["id"])] = (p, v)
    rows = []

    def add(system, item, field, exp, got, cmp=None):
        ok = (cmp or (lambda a, b: str(a) == str(b)))(exp, got)
        rows.append([system, item, field, exp, got, "MATCH" if ok else "MISMATCH"])

    seen_prod = set()
    for u in upd:
        vid = u["variant_id"]
        if vid not in live:
            add("shopify", u["stock_code"] or vid, "variant_exists", "yes", "no")
            continue
        p, v = live[vid]
        code = u["stock_code"]
        if u["new_status"] == "archived" and u["current_status"] != "archived" or "duplicate" in u["note"]:
            add("shopify", "%s (duplicate product %s)" % (code, p["id"]), "product_status", "archived", p["status"])
            continue
        m = master[code]
        item = "%s/%s" % (code, vid)
        add("shopify", item, "sku", code, v.get("sku"))
        add("shopify", item, "price", m["shopify_price"], v.get("price"), money_eq)
        add("shopify", item, "barcode", m["correct_barcode"], v.get("barcode"))
        exp_inv = u["new_inventory"]
        add("shopify", item, "inventory", exp_inv, v.get("inventory_quantity"))
        if p["id"] not in seen_prod:
            seen_prod.add(p["id"])
            add("shopify", "%s (product %s)" % (code, p["id"]), "product_status", u["new_status"], p["status"])
    amz = Amazon(base)
    for line in open(os.path.join(d, "amazon_price_quantity.txt")).read().splitlines()[1:]:
        sku, price, mn, mx, q, ht, ch = line.split("\t")
        l = amz.listing(sku)
        add("amazon", sku, "price", price, l.get("price"), money_eq)
        add("amazon", sku, "min_price", mn, l.get("minimum_seller_allowed_price", ""),
            lambda a, b: (a == "" and b in ("", None)) or money_eq(a, b))
        add("amazon", sku, "max_price", mx, l.get("maximum_seller_allowed_price", ""),
            lambda a, b: (a == "" and b in ("", None)) or money_eq(a, b))
        if ch == "AMAZON_EU":
            add("amazon", sku, "channel", "AFN", l.get("channel"))
            add("amazon", sku, "quantity", "", "" if l.get("quantity") in (None, "") else l.get("quantity"))
        else:
            add("amazon", sku, "quantity", q, l.get("quantity"))
            add("amazon", sku, "channel", "MFN", l.get("channel"))
    with open(os.path.join(d, "live_check.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["system", "item", "field", "expected", "live", "result"])
        w.writerows(rows)
    bad = [r for r in rows if r[-1] != "MATCH"]
    print("%d checks, %d mismatches" % (len(rows), len(bad)))
    for r in bad:
        print("  MISMATCH", r)
    return rows, bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    run(ap.parse_args().dir)
