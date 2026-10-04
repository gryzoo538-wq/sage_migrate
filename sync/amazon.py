"""Mock Amazon SP-API client: submit a feed, poll to DONE, fetch the processing report, return row errors."""
import json
import time
import urllib.error
import urllib.request

FEED_TYPE = "POST_FLAT_FILE_PRICEANDQUANTITYONLY_UPDATE_DATA"


class AmazonError(Exception):
    pass


class Amazon:
    def __init__(self, base="http://127.0.0.1:8770", token="Atza|northfield-test", sleep=time.sleep, log=None,
                 max_polls=60, poll_interval=1.0):
        self.base, self.token, self.sleep, self.log = base.rstrip("/"), token, sleep, log
        self.max_polls, self.poll_interval = max_polls, poll_interval

    def request(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method, headers={
            "x-amz-access-token": self.token, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                status, text = r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            status, text = e.code, e.read().decode()
        try:
            parsed = json.loads(text) if text else {}
        except ValueError:
            parsed = {"raw": text}
        if self.log:
            self.log(method, path, body if method != "POST" else {"feedType": body.get("feedType"), "rows": body["content"].count("\n")},
                     status, text[:300])
        if status >= 400:
            raise AmazonError("%s %s -> HTTP %s: %s" % (method, path, status, text[:500]))
        return parsed

    def submit_feed(self, content, feed_type=FEED_TYPE):
        return self.request("POST", "/sp/feeds", {"feedType": feed_type, "content": content})["feedId"]

    def wait_done(self, feed_id):
        for _ in range(self.max_polls):
            st = self.request("GET", "/sp/feeds/%s" % feed_id)
            if st.get("processingStatus") == "DONE":
                return st
            if st.get("processingStatus") in ("FATAL", "CANCELLED"):
                raise AmazonError("feed %s ended %s" % (feed_id, st))
            self.sleep(self.poll_interval)
        raise AmazonError("feed %s not DONE after %d polls" % (feed_id, self.max_polls))

    def report(self, feed_id):
        return self.request("GET", "/sp/feeds/%s/report" % feed_id)

    @staticmethod
    def row_errors(report):
        """Rows whose result is an error. Tolerates a few plausible report shapes."""
        rows = report.get("rows") or report.get("results") or report.get("issues") or []
        errs = []
        for r in rows:
            status = str(r.get("status") or r.get("result-type") or r.get("result") or "").upper()
            if status in ("SUCCESS", "OK", "ACCEPTED", "PROCESSED"):
                continue
            errs.append(r)
        declared = (report.get("summary") or {}).get("errors", 0)
        if declared and not errs:  # summary says errors but rows are in an unknown shape: never swallow them
            errs.append({"summary": report.get("summary")})
        return errs

    def submit_and_check(self, content):
        fid = self.submit_feed(content)
        self.wait_done(fid)
        rep = self.report(fid)
        return fid, rep, self.row_errors(rep)

    def listing(self, sku):
        return self.request("GET", "/sp/listings/%s" % sku)
