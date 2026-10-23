"""Build a weekly report from the sales CSV."""
import csv
import sys


def totals(path):
    out = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            out[row["region"]] = out.get(row["region"], 0) + float(row["amount"])
            out = dict(sorted(out.items()))
    return out


if __name__ == "__main__":
    print(totals(sys.argv[1]))
