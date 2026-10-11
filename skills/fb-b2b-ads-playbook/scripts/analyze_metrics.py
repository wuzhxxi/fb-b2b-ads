#!/usr/bin/env python3
"""Compute descriptive B2B ad metrics from validated, local canonical JSON."""

import argparse
from datetime import date
import json
import math
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

COUNTS = (
    'impressions', 'reach', 'link_clicks', 'landing_page_views',
    'results', 'leads', 'assessed_leads', 'qualified_leads', 'quotes', 'wins',
)
MONEY = ('spend', 'revenue', 'contribution_profit')
FIELDS = COUNTS + MONEY
CONTEXT = (
    'currency', 'timezone', 'date_start', 'date_end', 'grain',
    'attribution_window', 'results_definition',
)


def divide(numerator, denominator, multiplier=1):
    if numerator is None or denominator is None or denominator == 0:
        return None
    value = numerator / denominator * multiplier
    return round(value, 6) if math.isfinite(value) else None


def metrics(row, aligned, include_reach=True):
    g = row.get
    out = {
        'cpm': divide(g('spend'), g('impressions'), 1000),
        'ctr_link_pct': divide(g('link_clicks'), g('impressions'), 100),
        'cpc_link': divide(g('spend'), g('link_clicks')),
        'cost_per_platform_result': divide(g('spend'), g('results')),
        'cpl': divide(g('spend'), g('leads')),
    }
    if include_reach:
        out['frequency'] = divide(g('impressions'), g('reach'))
    for key, numerator, denominator, multiplier in (
        ('assessment_coverage_pct', 'assessed_leads', 'leads', 100),
        ('qualified_rate_assessed_pct', 'qualified_leads', 'assessed_leads', 100),
        ('cpql', 'spend', 'qualified_leads', 1),
        ('quote_rate_qualified_pct', 'quotes', 'qualified_leads', 100),
        ('win_rate_qualified_pct', 'wins', 'qualified_leads', 100),
        ('cac_ad_only', 'spend', 'wins', 1),
        ('roas', 'revenue', 'spend', 1),
        ('contribution_to_ad_spend', 'contribution_profit', 'spend', 1),
    ):
        out[key] = divide(g(numerator), g(denominator), multiplier) if aligned else None
    return out


def validate_context(ctx, label):
    if not isinstance(ctx, dict):
        raise ValueError(f'{label}: context must be an object')
    for key in CONTEXT:
        if not isinstance(ctx.get(key), str) or not ctx[key].strip():
            raise ValueError(f'{label}: missing text context field {key}')
    if not re.fullmatch(r'[A-Z]{3}', ctx['currency']):
        raise ValueError(f'{label}: currency must be an uppercase three-letter code')
    try:
        ZoneInfo(ctx['timezone'])
    except ZoneInfoNotFoundError as exc:
        raise ValueError(
            f'{label}: IANA timezone data is unavailable; install tzdata with '
            '`python -m pip install tzdata`, then rerun'
        ) from exc
    try:
        start, end = date.fromisoformat(ctx['date_start']), date.fromisoformat(ctx['date_end'])
    except ValueError as exc:
        raise ValueError(f'{label}: invalid ISO date') from exc
    if start > end:
        raise ValueError(f'{label}: date_start must not follow date_end')
    if ctx['grain'] not in ('campaign', 'ad_set', 'ad'):
        raise ValueError(f'{label}: grain must be campaign, ad_set or ad')
    for key in ('crm_cohort_aligned', 'rows_disjoint', 'crm_deduplicated'):
        if key in ctx and not isinstance(ctx[key], bool):
            raise ValueError(f'{label}: {key} must be boolean')


def analyze(data):
    if not isinstance(data, dict):
        raise ValueError('input must be an object')
    ctx = data.get('context')
    validate_context(ctx, 'report')
    rows = data.get('rows')
    if not isinstance(rows, list) or not rows:
        raise ValueError('rows must be a non-empty array')
    seen, processed, warnings = set(), [], []
    comparable = True
    for index, source in enumerate(rows):
        label = f'row {index + 1}'
        if not isinstance(source, dict):
            raise ValueError(f'{label}: must be an object')
        row_id = source.get('id')
        if not isinstance(row_id, str) or not row_id.strip():
            raise ValueError(f'{label}: id must be non-empty text')
        if row_id in seen:
            raise ValueError(f'{label}: duplicate id; deduplicate or separate periods')
        seen.add(row_id)
        override = source.get('context', {})
        if not isinstance(override, dict):
            raise ValueError(f'{label}: context override must be an object')
        row_ctx = {**ctx, **override}
        validate_context(row_ctx, label)
        if any(row_ctx[key] != ctx[key] for key in CONTEXT):
            comparable = False
            warnings.append(f'{label}: context differs; report aggregate suppressed')
        normalized = {'id': row_id}
        for key in FIELDS:
            value = source.get(key)
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f'{label}: {key} must be a JSON number or null')
                if not math.isfinite(value):
                    raise ValueError(f'{label}: {key} must be finite')
                if key != 'contribution_profit' and value < 0:
                    raise ValueError(f'{label}: {key} must not be negative')
                if key in COUNTS and int(value) != value:
                    raise ValueError(f'{label}: {key} must be an integer count')
            normalized[key] = value
        for child, parent in (
            ('assessed_leads', 'leads'), ('qualified_leads', 'assessed_leads'),
            ('qualified_leads', 'leads'), ('quotes', 'qualified_leads'),
            ('wins', 'qualified_leads'), ('reach', 'impressions'),
        ):
            if normalized[child] is not None and normalized[parent] is not None:
                if normalized[child] > normalized[parent]:
                    raise ValueError(f'{label}: {child} exceeds {parent}; check definitions')
        aligned = row_ctx.get('crm_cohort_aligned', False)
        if not aligned:
            warnings.append(f'{label}: CRM cohort not confirmed; quality and sales metrics suppressed')
        if not row_ctx.get('crm_deduplicated', False):
            warnings.append(f'{label}: unique CRM leads not confirmed; CPL requires deduplication')
        if normalized['qualified_leads'] is not None and normalized['assessed_leads'] is None:
            warnings.append(f'{label}: assessed_leads missing; quality coverage unknown')
        if normalized['leads'] is not None and normalized['assessed_leads'] is not None:
            pending = normalized['leads'] - normalized['assessed_leads']
            if pending:
                warnings.append(f'{label}: {pending} leads are unassessed; CPQL is provisional')
        calculated = metrics(normalized, aligned)
        if not row_ctx.get('crm_deduplicated', False):
            calculated['cpl'] = None
            for key in ('assessment_coverage_pct', 'qualified_rate_assessed_pct', 'cpql',
                        'quote_rate_qualified_pct', 'win_rate_qualified_pct', 'cac_ad_only'):
                calculated[key] = None
        processed.append({'context': row_ctx, 'counts': normalized, 'metrics': calculated})
    aggregate = None
    disjoint = ctx.get('rows_disjoint', False) and all(
        row['context'].get('rows_disjoint', False) for row in processed
    )
    if comparable and disjoint:
        totals = {}
        for key in FIELDS:
            if key == 'reach':
                continue  # Reach can overlap even when the spend rows are disjoint.
            values = [row['counts'][key] for row in processed]
            total = sum(values) if all(value is not None for value in values) else None
            if total is not None and not math.isfinite(total):
                raise ValueError('aggregate exceeds finite numeric range')
            totals[key] = total
        crm_valid = all(row['context'].get('crm_deduplicated', False) for row in processed)
        aligned = all(row['context'].get('crm_cohort_aligned', False) for row in processed)
        calculated = metrics(totals, aligned, include_reach=False)
        if not crm_valid:
            for key in ('leads', 'assessed_leads', 'qualified_leads', 'quotes', 'wins'):
                totals[key] = None
            calculated = metrics(totals, aligned, include_reach=False)
            warnings.append('CRM totals suppressed: cross-row deduplication not confirmed')
        aggregate = {'counts': totals, 'metrics': calculated}
    else:
        warnings.append('No aggregate: confirm identical context and non-overlapping rows')
    warnings.append('Descriptive metrics only; check sample size, assessment lag and business targets before action')
    return {'context': ctx, 'rows': processed, 'aggregate': aggregate, 'warnings': warnings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = analyze(json.loads(args.input.read_text(encoding='utf-8')))
        rendered = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        if args.output:
            args.output.write_text(rendered, encoding='utf-8')
        else:
            sys.stdout.write(rendered)
    except (ValueError, OSError, OverflowError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
