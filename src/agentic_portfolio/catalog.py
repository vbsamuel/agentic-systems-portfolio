"""Deterministic catalog-to-publication reconciliation with explicit review gates."""
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

FIELDS = ('title', 'description', 'price', 'currency', 'availability', 'image_url')
CRITICAL = frozenset({'price', 'currency', 'availability'})

@dataclass(frozen=True)
class Finding:
    sku: str
    field: str
    expected: Any
    observed: Any
    severity: str
    disposition: str = 'REVIEW_REQUIRED'


def reconcile(catalog: list[dict], published: list[dict]) -> list[Finding]:
    """Fail closed on duplicate IDs, incomplete authoritative data and uncertain values."""
    def index(rows: list[dict], side: str) -> dict[str, dict]:
        result = {}
        for row in rows:
            sku = row.get('sku')
            if not isinstance(sku, str) or not sku.strip():
                raise ValueError(f'{side}: missing SKU')
            if sku in result:
                raise ValueError(f'{side}: duplicate SKU {sku}')
            result[sku] = row
        return result

    truth, pages = index(catalog, 'catalog'), index(published, 'published')
    issues = []
    for sku, source in sorted(truth.items()):
        page = pages.get(sku)
        if page is None:
            issues.append(Finding(sku, 'page', 'present', 'missing', 'high'))
            continue
        for field in FIELDS:
            if source.get(field) is None:
                issues.append(Finding(sku, field, 'authoritative value required', None, 'high'))
                continue
            expected, actual = source[field], page.get(field)
            if field == 'price' and actual is not None:
                try:
                    expected, actual = Decimal(str(expected)), Decimal(str(actual))
                except InvalidOperation:
                    issues.append(Finding(sku, field, str(expected), str(actual), 'high'))
                    continue
            if expected != actual:
                issues.append(Finding(sku, field, str(expected), str(actual), 'high' if field in CRITICAL else 'medium'))
    for sku in sorted(pages.keys() - truth.keys()):
        issues.append(Finding(sku, 'catalog_record', 'present', 'missing', 'high'))
    return issues


def report(catalog: list[dict], published: list[dict]) -> dict:
    findings = reconcile(catalog, published)
    return {'compared_catalog_products': len(catalog), 'findings': [asdict(x) for x in findings],
            'status': 'REVIEW_REQUIRED' if findings else 'PASS', 'auto_published': False}
