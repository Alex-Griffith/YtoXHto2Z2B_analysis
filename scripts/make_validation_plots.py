#!/usr/bin/env python3
"""Make simple validation-only plots from YH(bb,4l) ntuple outputs."""

import argparse
from pathlib import Path


PLOTS = {
    "massZ1": ("massZ1", 60, 0.0, 150.0),
    "massZ2": ("massZ2", 60, 0.0, 150.0),
    "mass4l": ("mass4l", 80, 70.0, 190.0),
    "nSelectedJet": ("nSelectedJet", 8, -0.5, 7.5),
    "leadingJetPt": ("pTj1", 60, 0.0, 300.0),
    "subleadingJetPt": ("pTj2", 60, 0.0, 300.0),
    "leadingJetBtag": ("btagj1", 50, 0.0, 1.0),
    "subleadingJetBtag": ("btagj2", 50, 0.0, 1.0),
    "massbb": ("massbb", 80, 0.0, 500.0),
    "massbb4l": ("massbb4l", 100, 0.0, 1500.0),
}


def draw_tree_hist(root, tree, plot_name, branch, bins, low, high, outdir, formats):
    if not tree.GetBranch(branch):
        print(f"Skipping {plot_name}: branch {branch} is absent")
        return False
    hist = root.TH1F(f"h_{plot_name}", f";{branch};Events", bins, low, high)
    hist.SetLineWidth(2)
    tree.Draw(f"{branch}>>h_{plot_name}", f"{branch} > -98", "goff")
    canvas = root.TCanvas(f"c_{plot_name}", plot_name, 800, 700)
    canvas.SetFillColorAlpha(root.kWhite, 1.0)
    canvas.SetFillStyle(1001)
    canvas.SetFrameFillColor(root.kWhite)
    canvas.SetTopMargin(0.14)
    hist.Draw("hist")
    label = root.TLatex()
    label.SetNDC(True)
    label.SetTextColor(root.kBlack)
    label.SetTextSize(0.04)
    label.DrawLatex(0.14, 0.94, plot_name)
    label.SetTextSize(0.027)
    label.DrawLatex(0.14, 0.90, "Validation only -- no luminosity or scale-factor normalization")
    for ext in formats:
        canvas.SaveAs(str(outdir / f"{plot_name}.{ext}"))
    return True


def draw_cutflow(root, source, outdir, formats):
    hist = source.Get("Cutflow")
    if not hist:
        print("Skipping cutflow: Cutflow histogram is absent")
        return False
    canvas = root.TCanvas("c_cutflow", "cutflow", 1000, 700)
    canvas.SetFillColorAlpha(root.kWhite, 1.0)
    canvas.SetFillStyle(1001)
    canvas.SetFrameFillColor(root.kWhite)
    canvas.SetTopMargin(0.14)
    canvas.SetBottomMargin(0.32)
    hist.SetLineWidth(2)
    hist.SetTitle(";;Events")
    hist.LabelsOption("v", "X")
    hist.Draw("hist text0")
    label = root.TLatex()
    label.SetNDC(True)
    label.SetTextColor(root.kBlack)
    label.SetTextSize(0.04)
    label.DrawLatex(0.12, 0.94, "Event cutflow")
    label.SetTextSize(0.027)
    label.DrawLatex(0.12, 0.90, "Validation only -- no luminosity or scale-factor normalization")
    for ext in formats:
        canvas.SaveAs(str(outdir / f"cutflow.{ext}"))
    return True


def main():
    parser = argparse.ArgumentParser(description="Create validation plots from output ROOT ntuples")
    parser.add_argument("root_files", nargs="+")
    parser.add_argument("-o", "--output-dir", default="plots/validation")
    parser.add_argument("--formats", default="png,pdf")
    args = parser.parse_args()

    import ROOT

    ROOT.gROOT.SetBatch(True)
    ROOT.gStyle.SetOptStat(0)
    formats = [item.strip() for item in args.formats.split(",") if item.strip()]
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    produced = []
    for root_file in args.root_files:
        path = Path(root_file)
        sample_dir = outdir / path.stem
        sample_dir.mkdir(parents=True, exist_ok=True)
        source = ROOT.TFile.Open(str(path))
        if not source or source.IsZombie():
            print(f"Skipping {root_file}: cannot open")
            continue
        tree = source.Get("Events")
        if not tree:
            print(f"Skipping {root_file}: Events tree is absent")
            source.Close()
            continue
        if draw_cutflow(ROOT, source, sample_dir, formats):
            produced.append(sample_dir / f"cutflow.{formats[0]}")
        for plot_name, spec in PLOTS.items():
            if draw_tree_hist(ROOT, tree, plot_name, *spec, sample_dir, formats):
                produced.append(sample_dir / f"{plot_name}.{formats[0]}")
        source.Close()

    print("Produced plots:")
    for path in produced:
        print(path)


if __name__ == "__main__":
    main()
