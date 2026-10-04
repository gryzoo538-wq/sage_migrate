import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from amazon import Amazon  # noqa: E402
from shopify import Shopify, ValidationError, parse_next_link  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    calls = []
    script = {}  # path-prefix -> list of (status, headers, body) to pop

    def log_message(self, *a):
        pass

    def _serve(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n).decode() if n else ""
        Handler.calls.append((self.command, self.path, body, dict(self.headers)))
        for prefix, queue in Handler.script.items():
            if self.path.startswith(prefix) and queue:
                status, headers, payload = queue.pop(0)
                data = json.dumps(payload).encode()
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
        self.send_response(404)
        self.end_headers()

    do_GET = do_PUT = do_POST = _serve


class ServerCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Handler)
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_port
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        Handler.calls, Handler.script = [], {}


class Pagination(ServerCase):
    def test_link_header_parsing(self):
        h = '<http://x/a?page_info=2>; rel="previous", <http://x/a?page_info=3>; rel="next"'
        self.assertEqual(parse_next_link(h), "http://x/a?page_info=3")
        self.assertIsNone(parse_next_link('<http://x/a>; rel="previous"'))
        self.assertIsNone(parse_next_link(None))

    def test_follows_all_pages(self):
        nxt = lambda n: {"Link": '<%s/admin/api/2024-07/products.json?limit=2&page_info=%d>; rel="next"' % (self.base, n)}
        Handler.script["/admin/api/2024-07/products.json"] = [
            (200, nxt(2), {"products": [{"id": 1}, {"id": 2}]}),
            (200, nxt(3), {"products": [{"id": 3}, {"id": 4}]}),
            (200, {}, {"products": [{"id": 5}]})]
        got = Shopify(self.base).products(limit=2)
        self.assertEqual([p["id"] for p in got], [1, 2, 3, 4, 5])
        self.assertEqual(len(Handler.calls), 3)
        self.assertEqual(Handler.calls[0][3].get("X-Shopify-Access-Token"), "shpat_test_northfield")


class Retry429(ServerCase):
    def test_honours_retry_after_then_succeeds(self):
        Handler.script["/admin"] = [(429, {"Retry-After": "3"}, {}), (429, {"Retry-After": "1.5"}, {}),
                                    (200, {}, {"products": []})]
        sleeps = []
        s = Shopify(self.base, sleep=sleeps.append)
        self.assertEqual(s.products(), [])
        self.assertEqual(sleeps, [3.0, 1.5])
        self.assertEqual(len(Handler.calls), 3)

    def test_gives_up(self):
        Handler.script["/admin"] = [(429, {"Retry-After": "1"}, {})] * 5
        s = Shopify(self.base, sleep=lambda x: None, max_retries=2)
        with self.assertRaises(Exception):
            s.products()
        self.assertEqual(len(Handler.calls), 3)

    def test_422_reported_clearly(self):
        Handler.script["/admin"] = [(422, {}, {"errors": {"price": ["bad"]}})]
        with self.assertRaises(ValidationError) as c:
            Shopify(self.base).update_variant(1, {"price": "x"})
        self.assertEqual(c.exception.body, {"price": ["bad"]})
        self.assertIn("422", str(c.exception))

    def test_inventory_ids_sent_as_integers(self):
        Handler.script["/admin"] = [(200, {}, {})]
        Shopify(self.base).set_inventory("123", "4")
        sent = json.loads(Handler.calls[0][2])
        self.assertEqual(sent, {"location_id": 7001, "inventory_item_id": 123, "available": 4})


class Feeds(ServerCase):
    def test_submit_poll_report_errors(self):
        Handler.script["/sp/feeds/F1/report"] = [(200, {}, {"summary": {"errors": 1}, "results": [
            {"sku": "A", "status": "ERROR", "message": "min > price"}, {"sku": "B", "status": "SUCCESS"}]})]
        Handler.script["/sp/feeds/F1"] = [(200, {}, {"processingStatus": "IN_QUEUE"}),
                                          (200, {}, {"processingStatus": "IN_PROGRESS"}),
                                          (200, {}, {"processingStatus": "DONE"})]
        Handler.script["/sp/feeds"] = [(202, {}, {"feedId": "F1"})]
        sleeps = []
        a = Amazon(self.base, sleep=sleeps.append)
        fid, rep, errs = a.submit_and_check("sku\tprice\nA\t1\n")
        self.assertEqual(fid, "F1")
        self.assertEqual(len(sleeps), 2)
        self.assertEqual([e["sku"] for e in errs], ["A"])
        post = [c for c in Handler.calls if c[0] == "POST"][0]
        self.assertIn("POST_FLAT_FILE_PRICEANDQUANTITYONLY_UPDATE_DATA", post[2])
        self.assertEqual({k.lower(): v for k, v in post[3].items()}.get("x-amz-access-token"), "Atza|northfield-test")

    def test_summary_errors_never_swallowed(self):
        errs = Amazon.row_errors({"summary": {"errors": 2}, "results": []})
        self.assertTrue(errs)
        self.assertEqual(Amazon.row_errors({"summary": {"errors": 0}, "results": []}), [])


if __name__ == "__main__":
    unittest.main()
