"""Read-only conformance probe for a real external catalog/publishing service.

Requires explicit nonloopback HTTPS endpoints and independently fetched live
records. Does not make mutation or fabricate deployment qualification.
"""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
from .http_integration import Endpoint,call
from .catalog import report
from .live_e2e import atomic_json

REQUIRED=("sku","title","description","price","currency","availability","image_url")

def probe(config):
    catalog=Endpoint(**config["catalog"]["authoritative"])
    channel=Endpoint(**config["catalog"]["published"])
    if any(urlsplit(endpoint.url).scheme!="https" or
           urlsplit(endpoint.url).hostname in ("127.0.0.1","localhost","::1")
           for endpoint in (catalog,channel)):
        raise ValueError("external conformance requires non-loopback HTTPS services")
    source=call(catalog)
    published=call(channel)
    if not isinstance(source["body"],list) or not isinstance(published["body"],list):
        raise ValueError("external GET must return product arrays")
    if not published["etag"]:
        raise ValueError("external publishing endpoint lacks versioned ETag")
    for label,data in (("source",source["body"]),("published",published["body"])):
        for product in data:
            if not isinstance(product,dict) or any(k not in product for k in REQUIRED):
                raise ValueError(label+" record violates field contract")
    comparison=report(source["body"],published["body"])
    return {"scope":"EXTERNAL_READ_ONLY_PREFLIGHT_NOT_PRODUCTION_SIGNOFF",
            "status":"PASS","source_sha256":source["sha256"],
            "published_sha256":published["sha256"],"channel_etag":published["etag"],
            "source_count":len(source["body"]),"published_count":len(published["body"]),
            "reconciliation":comparison,
            "catalog_fetch_ms":source["duration_ms"],
            "channel_fetch_ms":published["duration_ms"]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    try:
        result=probe(json.loads(Path(args.config).read_text(encoding="utf-8")))
        atomic_json(args.output,result)
        print(json.dumps({"status":result["status"],"scope":result["scope"],"report":args.output}))
        return 0
    except Exception as exc:
        result={"status":"FAILED","error_type":type(exc).__name__}
        atomic_json(args.output,result)
        print(json.dumps(result))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
