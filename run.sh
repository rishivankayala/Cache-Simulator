#!/usr/bin/env bash
set -euo pipefail
python3 run_experiments.py --sweep
echo "Done. See outputs/results.csv and outputs/events.csv"
