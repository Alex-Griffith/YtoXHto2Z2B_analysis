import unittest

from yhbbzz.analysis import SEQUENTIAL_STAGES, _normalization_info


class NormalizationTest(unittest.TestCase):
    def test_missing_mc_metadata_is_explicit(self):
        result = _normalization_info(True, {"cross_section_pb": 1.0})
        self.assertEqual(result["status"], "missing_metadata")
        self.assertIsNone(result["scale_per_gen_weight"])
        self.assertEqual(result["missing_fields"], ["luminosity_fb", "sum_gen_weight"])

    def test_base_mc_normalization(self):
        result = _normalization_info(True, {
            "cross_section_pb": 2.0,
            "luminosity_fb": 10.0,
            "sum_gen_weight": 100.0,
        })
        self.assertEqual(result["status"], "base_normalization_available")
        self.assertEqual(result["scale_per_gen_weight"], 200.0)

    def test_data_uses_unit_weight(self):
        result = _normalization_info(False, {})
        self.assertEqual(result["status"], "data_unit_weight")
        self.assertEqual(result["scale_per_gen_weight"], 1.0)

    def test_sequential_stage_order_is_stable(self):
        self.assertEqual(SEQUENTIAL_STAGES[0], "all")
        self.assertEqual(SEQUENTIAL_STAGES[-1], "higgs_mass_window")
        self.assertEqual(len(SEQUENTIAL_STAGES), len(set(SEQUENTIAL_STAGES)))


if __name__ == "__main__":
    unittest.main()
