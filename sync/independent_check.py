"""Independent recomputation (does NOT import rules.py or build.py). Exact Fraction arithmetic.
usage: python3 sync/independent_check.py phase1|final [--live]"""
import csv
import json
import math
import re
import sys
import urllib.request
from fractions import Fraction as Fr

ROOT = __file__.rsplit("/sync/", 1)[0]
stage = sys.argv[1]
live = "--live" in sys.argv
OUT = ROOT + "/output/" + stage

# MAP typed from my second look at the three scans (HART01, GREEN02, OAKF03) -- NOT read from supplier_map.csv
MAP = {"HM-BP-LH": "14.99", "HM-HR30": "39.99", "HM-WC9-R": "22.99", "HM-SEC-S": "13.99", "HM-WC9-B": "22.99",
       "HM-SAW-F": None, "HM-WC9-G": "22.99", "HM-SEC-L": "14.99",
       "GS-BK-GYO": "9.99", "GS-COR-01": "2.49", "GS-WFM-100": None, "GS-PAR-01": "2.49", "GS-BAS-01": "2.49",
       "OGS-CB330": "34.99", "OGS-GL-XL": None, "OGS-BF-L": None, "OGS-BF-S": None, "OGS-PF1": "6.49", "OGS-RSL": None,
       "OGS-TT60": None, "OGS-RG": None, "OGS-KN-GY": "5.99", "OGS-RB-2": "69.99", "OGS-JT150": None, "OGS-KN-SG": "5.99",
       "OGS-STS5": None, "OGS-GL-S": None, "OGS-SPL10": "7.99", "OGS-GL-L": None, "OGS-RB-1": "44.99", "OGS-GL-M": None}
if stage == "final":  # HART01_MAP_update.pdf
    MAP.update({"HM-WC9-B": "24.99", "HM-WC9-G": "24.99", "HM-WC9-R": "24.99", "HM-SEC-S": "15.49", "HM-BP-LH": "16.99"})
    SAGE = OUT + "/sage_stock_export_updated.csv"
    FBA = ROOT + "/client_update/amazon_fba_inventory_report_2026-10-08.txt"
else:
    SAGE = ROOT + "/sage_stock_export.csv"
    FBA = ROOT + "/amazon_fba_inventory_report.txt"
    if False:
        pass
# stocktake/discontinuation are applied in the updated Sage copy; re-derive it independently from the originals:
if stage == "final":
    cnt = {r[0]: r[1] for r in list(csv.reader(open(ROOT + "/client_update/stocktake_2026-10-07.csv")))[1:]}
    base = list(csv.DictReader(open(ROOT + "/sage_stock_export.csv", encoding="utf-8-sig")))
    upd = {r["STOCK_CODE"]: r for r in csv.DictReader(open(SAGE))}
    for r in base:
        q = cnt.get(r["STOCK_CODE"], r["QTY_IN_STOCK"])
        inact = "1" if r["STOCK_CODE"] == "NHG-3003-S" else r["INACTIVE_FLAG"]
        assert upd[r["STOCK_CODE"]]["QTY_IN_STOCK"] == q and upd[r["STOCK_CODE"]]["INACTIVE_FLAG"] == inact, r["STOCK_CODE"]
        assert upd[r["STOCK_CODE"]]["QTY_ALLOCATED"] == r["QTY_ALLOCATED"]

problems = []
checks = 0


def chk(cond, msg):
    global checks
    checks += 1
    if not cond:
        problems.append(msg)


def ean_ok(s):
    if not re.fullmatch(r"\d{13}", s or ""):
        return False
    d = list(map(int, s))
    return (sum(d[0:12:2]) + 3 * sum(d[1:12:2]) + d[12]) % 10 == 0


def pence(x):
    return Fr(x)


def charm(v):  # v Fraction in pounds
    pounds = math.floor(v)
    t = Fr(pounds) + Fr(99, 100)
    return t if v <= t else t + 1


def money(f):
    c = f * 100
    assert c.denominator == 1, f
    return "%d.%02d" % divmod(int(c), 100)


sage = {r["STOCK_CODE"]: r for r in csv.DictReader(open(SAGE, encoding="utf-8-sig"))}
shop_orig = json.load(open(ROOT + "/output/phase1/shopify_raw_phase1.json"))
listings = list(csv.DictReader(open(ROOT + "/amazon_all_listings_report.txt"), delimiter="\t"))
fba_rep = {r["sku"]: int(r["afn-fulfillable-quantity"]) for r in csv.DictReader(open(FBA), delimiter="\t")}
tiers = [(Fr(r["max_weight_kg"]), Fr(r["fee_gbp"])) for r in csv.DictReader(open(ROOT + "/fba_fee_tiers.csv"))]

# ---- barcodes: majority of valid across sources ----
shop_bc = {}
for p in shop_orig:
    for v in p["variants"]:
        k = re.sub(r"[^A-Z0-9]", "", (v["sku"] or "").upper())
        for c in sage:
            if re.sub(r"[^A-Z0-9]", "", c) == k:
                shop_bc.setdefault(c, []).append(v["barcode"])
sage_count = {}
for r in sage.values():
    sage_count[r["BARCODE"]] = sage_count.get(r["BARCODE"], 0) + 1
amz_bc = {}
for l in listings:
    base = re.sub(r"(-X\d+|-FBA)+$", "", l["seller-sku"])
    for c in sage:
        if c == base:
            amz_bc.setdefault(c, []).append(l["product-id"])
# blank-SKU Shopify variant by barcode
for p in shop_orig:
    for v in p["variants"]:
        if not v["sku"]:
            for c, r in sage.items():
                if v["barcode"] == r["BARCODE"]:
                    shop_bc.setdefault(c, []).append(v["barcode"])
true_bc = {}
for c, r in sage.items():
    s = r["BARCODE"]
    if ean_ok(s) and sage_count[s] == 1:
        true_bc[c] = s
        continue
    cands = [b for b in shop_bc.get(c, []) if ean_ok(b)] + [b for b in amz_bc.get(c, []) if ean_ok(b)]
    true_bc[c] = max(set(cands), key=cands.count) if cands else None
# auto SKUs matched on EAN
by_ean = {b: c for c, b in true_bc.items() if b}

master = {r["stock_code"]: r for r in csv.DictReader(open(OUT + "/master_products.csv"))}
chk(set(master) == set(sage), "master rows != sage codes")
avail = {}
for c, r in sage.items():
    avail[c] = max(0, int(r["QTY_IN_STOCK"]) - int(r["QTY_ALLOCATED"]))
avail["NHG-KIT-01"] = min(avail[c] for c in ("NHG-2001", "NHG-2002", "NHG-2003", "NHG-3001"))
exp_shop = {}
for c, r in sage.items():
    m = master[c]
    net = Fr(r["SALES_PRICE"])
    vat = Fr(20, 100) if r["TAX_CODE"] == "T1" else Fr(0)
    g = net * (1 + vat)
    g = Fr(math.floor(g * 100 + Fr(1, 2)), 100)  # half-up
    mp = MAP.get(r["SUPPLIER_PART_REF"]) if r["SUPPLIER_PART_REF"] else None
    sp = max(g, Fr(mp)) if mp else g
    exp_shop[c] = sp
    chk(m["gross_price"] == money(g), "%s gross %s vs %s" % (c, m["gross_price"], money(g)))
    chk(m["map"] == (money(Fr(mp)) if mp else ""), "%s map %s vs %s" % (c, m["map"], mp))
    chk(m["shopify_price"] == money(sp), "%s shopify_price %s vs %s" % (c, m["shopify_price"], money(sp)))
    chk(m["correct_barcode"] == true_bc[c] and ean_ok(m["correct_barcode"]), "%s barcode %s vs %s" % (c, m["correct_barcode"], true_bc[c]))
    chk(int(m["available"]) == avail[c], "%s available %s vs %s" % (c, m["available"], avail[c]))
    chk(m["active"] == ("0" if r["INACTIVE_FLAG"] == "1" else "1"), "%s active" % c)

# ---- Shopify expected ----
def inactive(c):
    return sage[c]["INACTIVE_FLAG"] == "1"


exp_inv = {c: 0 if inactive(c) else max(0, avail[c] - 2) for c in sage}
for c in sage:
    chk(int(master[c]["shopify_variant_id"] or 0) > 0, "%s has no shopify variant" % c)

# ---- Amazon expected ----
feed = list(csv.DictReader(open(OUT + "/amazon_price_quantity.txt", newline=""), delimiter="\t"))
chk([l["seller-sku"] for l in listings] == [f["sku"] for f in feed], "feed rows != listing report rows/order")
chk(open(OUT + "/amazon_price_quantity.txt").readline().rstrip("\n") ==
    "sku\tprice\tminimum-seller-allowed-price\tmaximum-seller-allowed-price\tquantity\thandling-time\tfulfillment-channel", "feed header")
exp_amz = {}
for l, f in zip(listings, feed):
    sku = l["seller-sku"]
    is_fba = sku.upper().endswith("-FBA") or "-FBA" in sku.upper()
    mm = re.search(r"-X(\d+)", sku)
    n = int(mm.group(1)) if mm else 1
    base = re.sub(r"(-X\d+|-FBA)+$", "", sku)
    code = base if base in sage else by_ean.get(l["product-id"])
    if code is None:
        chk(f["price"] == l["price"] and f["quantity"] == "0" and f["minimum-seller-allowed-price"] == "" and
            f["maximum-seller-allowed-price"] == "" and f["handling-time"] == "2" and f["fulfillment-channel"] == "DEFAULT",
            "orphan row %s: %s" % (sku, f))
        exp_amz[sku] = dict(orphan=True, price=l["price"], qty="0", mn="", mx="", chan="DEFAULT")
        continue
    sp = exp_shop[code]
    if n > 1:
        price = charm(sp * n * Fr(92, 100) * Fr(108, 100))
        mn = ""
    elif is_fba:
        w = Fr(sage[code]["UNIT_WEIGHT"])
        fee = next(fee for mx, fee in tiers if mx >= w)
        price = charm(sp * Fr(108, 100) + fee)
    else:
        price = charm(sp * Fr(108, 100))
    if n == 1:
        mp = MAP.get(sage[code]["SUPPLIER_PART_REF"]) if sage[code]["SUPPLIER_PART_REF"] else None
        mn = money(Fr(mp)) if mp else money(sp)
    mx = money(price * 2)
    if is_fba:
        qty, ht, ch = "", "", "AMAZON_EU"
    else:
        qty = "0" if inactive(code) else str(max(0, (avail[code] - 2) // n))
        ht, ch = "2", "DEFAULT"
    exp = [money(price), mn, mx, qty, ht, ch]
    got = [f["price"], f["minimum-seller-allowed-price"], f["maximum-seller-allowed-price"], f["quantity"], f["handling-time"], f["fulfillment-channel"]]
    chk(exp == got, "feed %s expected %s got %s" % (sku, exp, got))
    exp_amz[sku] = dict(orphan=False, price=money(price), qty=qty, mn=mn, mx=mx, chan=ch)
    # crosswalk code
cw = {r["identifier"]: r["stock_code"] for r in csv.DictReader(open(OUT + "/crosswalk.csv")) if r["channel"] == "amazon"}
for l in listings:
    base = re.sub(r"(-X\d+|-FBA)+$", "", l["seller-sku"])
    code = base if base in sage else by_ean.get(l["product-id"], "ORPHAN")
    chk(cw[l["seller-sku"]] == code, "crosswalk amazon %s %s vs %s" % (l["seller-sku"], cw[l["seller-sku"]], code))
for p in shop_orig:
    for v in p["variants"]:
        pass

# FBA never sent
for f in feed:
    if f["fulfillment-channel"] == "AMAZON_EU":
        chk(f["quantity"] == "" and f["handling-time"] == "", "FBA qty sent for " + f["sku"])
# master FBA fulfillable
for c, m in master.items():
    skus = [l["seller-sku"] for l in listings if (re.sub(r"(-X\d+|-FBA)+$", "", l["seller-sku"]) == c or cw[l["seller-sku"]] == c)]
    want = ";".join(str(fba_rep[s]) for s in skus if s in fba_rep)
    chk(m["fba_fulfillable"] == want, "%s fba_fulfillable %s vs %s" % (c, m["fba_fulfillable"], want))

# sage_updates: exactly the barcodes needing correction
su = {r["STOCK_CODE"]: r for r in csv.DictReader(open(OUT + "/sage_updates.csv"))}
need = {c for c in sage if sage[c]["BARCODE"] != true_bc[c]}
chk(set(su) == need, "sage_updates codes %s vs %s" % (sorted(su), sorted(need)))
for c in need:
    chk(su[c]["OLD_VALUE"] == sage[c]["BARCODE"] and su[c]["NEW_VALUE"] == true_bc[c], "sage_update %s" % c)
# all barcodes in master valid
chk(all(ean_ok(m["correct_barcode"]) for m in master.values()), "invalid barcode in master")
chk(len({m["correct_barcode"] for m in master.values()}) == len(master), "duplicate correct barcodes")

# ---- live ----
if live:
    H = {"X-Shopify-Access-Token": "shpat_test_northfield"}
    items, url = [], "http://127.0.0.1:8770/admin/api/2024-07/products.json?limit=10"
    import time
    while url:
        for _ in range(20):
            try:
                resp = urllib.request.urlopen(urllib.request.Request(url, headers=H))
                break
            except urllib.error.HTTPError as e:
                if e.code != 429:
                    raise
                time.sleep(float(e.headers.get("Retry-After", 1)))
        items += json.loads(resp.read())["products"]
        lk = resp.headers.get("Link") or ""
        mm = re.search(r'<([^>]+)>; rel="next"', lk)
        url = mm.group(1) if mm else None
    byvar = {str(v["id"]): (p, v) for p in items for v in p["variants"]}
    for c in sage:
        p, v = byvar[master[c]["shopify_variant_id"]]
        chk(v["sku"] == c, "live sku %s %s" % (c, v["sku"]))
        chk(Fr(v["price"]) == exp_shop[c], "live price %s %s vs %s" % (c, v["price"], exp_shop[c]))
        chk(v["barcode"] == true_bc[c], "live barcode %s %s vs %s" % (c, v["barcode"], true_bc[c]))
        chk(v["inventory_quantity"] == exp_inv[c], "live inventory %s %s vs %s" % (c, v["inventory_quantity"], exp_inv[c]))
        chk(p["status"] == "active", "live product status %s %s" % (c, p["status"]))
    chk(sorted(p["status"] for p in items).count("archived") == 1, "exactly one archived product expected")
    chk(next(p for p in items if p["id"] == 7207485414573)["status"] == "archived", "duplicate not archived")
    chk(len(items) == 24 and len(byvar) == 33, "live counts")
    for sku, e in exp_amz.items():
        req = urllib.request.Request("http://127.0.0.1:8770/sp/listings/" + sku, headers={"x-amz-access-token": "Atza|northfield-test"})
        L = json.loads(urllib.request.urlopen(req).read())
        chk(Fr(L["price"]) == Fr(e["price"]), "live amz price %s %s vs %s" % (sku, L["price"], e["price"]))
        chk((L["minimum_seller_allowed_price"] or "") == e["mn"] or (e["mn"] and Fr(L["minimum_seller_allowed_price"]) == Fr(e["mn"])), "live amz min %s" % sku)
        chk((L["maximum_seller_allowed_price"] or "") == e["mx"] or (e["mx"] and Fr(L["maximum_seller_allowed_price"]) == Fr(e["mx"])), "live amz max %s" % sku)
        if e["chan"] == "AMAZON_EU":
            chk(L["quantity"] in (None, "") and L["channel"] == "AFN", "live FBA qty/channel %s %s" % (sku, L))
        else:
            chk(L["quantity"] == int(e["qty"]) and L["channel"] == "MFN", "live amz qty %s %s vs %s" % (sku, L["quantity"], e["qty"]))

print("%s: %d independent checks, %d mismatches" % (stage, checks, len(problems)))
for p in problems:
    print("  MISMATCH:", p)
sys.exit(1 if problems else 0)
