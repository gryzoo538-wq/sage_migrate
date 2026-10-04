#!/usr/bin/env python3
"""Mock channel APIs for Northfield Home & Garden: Shopify Admin REST (subset) and Amazon SP-API Feeds/Listings (subset).
Run: python3 mock_channels/server.py   (http://127.0.0.1:8770). Treat as a black box: HTTP only."""
import json, zlib, base64, re, time, os, threading, argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
HERE=os.path.dirname(os.path.abspath(__file__)); SF=os.path.join(HERE,"state.json")
ap=argparse.ArgumentParser(); ap.add_argument("--port",type=int,default=8770); A=ap.parse_args()
LOCK=threading.Lock(); HITS=[]
def init():
    if os.path.exists(SF): return json.load(open(SF))
    s=json.loads(zlib.decompress(base64.b64decode(open(os.path.join(HERE,"fixtures.bin")).read()))); s["feeds"]={}; return s
S=init()
def save(): json.dump(S,open(SF,"w"),indent=1)
def ean_ok(b): return bool(re.fullmatch(r"\d{13}",b)) and (10-sum(int(d)*(3 if i%2 else 1) for i,d in enumerate(b[:12]))%10)%10==int(b[12])
PRICE=re.compile(r"^\d+\.\d{2}$")
HDR=["sku","price","minimum-seller-allowed-price","maximum-seller-allowed-price","quantity","handling-time","fulfillment-channel"]
class H(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def send(self,code,obj,hdr=None):
        b=json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type","application/json")
        for k,v in (hdr or {}).items(): self.send_header(k,v)
        self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def body(self):
        try: return json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))) or b"{}")
        except Exception: return None
    def shop(self):
        if self.headers.get("X-Shopify-Access-Token")!="shpat_test_northfield": self.send(401,{"errors":"[API] Invalid API key or access token"}); return False
        with LOCK:
            now=time.time(); HITS[:]=[t for t in HITS if now-t<1.0]
            if len(HITS)>=4: self.send(429,{"errors":"Exceeded 4 calls per second for api client. Reduce request rates to resume uninterrupted service."},{"Retry-After":"1.0"}); return False
            HITS.append(now)
        return True
    def amz(self):
        if self.headers.get("x-amz-access-token")!="Atza|northfield-test": self.send(403,{"errors":[{"code":"Unauthorized"}]}); return False
        return True
    def do_GET(self):
        p=urlparse(self.path); q=parse_qs(p.query); path=p.path
        if path.startswith("/admin/"):
            if not self.shop(): return
            if path=="/admin/api/2024-07/products.json":
                lim=min(int(q.get("limit",["10"])[0]),10); off=int(base64.urlsafe_b64decode(q.get("page_info",["MA=="])[0]).decode())
                prods=S["shopify"]["products"]; page=prods[off:off+lim]; hdr={}
                if off+lim<len(prods): hdr["Link"]=f'<http://127.0.0.1:{A.port}/admin/api/2024-07/products.json?limit={lim}&page_info={base64.urlsafe_b64encode(str(off+lim).encode()).decode()}>; rel="next"'
                return self.send(200,{"products":page},hdr)
            if path=="/admin/api/2024-07/locations.json": return self.send(200,{"locations":[{"id":7001,"name":"Northfield Warehouse"}]})
            return self.send(404,{"errors":"Not Found"})
        if path.startswith("/sp/"):
            if not self.amz(): return
            m=re.fullmatch(r"/sp/feeds/(\w+)",path)
            if m:
                f=S["feeds"].get(m.group(1))
                if not f: return self.send(404,{"errors":[{"code":"NotFound"}]})
                f["polls"]+=1; st=["IN_QUEUE","IN_PROGRESS"][f["polls"]-1] if f["polls"]<=2 else "DONE"; save()
                return self.send(200,{"feedId":m.group(1),"processingStatus":st})
            m=re.fullmatch(r"/sp/feeds/(\w+)/report",path)
            if m:
                f=S["feeds"].get(m.group(1))
                if not f or f["polls"]<3: return self.send(400,{"errors":[{"code":"InvalidInput","message":"Report not available until processingStatus is DONE"}]})
                return self.send(200,f["report"])
            m=re.fullmatch(r"/sp/listings/([\w\-]+)",path)
            if m:
                l=S["amazon"].get(m.group(1))
                return self.send(200,dict(sku=m.group(1),**l)) if l else self.send(404,{"errors":[{"code":"NotFound"}]})
        self.send(404,{"errors":"Not Found"})
    def do_PUT(self):
        p=urlparse(self.path).path
        if not p.startswith("/admin/") or not self.shop(): return None if p.startswith("/admin/") else self.send(404,{})
        b=self.body()
        m=re.fullmatch(r"/admin/api/2024-07/variants/(\d+)\.json",p)
        if m:
            v=[v for pr in S["shopify"]["products"] for v in pr["variants"] if str(v["id"])==m.group(1)]
            if not v: return self.send(404,{"errors":"Not Found"})
            if not b or "variant" not in b: return self.send(400,{"errors":{"variant":"Required parameter missing or invalid"}})
            u=b["variant"]; err={}
            if "price" in u and not (isinstance(u["price"],str) and PRICE.match(u["price"])): err["price"]=["must be a string with 2 decimals, e.g. \"12.99\""]
            if "barcode" in u and u["barcode"] and not ean_ok(str(u["barcode"])): err["barcode"]=["is not a valid EAN-13"]
            bad=set(u)-{"price","barcode","sku","grams","compare_at_price","id"}
            if bad: err["base"]=[f"unsupported fields: {sorted(bad)}"]
            if err: return self.send(422,{"errors":err})
            for k in ("price","barcode","sku","grams","compare_at_price"):
                if k in u: v[0][k]=u[k]
            save(); return self.send(200,{"variant":v[0]})
        m=re.fullmatch(r"/admin/api/2024-07/products/(\d+)\.json",p)
        if m:
            pr=[x for x in S["shopify"]["products"] if str(x["id"])==m.group(1)]
            if not pr: return self.send(404,{"errors":"Not Found"})
            st=(b or {}).get("product",{}).get("status")
            if st not in ("active","draft","archived"): return self.send(422,{"errors":{"status":["is not included in the list"]}})
            pr[0]["status"]=st; save(); return self.send(200,{"product":pr[0]})
        self.send(404,{"errors":"Not Found"})
    def do_POST(self):
        p=urlparse(self.path).path; b=self.body()
        if p=="/admin/api/2024-07/inventory_levels/set.json":
            if not self.shop(): return
            v=[v for pr in S["shopify"]["products"] for v in pr["variants"] if b and v["inventory_item_id"]==b.get("inventory_item_id")]
            if not b or b.get("location_id")!=7001 or not v: return self.send(422,{"errors":["location_id and a valid inventory_item_id are required"]})
            a=b.get("available")
            if not isinstance(a,int) or a<0: return self.send(422,{"errors":["available must be a non-negative integer"]})
            v[0]["inventory_quantity"]=a; save(); return self.send(200,{"inventory_level":{"inventory_item_id":v[0]["inventory_item_id"],"location_id":7001,"available":a}})
        if p=="/sp/feeds":
            if not self.amz(): return
            if not b or b.get("feedType")!="POST_FLAT_FILE_PRICEANDQUANTITYONLY_UPDATE_DATA" or not isinstance(b.get("content"),str):
                return self.send(400,{"errors":[{"code":"InvalidInput","message":"feedType POST_FLAT_FILE_PRICEANDQUANTITYONLY_UPDATE_DATA and string content required"}]})
            lines=[l for l in b["content"].replace("\r\n","\n").split("\n") if l.strip()]
            res=[]; ok=0
            if not lines or lines[0].split("\t")!=HDR:
                rep={"summary":{"processed":0,"successful":0,"errors":1},"results":[{"row":1,"sku":"","status":"ERROR","message":"Header row must be exactly: "+"\\t".join(HDR)}]}
            else:
                for i,l in enumerate(lines[1:],start=2):
                    c=(l.split("\t")+[""]*7)[:7]; sku,pr,mn,mx,qt,ht,fc=[x.strip() for x in c]; L=S["amazon"].get(sku); e=[]
                    if not L: e.append("SKU not found in your catalogue")
                    else:
                        if not PRICE.match(pr): e.append("price must have exactly 2 decimals")
                        if mn and not PRICE.match(mn): e.append("minimum-seller-allowed-price must have 2 decimals")
                        if mx and not PRICE.match(mx): e.append("maximum-seller-allowed-price must have 2 decimals")
                        if not e:
                            if mn and float(pr)<float(mn): e.append("price is below minimum-seller-allowed-price")
                            if mx and float(pr)>float(mx): e.append("price is above maximum-seller-allowed-price")
                        if L["channel"]=="AFN":
                            if qt: e.append("Quantity cannot be updated for Fulfilled by Amazon SKUs")
                            if fc!="AMAZON_EU": e.append("fulfillment-channel must be AMAZON_EU for this SKU")
                            if ht: e.append("handling-time must be blank for Fulfilled by Amazon SKUs")
                        else:
                            if not re.fullmatch(r"\d+",qt or "x"): e.append("quantity must be a non-negative integer")
                            if fc!="DEFAULT": e.append("fulfillment-channel must be DEFAULT for this SKU")
                            if not re.fullmatch(r"\d+",ht or "x") or not 1<=int(ht)<=30: e.append("handling-time must be 1-30")
                    if e: res.append({"row":i,"sku":sku,"status":"ERROR","message":"; ".join(e)})
                    else:
                        L.update(price=pr,minimum_seller_allowed_price=mn,maximum_seller_allowed_price=mx)
                        if L["channel"]=="MFN": L["quantity"]=int(qt)
                        ok+=1
                rep={"summary":{"processed":len(lines)-1,"successful":ok,"errors":len(res)},"results":res}
            fid="F"+str(50000+len(S["feeds"])); S["feeds"][fid]={"polls":0,"report":rep}; save()
            return self.send(202,{"feedId":fid})
        self.send(404,{"errors":"Not Found"})
print(f"Mock channel APIs on http://127.0.0.1:{A.port}",flush=True)
ThreadingHTTPServer(("127.0.0.1",A.port),H).serve_forever()
