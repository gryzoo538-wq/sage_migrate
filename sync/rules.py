"""Pricing, charm rounding, stock and barcode logic from channel_rules.md (all money in Decimal)."""
import csv
import math
import re
from decimal import Decimal, ROUND_HALF_UP

D = Decimal
CENT = D("0.01")
VAT = {"T1": D("0.20"), "T0": D("0")}
SAFETY_BUFFER = 2
KIT_COMPONENTS = {"NHG-KIT-01": ["NHG-2001", "NHG-2002", "NHG-2003", "NHG-3001"]}


# ---- barcodes ---------------------------------------------------------------
def check_digit(first12):
    digits = [int(c) for c in first12]
    total = sum(d * (3 if i % 2 else 1) for i, d in enumerate(digits))
    return (10 - total % 10) % 10


def valid_ean13(value):
    v = (value or "").strip()
    return len(v) == 13 and v.isdigit() and check_digit(v[:12]) == int(v[12])


def is_mangled(value):
    """Scientific notation or other Excel damage (e.g. 5.06012E+12, 5.06E12)."""
    v = (value or "").strip()
    return bool(re.search(r"[eE][+-]?\d+$", v)) or "." in v


# ---- SKU matching -----------------------------------------------------------
def normalise_sku(sku):
    return re.sub(r"[^A-Z0-9]", "", (sku or "").upper())


def parse_amazon_sku(sku):
    """Strip trailing -FBA and/or -X<n>. Returns (base_sku, pack_qty, is_fba). Any order of the two suffixes."""
    base, pack, fba = sku.strip(), 1, False
    while True:
        m = re.match(r"^(.*)-FBA$", base, re.I)
        if m:
            base, fba = m.group(1), True
            continue
        m = re.match(r"^(.*)-X(\d+)$", base, re.I)
        if m:
            base, pack = m.group(1), int(m.group(2))
            continue
        return base, pack, fba


# ---- stock ------------------------------------------------------------------
def available(in_stock, allocated):
    return max(0, int(in_stock) - int(allocated))


def kit_available(avail_by_code, components=None):
    comps = components or KIT_COMPONENTS["NHG-KIT-01"]
    return min(avail_by_code[c] for c in comps)


def channel_qty(avail, pack=1, inactive=False):
    if inactive:
        return 0
    return max(0, (int(avail) - SAFETY_BUFFER) // int(pack))


# ---- prices -----------------------------------------------------------------
def gross(net, vat_code):
    return (D(str(net)) * (1 + VAT[vat_code])).quantize(CENT, ROUND_HALF_UP)


def shopify_price(gross_price, map_price):
    g = D(str(gross_price))
    return max(g, D(str(map_price))) if map_price not in (None, "") else g


def charm(value):
    """Round UP to the next price ending .99 (x.00-x.99 -> x.99; x.995 -> (x+1).99). Not rounded to pence first."""
    v = D(str(value))
    base = v.to_integral_value(rounding="ROUND_FLOOR")
    target = base + D("0.99")
    return target if v <= target else base + D("1.99")


def load_fee_tiers(path):
    with open(path, newline="") as f:
        return sorted(((D(r["max_weight_kg"]), D(r["fee_gbp"])) for r in csv.DictReader(f)))


def fba_fee(weight_kg, tiers):
    w = D(str(weight_kg))
    for max_w, fee in tiers:
        if max_w >= w:
            return fee
    return tiers[-1][1]


def amazon_price(shop_price, pack=1, fba=False, fee=D("0")):
    p = D(str(shop_price))
    if pack > 1:
        return charm(p * pack * D("0.92") * D("1.08"))
    if fba:
        return charm(p * D("1.08") + D(str(fee)))
    return charm(p * D("1.08"))


def amazon_limits(amz_price, shop_price, map_price, pack=1):
    """(min, max) seller-allowed prices; min blank (None) for multipacks."""
    mx = (D(str(amz_price)) * 2).quantize(CENT)
    if pack > 1:
        return None, mx
    mn = D(str(map_price)) if map_price not in (None, "") else D(str(shop_price))
    return mn.quantize(CENT), mx
