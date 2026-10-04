"""Apply shopify_updates.csv and submit amazon_price_quantity.txt, logging every call to a push log.

usage: python3 sync/push.py --shopify output/phase1/shopify_updates.csv --feed output/phase1/amazon_price_quantity.txt \
           --log output/phase1/push_log.csv [--baseline-feed previous_feed.txt] [--shopify-only | --amazon-only]
Only fields whose new value differs from the current value are sent; Amazon rows identical to the baseline are skipped.
"""
import argparse
import csv
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from amazon import Amazon, AmazonError  # noqa: E402
from shopify import Shopify, ShopifyError, ValidationError  # noqa: E402


class PushLog:
    def __init__(self, path, append=False):
        self.path = path
        new = not (append and os.path.exists(path))
        self.f = open(path, "a" if append else "w", newline="")
        self.w = csv.writer(self.f)
        if new:
            self.w.writerow(["timestamp", "system", "method", "path", "request", "http_status", "result"])

    def logger(self, system):
        def _log(method, path, body, status, result):
            self.w.writerow([datetime.datetime.utcnow().isoformat(timespec="seconds"), system, method, path,
                             "" if body is None else str(body), status, str(result).replace("\n", " ")])
            self.f.flush()
        return _log


def read_feed(path):
    with open(path, newline="") as f:
        lines = f.read().splitlines()
    return lines[0], lines[1:]


def push_shopify(client, csv_path):
    errors, calls = [], 0
    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))
    seen_products = set()
    for r in rows:
        v = {}
        if r["new_sku"] != r["current_sku"]:
            v["sku"] = r["new_sku"]
        if r["new_price"] != r["current_price"]:
            v["price"] = r["new_price"]
        if r["new_barcode"] != r["current_barcode"]:
            v["barcode"] = r["new_barcode"]
        try:
            if v:
                client.update_variant(r["variant_id"], v)
                calls += 1
            if r["new_inventory"] != r["current_inventory"]:
                client.set_inventory(r["inventory_item_id"], int(r["new_inventory"]))
                calls += 1
            if r["new_status"] != r["current_status"] and r["product_id"] not in seen_products:
                seen_products.add(r["product_id"])
                client.update_product(r["product_id"], {"status": r["new_status"]})
                calls += 1
        except ValidationError as e:
            errors.append((r["variant_id"], r["stock_code"], "422", e.body))
        except ShopifyError as e:
            errors.append((r["variant_id"], r["stock_code"], str(e.status), e.body))
    return calls, errors


def push_amazon(client, feed_path, baseline=None):
    header, rows = read_feed(feed_path)
    if baseline:
        _, old = read_feed(baseline)
        old = set(old)
        rows = [r for r in rows if r not in old]
    if not rows:
        return None, None, []
    content = header + "\n" + "\n".join(rows) + "\n"
    fid, rep, errs = client.submit_and_check(content)
    return fid, rep, errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shopify")
    ap.add_argument("--feed")
    ap.add_argument("--baseline-feed")
    ap.add_argument("--log", required=True)
    ap.add_argument("--append-log", action="store_true")
    ap.add_argument("--base", default="http://127.0.0.1:8770")
    a = ap.parse_args()
    log = PushLog(a.log, a.append_log)
    ok = True
    if a.shopify:
        calls, errs = push_shopify(Shopify(a.base, log=log.logger("shopify")), a.shopify)
        print("shopify: %d successful calls, %d rejected" % (calls, len(errs)))
        for e in errs:
            ok = False
            print("  REJECTED variant %s (%s): HTTP %s %s" % e)
    if a.feed:
        fid, rep, errs = push_amazon(Amazon(a.base, log=log.logger("amazon")), a.feed, a.baseline_feed)
        print("amazon: feed %s, %d row errors" % (fid, len(errs)))
        for e in errs:
            ok = False
            print("  ROW ERROR:", e)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
