import unittest

from yhbbzz.hzz4l import _passes_electron_hzz_id, resolve_electron_hzz_id


class FakeTree:
    Electron_pt = [9.0, 20.0, 20.0]
    Electron_eta = [0.2, 1.0, 2.0]
    Electron_deltaEtaSC = [0.0, 0.0, 0.0]
    Electron_mvaHZZIso = [1.50, 0.08, -0.58]
    Electron_mvaIso_WPHZZ = [True, False, True]


class HZZElectronIDSchemaTest(unittest.TestCase):
    def test_prefers_stored_working_point(self):
        branches = {"Electron_mvaHZZIso", "Electron_mvaIso_WPHZZ"}
        self.assertEqual(resolve_electron_hzz_id(branches), "Electron_mvaIso_WPHZZ")
        self.assertTrue(_passes_electron_hzz_id(FakeTree(), 0, "Electron_mvaIso_WPHZZ"))
        self.assertFalse(_passes_electron_hzz_id(FakeTree(), 1, "Electron_mvaIso_WPHZZ"))

    def test_recomputes_working_point_from_v12_score(self):
        mode = resolve_electron_hzz_id({"Electron_mvaHZZIso"})
        self.assertEqual(mode, "Electron_mvaHZZIso_recomputed_WPHZZ")
        self.assertTrue(_passes_electron_hzz_id(FakeTree(), 0, mode))
        self.assertTrue(_passes_electron_hzz_id(FakeTree(), 1, mode))
        self.assertFalse(_passes_electron_hzz_id(FakeTree(), 2, mode))


if __name__ == "__main__":
    unittest.main()
