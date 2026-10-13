"""HTTP-based catalog reconciliation with optimistic concurrency and measured results.

Designed for authenticated JSON endpoints with an explicit URL allowlist and
an operator-controlled writeback flag. No implicit LLM or fabricated success.
"""
import hashlib
import json
import time
from dataclasses import dataclass
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from .catalog import report

@dataclass(frozen=True)
class Endpoint:
    url: str
    token: str
    timeout_seconds: float = 10.0

    def __post_init__(self):
        parsed = urlsplit(self.url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname:
            raise ValueError('invalid HTTP endpoint')
        if parsed.scheme != 'https' and parsed.hostname not in ('127.0.0.1', 'localhost', '::1'):
            raise ValueError('HTTPS required for non-loopback hosts')
        if not self.token:
            raise ValueError('endpoint access token is required')

def call(endpoint: Endpoint, method='GET', payload=None, version=None):
    headers = {'Authorization': 'Bearer ' + endpoint.token, 'Accept': 'application/json'}
    if payload is not None:
        headers['Content-Type'] = 'application/json'
    if version is not None:
        headers['If-Match'] = version
    body = None if payload is None else json.dumps(payload, sort_keys=True).encode()
    req = Request(endpoint.url, method=method, headers=headers, data=body)
    start = time.perf_counter_ns()
    try:
        with urlopen(req, timeout=endpoint.timeout_seconds) as response:
            raw = response.read(16 * 1024 * 1024 + 1)
            if len(raw) > 16 * 1024 * 1024:
                raise ValueError('response over size limit')
            return {'status': response.status, 'body': json.loads(raw),
                    'etag': response.headers.get('ETag'),
                    'duration_ms': round((time.perf_counter_ns()-start)/1e6,3),
                    'sha256': hashlib.sha256(raw).hexdigest()}
    except HTTPError as exc:
        raise RuntimeError(f'HTTP {exc.code} for {method} {endpoint.url}') from exc

def synchronize(catalog: Endpoint, channel: Endpoint, *, writeback=False):
    """Fetch both live endpoints; write only if explicitly enabled and versioned.

    Endpoint contract: GET returns JSON array of catalog/product objects. PUT
    accepts {"products": [...]} and requires If-Match with prior response ETag.
    The channel must apply atomic compare-and-swap and reject stale ETags.
    """
    source = call(catalog)
    observed = call(channel)
    if not isinstance(source['body'], list) or not isinstance(observed['body'], list):
        raise ValueError('GET endpoints must return JSON arrays')
    before = report(source['body'], observed['body'])
    evidence = {'catalog_digest':source['sha256'], 'channel_digest_before':observed['sha256'],
                'catalog_fetch_ms':source['duration_ms'],
                'channel_fetch_ms':observed['duration_ms'],
                'before':before, 'writeback_requested':writeback,
                'writeback_performed':False, 'verified':before['status']=='PASS'}
    if before['status']=='PASS' or not writeback:
        return evidence
    if not observed['etag']:
        raise ValueError('writeback prohibited without channel ETag')
    if any(item['field'] in ('catalog_record','page') for item in before['findings']):
        raise ValueError('writeback prohibited for missing or extra catalog identities')
    current = {p['sku']:dict(p) for p in observed['body']}
    for authoritative in source['body']:
        if authoritative['sku'] not in current:
            raise ValueError('unknown channel SKU')
        for field in ('title','description','price','currency','availability','image_url'):
            if field not in authoritative or authoritative[field] is None:
                raise ValueError(f'missing authoritative field {field}')
            current[authoritative['sku']][field] = authoritative[field]
    update = call(channel, method='PUT', payload={'products':list(current.values())},
                  version=observed['etag'])
    after = call(channel)
    final = report(source['body'], after['body'])
    evidence.update(writeback_performed=True, update_status=update['status'],
                    channel_digest_after=after['sha256'],
                    after=final, verified=final['status']=='PASS')
    return evidence
