import importlib.util, unittest
from pathlib import Path
P=Path(__file__).resolve(); s=importlib.util.spec_from_file_location('m',P.with_name('compare_endminf_current_baseline.py')); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
class BaselineTests(unittest.TestCase):
    def test_contract_is_sparse_and_explicit(self):
        r=m.verify(); self.assertEqual(r['status'],'sparse_baseline'); self.assertEqual(r['unityPhaseRenders']['missingPhases'],['start','transition']); self.assertEqual(len(r['comparisons']),3)
    def test_no_perceptual_claim(self): self.assertFalse(m.verify()['diagnostics']['perceptualEquivalence'])
if __name__=='__main__': unittest.main()
