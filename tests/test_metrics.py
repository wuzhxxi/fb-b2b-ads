import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'fb-b2b-ads-playbook'
spec = importlib.util.spec_from_file_location('metrics', SKILL / 'scripts' / 'analyze_metrics.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((SKILL / 'assets' / 'sample-metrics.json').read_text())

    def test_quality_and_weighted_aggregation(self):
        result = module.analyze(self.data)
        a, b = [r['metrics'] for r in result['rows']]
        self.assertEqual(a['cpl'], 2.5)
        self.assertEqual(a['cpql'], 50)
        self.assertAlmostEqual(b['cpql'], 100 / 6, places=5)
        self.assertEqual(result['aggregate']['metrics']['cpql'], 25)
        self.assertAlmostEqual(result['aggregate']['metrics']['ctr_link_pct'], 300 / 18000 * 100, places=5)
        self.assertNotIn('reach', result['aggregate']['counts'])
        self.assertNotIn('frequency', result['aggregate']['metrics'])

    def test_missing_is_not_zero_and_zero_is_not_infinity(self):
        del self.data['rows'][0]['leads']
        self.data['rows'][0]['qualified_leads'] = 0
        self.data['rows'][0]['quotes'] = 0
        result = module.analyze(self.data)
        self.assertIsNone(result['aggregate']['counts']['leads'])
        self.assertIsNone(result['rows'][0]['metrics']['cpql'])
        self.assertIsNone(result['rows'][0]['metrics']['cac_ad_only'])
        self.assertEqual(result['rows'][0]['metrics']['qualified_rate_assessed_pct'], 0)

    def test_context_conflict_suppresses_aggregate(self):
        for key, value in [('currency', 'EUR'), ('attribution_window', '1-day click'), ('grain', 'campaign')]:
            data = copy.deepcopy(self.data)
            data['rows'][1]['context'] = {key: value}
            self.assertIsNone(module.analyze(data)['aggregate'])

    def test_duplicate_and_impossible_counts_fail(self):
        self.data['rows'].append(copy.deepcopy(self.data['rows'][0]))
        with self.assertRaises(ValueError):
            module.analyze(self.data)
        self.data['rows'].pop()
        self.data['rows'][0]['qualified_leads'] = 41
        with self.assertRaises(ValueError):
            module.analyze(self.data)

    def test_no_cohort_no_quality_metrics(self):
        self.data['context']['crm_cohort_aligned'] = False
        result = module.analyze(self.data)
        self.assertIsNone(result['aggregate']['metrics']['cpql'])
        self.assertIsNone(result['aggregate']['metrics']['roas'])
        self.assertAlmostEqual(result['aggregate']['metrics']['cpl'], 200 / 55, places=5)

    def test_pending_leads_are_not_invalid(self):
        self.data['rows'][0]['assessed_leads'] = 10
        result = module.analyze(self.data)
        self.assertEqual(result['rows'][0]['metrics']['qualified_rate_assessed_pct'], 20)
        self.assertEqual(result['rows'][0]['metrics']['assessment_coverage_pct'], 25)
        self.assertTrue(any('unassessed' in w for w in result['warnings']))

    def test_unconfirmed_dedup_and_overlap(self):
        self.data['context']['crm_deduplicated'] = False
        result = module.analyze(self.data)
        self.assertIsNone(result['aggregate']['counts']['leads'])
        self.assertIsNone(result['rows'][0]['metrics']['cpql'])
        self.data['context']['rows_disjoint'] = False
        self.assertIsNone(module.analyze(self.data)['aggregate'])
        self.data['context']['rows_disjoint'] = True
        self.data['rows'][0]['context'] = {'rows_disjoint': False}
        self.assertIsNone(module.analyze(self.data)['aggregate'])

    def test_invalid_numeric_values_and_dates(self):
        for value in (-1, float('nan'), float('inf'), True, '$20'):
            data = copy.deepcopy(self.data)
            data['rows'][0]['spend'] = value
            with self.assertRaises(ValueError):
                module.analyze(data)
        self.data['context']['date_start'] = '2026-09-09'
        with self.assertRaises(ValueError):
            module.analyze(self.data)


if __name__ == '__main__':
    unittest.main()
