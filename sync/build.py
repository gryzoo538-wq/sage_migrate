"""Reconcile Sage + Shopify + Amazon into the master dataset and channel files.

usage: python3 sync/build.py --out output/phase1 [--sage F] [--listings F] [--fba F] [--shopify-json F] [--supplier-map F]
"""
import argparse
import csv
import json
import os
import sys
from decimal import Decimal as D

sys.path.insert(0, os.path.dirname(__file__))
import rules  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED_HEADER = ["sku", "price", "minimum-seller-allowed-price", "maximum-seller-allowed-price",
               "quantity", "handling-time", "fulfillment-channel"]


def read_sage(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = []
        for r in csv.DictReader(f):
            r = {k.strip(): (v or "").strip() for k, v in r.items()}
            rows.append(r)
    return rows


def read_tsv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f, delimiter="\t")]


def read_map(path):
    out = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            out[r["part_ref"]] = None if r["MAP"] in ("—", "", "-") else D(r["MAP"])
    return out


def fmt(d):
    return "" if d is None else str(D(str(d)).quantize(rules.CENT))


def build(sage_rows, listings, fba_rows, shop_products, map_by_ref, tiers, overrides=None, live_products=None):
    """shop_products = original Shopify pull (identity, match method, barcode provenance);
    live_products = optional later pull whose values are the 'current' side of shopify_updates."""
    overrides = overrides or {}
    live_by_id = {}
    for lp in (live_products or []):
        for lv in lp["variants"]:
            live_by_id[lv["id"]] = (lp, lv)
    S = {}
    for r in sage_rows:
        code = r["STOCK_CODE"]
        S[code] = dict(r, code=code, norm=rules.normalise_sku(code))
    by_norm = {s["norm"]: c for c, s in S.items()}

    # ---- Shopify flatten, match ----
    variants = []
    for p in shop_products:
        for v in p["variants"]:
            variants.append(dict(v, product=p))
    # barcode candidates from Sage that are valid and unshared
    sage_bc_count = {}
    for s in S.values():
        sage_bc_count[s["BARCODE"]] = sage_bc_count.get(s["BARCODE"], 0) + 1
    sage_ok = lambda s: (rules.valid_ean13(s["BARCODE"]) and not rules.is_mangled(s["BARCODE"])
                         and sage_bc_count[s["BARCODE"]] == 1)

    # first pass: SKU match
    for v in variants:
        sku = (v.get("sku") or "").strip()
        n = rules.normalise_sku(sku)
        v["code"], v["method"] = None, None
        if sku in S:
            v["code"], v["method"] = sku, "sku"
        elif n and n in by_norm:
            v["code"], v["method"] = by_norm[n], "normalised sku"
    # barcode-based match for blank SKU: any Sage item whose any-source barcode equals it
    shop_bc = {}
    for v in variants:
        if v["code"]:
            shop_bc.setdefault(v["code"], []).append((v.get("barcode") or "").strip())
    amz_bc = {}
    amazon_info = []
    for l in listings:
        base, pack, fba = rules.parse_amazon_sku(l["seller-sku"])
        info = dict(l, base=base, pack=pack, fba=fba, code=None, method=None)
        n = rules.normalise_sku(base)
        if base in S:
            info["code"], info["method"] = base, "sku"
        elif n in by_norm:
            info["code"], info["method"] = by_norm[n], "normalised sku"
        amazon_info.append(info)
        if info["code"]:
            amz_bc.setdefault(info["code"], []).append(l["product-id"])

    # ---- duplicate products: active wins ----
    by_code = {}
    for v in variants:
        if v["code"]:
            by_code.setdefault(v["code"], []).append(v)
    for c, vs in by_code.items():
        vs_prod = {v["product"]["id"] for v in vs}
        for v in vs:
            v["duplicate"] = False
        if len(vs_prod) > 1:
            actives = [v for v in vs if v["product"]["status"] == "active"]
            real = actives[0] if actives else vs[0]
            for v in vs:
                v["duplicate"] = v is not real

    # ---- correct barcode ----
    def correct_barcode(code):
        s = S[code]
        sb = s["BARCODE"]
        shp = [b for b in shop_bc.get(code, []) if b]
        amz = [b for b in amz_bc.get(code, [])]
        if code in overrides.get("barcode", {}):
            return overrides["barcode"][code]
        if sage_ok(s):
            # conflicts: a valid unshared Sage barcode is kept unless two valid others agree against it
            return sb, "sage"
        for b in shp:
            if rules.valid_ean13(b):
                return b, "shopify"
        for b in amz:
            if rules.valid_ean13(b):
                return b, "amazon"
        return None, "none"

    # blank-SKU variants matched by barcode against any source's barcode of a Sage item
    for v in variants:
        if v["code"]:
            continue
        bc = (v.get("barcode") or "").strip()
        for c, s in S.items():
            if bc and (bc == s["BARCODE"] or bc in amz_bc.get(c, [])):
                v["code"], v["method"] = c, "barcode"
                shop_bc.setdefault(c, []).append(bc)
                by_code.setdefault(c, []).append(v)
                v["duplicate"] = False
    correct = {}
    for c in S:
        b = correct_barcode(c)
        correct[c] = b if isinstance(b, tuple) and not isinstance(b[0], tuple) else b
    # normalise shape
    correct = {c: (b if isinstance(b, tuple) else (b, "override")) for c, b in correct.items()}
    # amazon auto-SKU / unmatched by product-id
    cb_to_code = {b: c for c, (b, _) in correct.items() if b}
    for info in amazon_info:
        if not info["code"] and info["product-id"] in cb_to_code:
            info["code"], info["method"] = cb_to_code[info["product-id"]], "product-id"

    # ---- stock ----
    avail = {c: rules.available(s["QTY_IN_STOCK"], s["QTY_ALLOCATED"]) for c, s in S.items()}
    for c, s in overrides.get("avail", {}).items():
        avail[c] = s
    for kit, comps in rules.KIT_COMPONENTS.items():
        if kit in S:
            avail[kit] = rules.kit_available(avail, comps)
    fba_q = {r["sku"]: r["afn-fulfillable-quantity"] for r in fba_rows}

    master = []
    for c, s in S.items():
        inactive = s["INACTIVE_FLAG"] == "1" or c in overrides.get("inactive", set())
        net = D(s["SALES_PRICE"])
        gr = rules.gross(net, s["TAX_CODE"])
        mp = map_by_ref.get(s["SUPPLIER_PART_REF"]) if s["SUPPLIER_PART_REF"] else None
        sp = rules.shopify_price(gr, mp)
        real = [v for v in by_code.get(c, []) if not v["duplicate"]]
        v = real[0] if real else None
        notes = []
        if c in rules.KIT_COMPONENTS:
            notes.append("kit: available = min of components %s; Sage figure ignored" % ", ".join(rules.KIT_COMPONENTS[c]))
        if mp is not None and mp > gr:
            notes.append("MAP raised price (gross %s -> MAP %s)" % (fmt(gr), fmt(mp)))
        if int(s["QTY_IN_STOCK"]) < 0:
            notes.append("negative stock in Sage")
        if int(s["QTY_ALLOCATED"]) > int(s["QTY_IN_STOCK"]) and c not in rules.KIT_COMPONENTS:
            notes.append("over-allocated (allocated > in stock)")
        if inactive:
            notes.append("inactive: channel qty 0")
        if v is not None and v["method"] != "sku":
            notes.append("Shopify SKU '%s' fixed (%s match)" % (v.get("sku") or "", v["method"]))
        cb, src = correct[c]
        if cb != s["BARCODE"]:
            notes.append("Sage barcode '%s' needs correcting" % s["BARCODE"])
        if v is not None:
            g = v.get("grams")
            if g is not None and int(g) != int(round(D(s["UNIT_WEIGHT"]) * 1000)):
                notes.append("weight mismatch: Shopify %s g vs Sage %s kg" % (g, s["UNIT_WEIGHT"]))
        amz = [i["seller-sku"] for i in amazon_info if i["code"] == c]
        fq = [fba_q[a] for a in amz if a in fba_q]
        opt = v["option1"] if v and v["option1"] != "Default Title" else ""
        master.append(dict(
            stock_code=c, title=v["product"]["title"] if v else s["DESCRIPTION"], variant=opt,
            vat_code=s["TAX_CODE"], net_price=fmt(net), gross_price=fmt(gr), map=fmt(mp), shopify_price=fmt(sp),
            correct_barcode=cb, barcode_source=src, qty_in_stock=s["QTY_IN_STOCK"], qty_allocated=s["QTY_ALLOCATED"],
            available=avail[c], active=0 if inactive else 1, weight_kg=s["UNIT_WEIGHT"],
            shopify_product_id=v["product"]["id"] if v else "", shopify_variant_id=v["id"] if v else "",
            shopify_inventory_item_id=v["inventory_item_id"] if v else "", amazon_skus=";".join(amz),
            fba_fulfillable=";".join(fq) if fq else "", notes="; ".join(notes)))
    M = {m["stock_code"]: m for m in master}

    # ---- Shopify updates ----
    # product status: duplicate -> archived; all variants inactive -> draft
    prod_variants = {}
    for v in variants:
        prod_variants.setdefault(v["product"]["id"], []).append(v)
    shop_rows = []
    for v in variants:
        p = v["product"]
        c = v["code"]
        lp, lv = live_by_id.get(v["id"], (p, v))
        row = dict(variant_id=v["id"], product_id=p["id"], stock_code=c or "", inventory_item_id=v["inventory_item_id"],
                   current_sku=lv.get("sku") or "", new_sku=c or lv.get("sku") or "",
                   current_price=lv.get("price"), new_price=lv.get("price"),
                   current_barcode=lv.get("barcode") or "", new_barcode=lv.get("barcode") or "",
                   current_inventory=lv.get("inventory_quantity"), new_inventory=lv.get("inventory_quantity"),
                   current_status=lp["status"], new_status=lp["status"], note="")
        if c and not v["duplicate"]:
            m = M[c]
            row["new_price"] = m["shopify_price"]
            row["new_barcode"] = m["correct_barcode"]
            row["new_inventory"] = rules.channel_qty(m["available"], 1, not int(m["active"]))
        if c and v["duplicate"]:
            row["new_status"] = "archived"
            row["note"] = "duplicate product of %s: archive" % c
        elif c:
            members = [x for x in prod_variants[p["id"]] if x["code"] and not x["duplicate"]]
            if members and all(not int(M[x["code"]]["active"]) for x in members):
                row["new_status"] = "draft"
                row["note"] = "all variants inactive: draft"
            elif lp["status"] != "active" and not v["duplicate"]:
                row["new_status"] = "active"
        shop_rows.append(row)

    # ---- Amazon feed ----
    feed = []
    for i in amazon_info:
        l = i
        if i["code"] is None:
            feed.append(dict(sku=l["seller-sku"], price=l["price"], min="", max="", quantity="0",
                             handling="2", channel=l["fulfillment-channel"] if l["fulfillment-channel"] != "AMAZON_EU" else "AMAZON_EU",
                             code="ORPHAN", pack=1, fba=i["fba"], note="orphan: current price, qty 0"))
            continue
        c = i["code"]
        m = M[c]
        sp = D(m["shopify_price"])
        fee = rules.fba_fee(m["weight_kg"], tiers) if i["fba"] else D("0")
        ap = rules.amazon_price(sp, i["pack"], i["fba"], fee)
        mp = D(m["map"]) if m["map"] else None
        mn, mx = rules.amazon_limits(ap, sp, mp, i["pack"])
        if i["fba"]:
            q, h, ch = "", "", "AMAZON_EU"
        else:
            q = rules.channel_qty(m["available"], i["pack"], not int(m["active"]))
            h, ch = "2", "DEFAULT"
        feed.append(dict(sku=l["seller-sku"], price=fmt(ap), min=fmt(mn), max=fmt(mx), quantity=q, handling=h,
                         channel=ch, code=c, pack=i["pack"], fba=i["fba"], note="fba fee %s" % fee if i["fba"] else ""))
    return dict(S=S, M=M, master=master, variants=variants, amazon=amazon_info, shop_rows=shop_rows, feed=feed)


def write_all(res, out, listings):
    os.makedirs(out, exist_ok=True)
    cols = ["stock_code", "title", "variant", "vat_code", "net_price", "gross_price", "map", "shopify_price",
            "correct_barcode", "barcode_source", "qty_in_stock", "qty_allocated", "available", "active", "weight_kg",
            "shopify_product_id", "shopify_variant_id", "shopify_inventory_item_id", "amazon_skus", "fba_fulfillable", "notes"]
    with open(os.path.join(out, "master_products.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(res["master"])
    # crosswalk
    with open(os.path.join(out, "crosswalk.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["channel", "identifier", "listing_id", "current_sku", "stock_code", "match_method", "pack_qty",
                    "fulfilment", "barcode", "product_title", "notes"])
        for v in res["variants"]:
            notes = []
            if not (v.get("sku") or "").strip():
                notes.append("blank SKU")
            elif v["method"] == "normalised sku":
                notes.append("SKU format differs from Sage")
            if v.get("duplicate"):
                notes.append("DUPLICATE product (status %s): archive; active product is the real one" % v["product"]["status"])
            w.writerow(["shopify", v["id"], v["product"]["id"], v.get("sku") or "", v["code"] or "ORPHAN",
                        v["method"] or "none", 1, "", v.get("barcode") or "", v["product"]["title"], "; ".join(notes)])
        for i in res["amazon"]:
            notes = []
            if i["code"] is None:
                notes.append("ORPHAN: no Sage item (EAN %s unknown)" % i["product-id"])
            elif i["method"] == "product-id":
                notes.append("auto-generated SKU matched on product-id")
            w.writerow(["amazon", i["seller-sku"], i["listing-id"], i["seller-sku"], i["code"] or "ORPHAN",
                        i["method"] or "none", i["pack"], "FBA" if i["fba"] else "MFN", i["product-id"], i["item-name"],
                        "; ".join(notes)])
    with open(os.path.join(out, "shopify_updates.csv"), "w", newline="") as f:
        cols = ["variant_id", "product_id", "stock_code", "inventory_item_id", "current_sku", "new_sku", "current_price",
                "new_price", "current_barcode", "new_barcode", "current_inventory", "new_inventory", "current_status",
                "new_status", "note"]
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(res["shop_rows"])
    with open(os.path.join(out, "amazon_price_quantity.txt"), "w", newline="") as f:
        f.write("\t".join(FEED_HEADER) + "\n")
        for r in res["feed"]:
            f.write("\t".join([r["sku"], r["price"], r["min"], r["max"], str(r["quantity"]), r["handling"], r["channel"]]) + "\n")
    with open(os.path.join(out, "sage_updates.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["STOCK_CODE", "FIELD", "OLD_VALUE", "NEW_VALUE", "SOURCE"])
        for m in res["master"]:
            s = res["S"][m["stock_code"]]
            if m["correct_barcode"] != s["BARCODE"]:
                reason = "damaged (scientific notation)" if rules.is_mangled(s["BARCODE"]) else (
                    "invalid check digit" if not rules.valid_ean13(s["BARCODE"]) else "shared with another stock code")
                w.writerow([m["stock_code"], "BARCODE", s["BARCODE"], m["correct_barcode"],
                            "%s (%s)" % (m["barcode_source"], reason)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--sage", default=os.path.join(ROOT, "sage_stock_export.csv"))
    ap.add_argument("--listings", default=os.path.join(ROOT, "amazon_all_listings_report.txt"))
    ap.add_argument("--fba", default=os.path.join(ROOT, "amazon_fba_inventory_report.txt"))
    ap.add_argument("--shopify-json", required=True, help="original Shopify pull")
    ap.add_argument("--live-json", help="later Shopify pull used as the current values")
    ap.add_argument("--supplier-map", required=True)
    ap.add_argument("--tiers", default=os.path.join(ROOT, "fba_fee_tiers.csv"))
    a = ap.parse_args()
    res = build(read_sage(a.sage), read_tsv(a.listings), read_tsv(a.fba), json.load(open(a.shopify_json)),
                read_map(a.supplier_map), rules.load_fee_tiers(a.tiers),
                live_products=json.load(open(a.live_json)) if a.live_json else None)
    write_all(res, a.out, None)
    print("built", len(res["master"]), "master rows,", len(res["feed"]), "feed rows")


if __name__ == "__main__":
    main()
