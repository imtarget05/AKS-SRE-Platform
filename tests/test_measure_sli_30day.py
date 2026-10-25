"""Evidence contract tests for the daily SRE demo API SLI collector."""

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from scripts.measure_sli_30day import QUERIES, capture, summarize

DIGEST = 'sha256:' + 'a' * 64


class ThirtyDaySliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.end_day = date(2026, 9, 30)

    def write_days(self, omit=None, errors=1.0):
        for offset in range(29, -1, -1):
            day = self.end_day - timedelta(days=offset)
            if day == omit:
                continue
            data = {
                'schema_version': 1,
                'day_utc': day.isoformat(),
                'window_start_utc': f'{day.isoformat()}T00:00:00+00:00',
                'window_end_utc': f'{(day + timedelta(days=1)).isoformat()}T00:00:00+00:00',
                'service': 'sre-demo-api',
                'app_image_digest': DIGEST,
                'queries': QUERIES,
                'values': {
                    'requests': 1000.0,
                    'server_errors': errors,
                    'within_500ms': 960.0,
                    'latency_count': 1000.0,
                },
            }
            (self.directory / f'{day.isoformat()}.json').write_text(json.dumps(data))

    def test_sums_all_days_and_never_claims_external_acceptance(self):
        self.write_days()
        result = summarize(self.directory, self.end_day)
        self.assertEqual(result['days'], 30)
        self.assertEqual(result['requests'], 30000)
        self.assertAlmostEqual(result['availability'], 0.999)
        self.assertAlmostEqual(result['latency_within_500ms'], 0.96)
        self.assertTrue(all(result['proposed_targets_met'].values()))
        self.assertIn('EXTERNAL_PROBE', result['acceptance_status'])

    def test_missing_day_never_passes_as_30_day_window(self):
        self.write_days(omit=self.end_day - timedelta(days=5))
        with self.assertRaises(FileNotFoundError):
            summarize(self.directory, self.end_day)

    def test_metric_contract_change_is_rejected(self):
        self.write_days()
        path = self.directory / f'{self.end_day.isoformat()}.json'
        data = json.loads(path.read_text())
        data['queries']['requests'] = 'sum(fake_metric)'
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'contract changed'):
            summarize(self.directory, self.end_day)

    def test_wrong_utc_window_and_no_traffic_are_rejected(self):
        self.write_days()
        path = self.directory / f'{self.end_day.isoformat()}.json'
        data = json.loads(path.read_text())
        data['window_end_utc'] = '2026-10-02T00:00:00+00:00'
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'invalid UTC window'):
            summarize(self.directory, self.end_day)
        data['window_end_utc'] = '2026-10-01T00:00:00+00:00'
        data['values']['requests'] = 0.0
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'no measured traffic'):
            summarize(self.directory, self.end_day)

    @patch('scripts.measure_sli_30day.query_scalar')
    def test_capture_is_bound_to_digest_and_cannot_overwrite(self, query):
        query.side_effect = [1000.0, 0.0, 950.0, 1000.0]
        day = date(2020, 1, 1)
        path = capture(day, 'http://127.0.0.1:9090', DIGEST, self.directory)
        data = json.loads(path.read_text())
        self.assertEqual(data['app_image_digest'], DIGEST)
        self.assertEqual(data['window_start_utc'], '2020-01-01T00:00:00+00:00')
        self.assertEqual(data['window_end_utc'], '2020-01-02T00:00:00+00:00')
        with self.assertRaises(FileExistsError):
            capture(day, 'http://127.0.0.1:9090', DIGEST, self.directory)


if __name__ == '__main__':
    unittest.main()
