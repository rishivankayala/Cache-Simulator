# Cache Simulator (Python) + Tableau

[![CI](https://github.com/rishivankayala/Cache-Simulator/actions/workflows/ci.yml/badge.svg)](https://github.com/rishivankayala/Cache-Simulator/actions/workflows/ci.yml)

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://github.com/rishivankayala/Cache-Simulator)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/rishivankayala/Cache-Simulator)
[![CI Ready](https://img.shields.io/badge/CI-ready-lightgrey.svg)](https://github.com/rishivankayala/Cache-Simulator)

Repository: **https://github.com/rishivankayala/Cache-Simulator**

## What it is
A flexible, educational **cache & memory hierarchy simulator** for experimenting with **replacement policies** (LRU, FIFO, Belady’s OPT) across multi-level inclusive caches (L1→L2→Memory). It generates **Tableau-ready CSVs** and includes **ready-made sweeps** plus KPI deltas to analyze **AMAT, hit/miss rates, evictions, write-backs**, and policy trade‑offs.

## How it works
- **Set-associative caches**, configurable per level: size, associativity, block size, and latency.
- **Replacement policies** per level: `LRU`, `FIFO`, `OPT` (Belady; uses next‑use deques as an analytical upper bound).
- **Inclusive hierarchy** model with simplified write‑back + write‑allocate.
- **Synthetic workload generator** with sequential/hot/random locality controls.
- **Outputs** two CSVs:
  - `outputs/events.csv` — per access: level hit, latency, set indices, writeback flags.
  - `outputs/results.csv` — per run: hit rates, **AMAT**, **MPKI**, evictions, **writebacks**; when using sweeps, includes **ΔAMAT** and **ΔMPKI vs baseline**.

### Design & Efficiency
- **OPT** implemented with **per-level, per-set deques** (tag → deque of future positions). Each access pops current and **peeks** next-use only for candidate tags in the *current set* → reduced memory/time overhead.
- **LRU/FIFO** managed with `OrderedDict` for O(1) updates.
- Tight inner loop and batched CSV writing.

## Requirements
This project is pure Python stdlib for the simulator, with **one optional dependency** for the sweeps summary:
```
# requirements.txt
pandas  # optional: only needed for KPI deltas/summary in run_sweeps.py
```
> If you don’t install `pandas`, sweeps still run and produce CSVs; the KPI delta columns/summary are skipped.

---

## Quick Start

```bash
# Clone
git clone https://github.com/rishivankayala/Cache-Simulator.git
cd Cache-Simulator

# (Optional) venv
python3 -m venv .venv && source .venv/bin/activate

# (Optional) install pandas for KPI deltas (recommended)
pip install -r requirements.txt

# One-click policy sweep (LRU/FIFO/OPT at L1; L2=LRU)
python3 run_experiments.py --sweep

# Explore outputs
head outputs/results.csv
head outputs/events.csv
```

### Makefile shortcuts
```bash
make sweep       # python3 run_experiments.py --sweep
make policies    # python3 run_sweeps.py policies
make assoc       # python3 run_sweeps.py assoc --l1_assoc "2,4,8,16"
make blocks      # python3 run_sweeps.py blocks --block_size "32,64,128"
make workload    # python3 run_sweeps.py workload --seq_frac "0.2,0.5,0.8" --hot_frac "0.1,0.3,0.6"
make clean       # remove CSVs
```

---

## Running Experiments

### Single custom run
```bash
python3 run_experiments.py --levels 2 --l1_policy LRU --l2_policy LRU   --l1_size_kb 32 --l2_size_kb 256 --l1_assoc 8 --l2_assoc 8   --block_size 64 --n 10000 --address_space_kb 1024   --seq_frac 0.5 --hot_frac 0.3 --write_ratio 0.1 --seed 42
```

### Pre-built sweeps (and KPI deltas if pandas is installed)
```bash
# Policy comparison (L1: LRU/FIFO/OPT; L2: LRU)
python3 run_sweeps.py policies

# Associativity sweep (L1 assoc 2,4,8,16)
python3 run_sweeps.py assoc --l1_assoc "2,4,8,16"

# Block size sweep (32,64,128)
python3 run_sweeps.py blocks --block_size "32,64,128"

# Workload shape
python3 run_sweeps.py workload --seq_frac "0.2,0.5,0.8" --hot_frac "0.1,0.3,0.6"
```
Artifacts:
- `outputs/results.csv` — aggregate KPIs (+ deltas when ≥2 runs).
- `outputs/events.csv` — per-access log.
- `outputs/summary.txt` — human-readable ΔAMAT/ΔMPKI summary (if pandas is installed).

---

## Tableau Instructions
- Open `tableau/Tableau_Starter.twb` in Tableau Desktop.
- Relink to `outputs/results.csv` and `outputs/events.csv` when prompted.
- See `tableau/dashboards.md` for field list, calculated fields, and dashboard ideas.

**New fields (v3+):**
- From `events.csv`: `writeback_L1`, `writeback_L2` (0/1 per access).
- From `results.csv`: `writebacks_L1`, `writebacks_L2`, `delta_amat_ns_vs_base`, `delta_mpki_vs_base`.

**Dashboard ideas:**
- **Policy Comparison:** Avg `amat_ns` by `policy_L1`, color by `policy_L2`; add `delta_amat_ns_vs_base` labels.
- **Latency Breakdown:** Distribution of `total_latency_ns` filtered by `level_hit`.
- **Miss/Write-back Analysis:** `evictions_*` & `writebacks_*` vs AMAT.

---

## Suggested Test Cases

**Policy comparisons**  
```bash
python3 run_sweeps.py policies
```
Expect: OPT raises L1 hits, lowers AMAT vs LRU/FIFO.

**Associativity sweep**  
```bash
python3 run_sweeps.py assoc --l1_assoc "2,4,8,16"
```
Expect: Fewer conflict misses as associativity increases (diminishing returns).

**Block size sensitivity**  
```bash
python3 run_sweeps.py blocks --block_size "32,64,128"
```
Trade-off: Overfetch vs streaming benefit.

**Workload shape**  
```bash
python3 run_sweeps.py workload --seq_frac "0.2,0.5,0.8" --hot_frac "0.1,0.3,0.6"
```

**Write-intensive**  
```bash
python3 run_experiments.py --write_ratio 0.6 --n 12000
```

**Reproducibility**  
```bash
python3 run_experiments.py --seed 123 --n 8000
python3 run_experiments.py --seed 123 --n 8000
```

---

## Git Steps (Commit & Push)

Initialize and push this project to your repo (**one-time**):
```bash
git init
git add .
git commit -m "Initial commit: cache simulator (LRU/FIFO/OPT), optimized OPT, sweeps, Tableau, docs"
git branch -M main
git remote add origin https://github.com/rishivankayala/Cache-Simulator.git
git push -u origin main
```

Future updates:
```bash
git add -A
git commit -m "Update experiments/docs"
git push
```

---

## License
MIT