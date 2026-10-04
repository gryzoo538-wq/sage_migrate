"""Apply client_update/ to copies of the inputs: stocktake counts + discontinuation into a Sage export copy,
Hartley MAP update into supplier_map.csv. Originals are left untouched."""
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = os.path.join(ROOT, "output", "final")
os.makedirs(out, exist_ok=True)
counts = {r["STOCK_CODE"]: r["COUNTED_QTY"] for r in csv.DictReader(open(os.path.join(ROOT, "client_update/stocktake_2026-10-07.csv")))}
DISCONTINUED = ["NHG-3003-S"]
with open(os.path.join(ROOT, "sage_stock_export.csv"), newline="", encoding="utf-8-sig") as f:
    rdr = csv.DictReader(f)
    rows, cols = list(rdr), rdr.fieldnames
for r in rows:
    if r["STOCK_CODE"] in counts:
        r["QTY_IN_STOCK"] = counts[r["STOCK_CODE"]]
    if r["STOCK_CODE"] in DISCONTINUED:
        r["INACTIVE_FLAG"] = "1"
with open(os.path.join(out, "sage_stock_export_updated.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, cols)
    w.writeheader()
    w.writerows(rows)
# values read from the scan HART01_MAP_update.pdf (effective 10 Oct 2026)
MAP_UPDATE = {"HM-WC9-B": "24.99", "HM-WC9-G": "24.99", "HM-WC9-R": "24.99", "HM-SEC-S": "15.49", "HM-BP-LH": "16.99"}
with open(os.path.join(ROOT, "output/phase1/supplier_map.csv"), newline="") as f:
    rdr = csv.DictReader(f)
    srows, scols = list(rdr), rdr.fieldnames
for r in srows:
    if r["part_ref"] in MAP_UPDATE:
        r["MAP"] = MAP_UPDATE[r["part_ref"]]
        r["source_scan"] = "HART01_MAP_update.pdf (supersedes HART01_pricelist_autumn2026.pdf)"
with open(os.path.join(out, "supplier_map.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, scols)
    w.writeheader()
    w.writerows(srows)
print("updated", len(counts), "stock counts,", len(MAP_UPDATE), "MAPs,", len(DISCONTINUED), "discontinued")
