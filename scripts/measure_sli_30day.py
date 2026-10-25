#!/usr/bin/env python3
"""Capture daily Prometheus API counters and summarize 30 complete UTC days.

This measures the in-process sre-demo-api RED metrics. It is not an external
availability probe and deliberately never labels its result production accepted.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
SERVICE = 'sre-demo-api'
ROUTES = '/api/(work|dependency)'
SELECTOR = f'service="{SERVICE}",route=~"{ROUTES}"'
QUERIES = {
    'requests': f'sum(increase(sre_api_requests_total{{{SELECTOR}}}[1d]))',
    'server_errors': f'sum(increase(sre_api_requests_total{{{SELECTOR},status=~"5.."}}[1d]))',
    'within_500ms': f'sum(increase(sre_api_request_duration_seconds_bucket{{{SELECTOR},le="0.5"}}[1d]))',
    'latency_count': f'sum(increase(sre_api_request_duration_seconds_count{{{SELECTOR}}}[1d]))',
}


def query_scalar(base_url: str, expression: str, at: datetime) -> float:
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Prometheus URL must be HTTP(S) without embedded credentials')
    endpoint = base_url.rstrip('/') + '/api/v1/query'
    url = endpoint + '?' + urllib.parse.urlencode({'query': expression, 'time': at.isoformat()})
    with urllib.request.urlopen(url, timeout=20) as response:
        body = json.load(response)
    if body.get('status') != 'success' or body.get('data', {}).get('resultType') != 'vector':
        raise ValueError('Prometheus query did not succeed')
    result = body['data']['result']
    if len(result) != 1 or result[0].get('metric') != {}:
        raise ValueError('Prometheus query returned no single aggregate series')
    value = float(result[0]['value'][1])
    if not math.isfinite(value) or value < 0:
        raise ValueError('Prometheus query returned an invalid counter increase')
    return value


def capture(day: date, base_url: str, app_image_digest: str, out_dir: Path) -> Path:
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', app_image_digest):
        raise ValueError('app image digest must be sha256:<64 lowercase hex characters>')
    path = out_dir / f'{day.isoformat()}.json'
    if path.exists():
        raise FileExistsError(path)
    end = datetime.combine(day + timedelta(days=1), time.min, UTC)
    if datetime.now(UTC) < end + timedelta(minutes=5):
        raise ValueError('wait at least five minutes after the UTC day ends')
    values = {name: query_scalar(base_url, expression, end) for name, expression in QUERIES.items()}
    if values['requests'] <= 0 or values['latency_count'] <= 0:
        raise ValueError('daily window has no measured application traffic')
    if values['server_errors'] > values['requests'] + 1e-6:
        raise ValueError('5xx count exceeds total request count')
    if values['within_500ms'] > values['latency_count'] + 1e-6:
        raise ValueError('fast request count exceeds histogram total')
    if abs(values['latency_count'] - values['requests']) > max(1.0, values['requests'] * 0.01):
        raise ValueError('request and latency counter totals differ by more than 1%')
    evidence = {
        'schema_version': 1,
        'day_utc': day.isoformat(),
        'window_start_utc': datetime.combine(day, time.min, UTC).isoformat(),
        'window_end_utc': end.isoformat(),
        'collected_at_utc': datetime.now(UTC).isoformat(),
        'service': SERVICE,
        'app_image_digest': app_image_digest,
        'source': 'Prometheus query API; in-process metrics only',
        'queries': QUERIES,
        'values': values,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as output:
        json.dump(evidence, output, indent=2, sort_keys=True)
        output.write('\n')
    return path


def summarize(directory: Path, end_day: date) -> dict[str, object]:
    days = [end_day - timedelta(days=offset) for offset in range(29, -1, -1)]
    totals = {name: 0.0 for name in QUERIES}
    digests: set[str] = set()
    for day in days:
        path = directory / f'{day.isoformat()}.json'
        with path.open(encoding='utf-8') as source:
            item = json.load(source)
        if item.get('schema_version') != 1 or item.get('day_utc') != day.isoformat():
            raise ValueError(f'invalid daily evidence: {path}')
        expected_start = datetime.combine(day, time.min, UTC).isoformat()
        expected_end = datetime.combine(day + timedelta(days=1), time.min, UTC).isoformat()
        if item.get('window_start_utc') != expected_start or item.get('window_end_utc') != expected_end:
            raise ValueError(f'invalid UTC window: {path}')
        if item.get('service') != SERVICE or item.get('queries') != QUERIES:
            raise ValueError(f'metric contract changed or service mismatch: {path}')
        digest = item.get('app_image_digest', '')
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
            raise ValueError(f'missing image digest: {path}')
        digests.add(digest)
        for name in totals:
            value = item.get('values', {}).get(name)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f'invalid {name}: {path}')
            totals[name] += value
        values = item['values']
        if values['requests'] <= 0 or values['latency_count'] <= 0:
            raise ValueError(f'no measured traffic: {path}')
        if values['server_errors'] > values['requests'] + 1e-6:
            raise ValueError(f'5xx count exceeds requests: {path}')
        if values['within_500ms'] > values['latency_count'] + 1e-6:
            raise ValueError(f'fast count exceeds histogram total: {path}')
        if abs(values['latency_count'] - values['requests']) > max(1.0, values['requests'] * 0.01):
            raise ValueError(f'request and histogram counts differ: {path}')
    if totals['requests'] <= 0 or totals['latency_count'] <= 0:
        raise ValueError('30-day window has no measured application traffic')
    if totals['server_errors'] > totals['requests'] + 1e-6:
        raise ValueError('30-day 5xx count exceeds requests')
    if totals['within_500ms'] > totals['latency_count'] + 1e-6:
        raise ValueError('30-day fast count exceeds histogram total')
    availability = 1 - totals['server_errors'] / totals['requests']
    latency_fraction = totals['within_500ms'] / totals['latency_count']
    return {
        'window_start_utc': days[0].isoformat(),
        'window_end_utc_exclusive': (end_day + timedelta(days=1)).isoformat(),
        'days': 30,
        'app_image_digests': sorted(digests),
        'requests': totals['requests'],
        'server_errors': totals['server_errors'],
        'availability': availability,
        'error_rate': 1 - availability,
        'latency_within_500ms': latency_fraction,
        'proposed_targets_met': {
            'availability_at_least_99_9_percent': availability >= 0.999,
            'server_error_rate_under_1_percent': (1 - availability) < 0.01,
            'at_least_95_percent_within_500ms': latency_fraction >= 0.95,
        },
        'acceptance_status': 'INTERNAL_API_ONLY_EXTERNAL_PROBE_AND_REVIEW_REQUIRED',
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    collect = commands.add_parser('collect', help='capture one completed UTC day')
    collect.add_argument('--day', type=date.fromisoformat, required=True)
    collect.add_argument('--prometheus-url', required=True)
    collect.add_argument('--app-image-digest', required=True)
    collect.add_argument('--out-dir', type=Path, required=True)
    report = commands.add_parser('report', help='summarize 30 contiguous daily files')
    report.add_argument('--end-day', type=date.fromisoformat, required=True)
    report.add_argument('--in-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'collect':
        print(capture(args.day, args.prometheus_url, args.app_image_digest, args.out_dir))
    else:
        print(json.dumps(summarize(args.in_dir, args.end_day), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
