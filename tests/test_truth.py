import unittest

from yhbbzz.truth import classify_signal


class TruthTest(unittest.TestCase):
    def test_xyh_ybb_h4l(self):
        # X -> Y H; Y -> b b; H -> Z Z; each Z -> l l
        pdg = [45, 35, 25, 5, -5, 23, 23, 11, -11, 13, -13]
        mothers = [-1, 0, 0, 1, 1, 2, 2, 5, 5, 6, 6]
        status = [2, 2, 2, 23, 23, 2, 2, 1, 1, 1, 1]
        result = classify_signal(pdg, status, mothers)
        self.assertTrue(result["valid_signal"])
        self.assertEqual(result["n_h_leptons"], 4)
        self.assertEqual(result["n_y_b_quarks"], 2)

    def test_h_to_bb_is_not_y_to_bb(self):
        pdg = [45, 35, 25, 5, -5]
        mothers = [-1, 0, 0, 2, 2]
        status = [2, 2, 2, 23, 23]
        result = classify_signal(pdg, status, mothers)
        self.assertFalse(result["has_ybb"])


if __name__ == "__main__":
    unittest.main()
