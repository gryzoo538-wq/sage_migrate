"""Minimal Shopify Admin API client: auth, Link-header pagination, 429 handling, clear 422 errors."""
import json
import re
import time
import urllib.error
import urllib.request

API = "/admin/api/2024-07"


class ShopifyError(Exception):
    def __init__(self, status, method, path, body):
        self.status, self.method, self.path, self.body = status, method, path, body
        super().__init__("%s %s -> HTTP %s: %s" % (method, path, status, body))


class ValidationError(ShopifyError):
    """HTTP 422: Shopify rejected the payload; .body holds the field errors."""


def parse_next_link(header):
    if not header:
        return None
    for part in header.split(","):
        m = re.search(r'<([^>]+)>\s*;\s*rel="?next"?', part)
        if m:
            return m.group(1)
    return None


class Shopify:
    def __init__(self, base="http://127.0.0.1:8770", token="shpat_test_northfield",
                 sleep=time.sleep, log=None, max_retries=8):
        self.base, self.token, self.sleep, self.log = base.rstrip("/"), token, sleep, log
        self.max_retries = max_retries

    def _url(self, path):
        return path if path.startswith("http") else self.base + path

    def request(self, method, path, body=None):
        """Returns (parsed_json, headers). Retries on 429 after Retry-After."""
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(self.max_retries + 1):
            req = urllib.request.Request(self._url(path), data=data, method=method, headers={
                "X-Shopify-Access-Token": self.token, "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req) as r:
                    payload, status, headers = r.read(), r.status, r.headers
            except urllib.error.HTTPError as e:
                payload, status, headers = e.read(), e.code, e.headers
            text = payload.decode() if payload else ""
            if status == 429:
                wait = float(headers.get("Retry-After", "1"))
                self._log(method, path, body, 429, "retry in %ss" % wait)
                self.sleep(wait)
                continue
            try:
                parsed = json.loads(text) if text else {}
            except ValueError:
                parsed = {"raw": text}
            self._log(method, path, body, status, text[:300])
            if status == 422:
                raise ValidationError(status, method, path, parsed.get("errors", parsed))
            if status >= 400:
                raise ShopifyError(status, method, path, parsed)
            return parsed, headers
        raise ShopifyError(429, method, path, "still rate limited after %d retries" % self.max_retries)

    def _log(self, method, path, body, status, result):
        if self.log:
            self.log(method, path, body, status, result)

    def paginate(self, path, key):
        """Follow Link rel=next until exhausted; returns list of items under `key`."""
        items, nxt = [], path
        while nxt:
            data, headers = self.request("GET", nxt)
            items.extend(data.get(key, []))
            nxt = parse_next_link(headers.get("Link"))
        return items

    def products(self, limit=10):
        return self.paginate(API + "/products.json?limit=%d" % limit, "products")

    def update_variant(self, vid, fields):
        return self.request("PUT", API + "/variants/%s.json" % vid, {"variant": fields})[0]

    def update_product(self, pid, fields):
        return self.request("PUT", API + "/products/%s.json" % pid, {"product": fields})[0]

    def set_inventory(self, item_id, available, location_id=7001):
        return self.request("POST", API + "/inventory_levels/set.json", {
            "location_id": int(location_id), "inventory_item_id": int(item_id), "available": int(available)})[0]
