#!/usr/bin/env python3
"""
Runs the building exactly as authored: DOE Reference Medium Office fixed
heating/cooling setpoint schedules (21C occupied heating / 24C occupied
cooling, night/weekend setback) -- the traditional rigid, rule-based BMS
described in the problem statement. No AI in the loop.
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
EPLUS_ROOT = os.environ.get("EPLUS_ROOT", r"C:\EnergyPlusV26-1-0")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--idf", default=os.path.join(ROOT, "idf", "baseline.idf"))
    ap.add_argument("--weather", default=os.path.join(ROOT, "weather", "chicago.epw"))
    ap.add_argument("--out", default=os.path.join(ROOT, "results"))
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    eplus_bin = os.path.join(EPLUS_ROOT, "energyplus.exe")
    cmd = [eplus_bin, "-w", args.weather, "-d", args.out, "-r", args.idf]
    print("Running baseline (traditional rule-based BMS):", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout[-2000:])
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    print(f"Baseline complete. Outputs in {args.out}")


if __name__ == "__main__":
    main()