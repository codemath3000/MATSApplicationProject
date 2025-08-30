
import argparse
import csv
from collections import defaultdict
import os
import matplotlib.pyplot as plt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="results csv from experiment.py")
    args = ap.parse_args()
    prefix = os.path.splitext(os.path.basename(args.csv))[0]

    # Read
    rows = []
    with open(args.csv, "r", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            r["snitch"] = int(r["snitch"])
            r["moral"] = int(r["moral"])
            r["evidence"] = int(r["evidence"])
            r["friction"] = int(r["friction"])
            rows.append(r)

    # Plot simple dose-response for each factor, marginalizing the others
    def rate_by(key):
        agg = defaultdict(lambda: [0,0])  # key -> [snitch_sum, count]
        for r in rows:
            k = r[key]
            agg[k][0] += r["snitch"]
            agg[k][1] += 1
        xs = sorted(agg.keys())
        ys = [agg[k][0] / max(1, agg[k][1]) for k in xs]
        return xs, ys

    for key in ["moral","evidence","friction"]:
        xs, ys = rate_by(key)
        plt.figure()
        plt.title("Snitch rate vs " + key)
        plt.xlabel(key + " level")
        plt.ylabel("snitch rate")
        plt.plot(xs, ys, marker="o")
        out = f"{prefix}_plot_{key}.png"
        plt.savefig(out, dpi=160, bbox_inches="tight")
        print("Saved", out)

if __name__ == "__main__":
    main()
