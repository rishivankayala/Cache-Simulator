# Tableau Setup Guide

## Data Sources
Connect **events.csv** and **results.csv** from the `outputs/` folder.

### `events.csv` (per access)
**Dimensions**
- access_id (Number)
- op (String: R/W)
- level_hit (String: L1/L2/Memory)
- set_index_L1 (Number)
- set_index_L2 (Number)
- block_addr (Number)
- policy_L1 / policy_L2 (String)
- run_id (String)

**Measures**
- total_latency_ns (Number)
- l1_hit (Number: 0/1)
- l2_hit (Number: 0/1)

### `results.csv` (per run)
**Dimensions**
- run_id (String)
- policy_L1, policy_L2 (String)
- config_json (String)

**Measures**
- n_accesses
- l1_hit_rate
- l2_hit_rate
- overall_hit_rate
- amat_ns
- mpki
- evictions_L1
- evictions_L2

## Calculated Fields
- **Overall Miss Rate** (if not provided): `1 - [overall_hit_rate]`
- **AMAT (ns)**: `[amat_ns]`
- **Misses per K**: `[mpki]`

## Dashboard Ideas
1) **Policy Comparison Overview**
   - Bar/Column chart: AMAT (ns) by Policy (policy_L1) — color by policy_L2.
   - Table: hit rates, evictions, MPKI per run_id.

2) **Latency Breakdown**
   - Box/violin (approx with bins): total_latency_ns from `events.csv`, segmented by policy_L1.
   - Highlight L1/L2/Memory hit proportions (stacked bar).

3) **Miss Analysis by Level**
   - Heatmap: set_index vs. miss frequency for L1 to spot conflict-heavy sets.
   - Show distribution of block_addr modulo #sets to illustrate mapping skew.

4) **Working Set Explorer**
   - Line chart: rolling hit rate (window avg of l1_hit) over access_id.
   - Parameter controls to filter access_id ranges and ops (R vs W).

5) **OPT vs Practical Policies**
   - Two KPIs: ΔAMAT(ns) = AMAT(LRU) - AMAT(OPT); ΔMissRate = MissRate(LRU) - MissRate(OPT).

> Tip: Use `run_id` as a high-level filter and `policy_L1`, `policy_L2` as color encoding.


## New Fields (v3)
From `events.csv`:
- **writeback_L1**, **writeback_L2** (0/1 per access)

From `results.csv`:
- **writebacks_L1**, **writebacks_L2**
- **delta_amat_ns_vs_base** (if you used `run_sweeps.py` with multiple runs)
- **delta_mpki_vs_base**

## KPI Sheet Suggestions
- **ΔAMAT vs baseline**: Use `delta_amat_ns_vs_base` — bar chart by `policy_L1` or `run_id`.
- **Writeback cost**: Show `writebacks_L1` + `writebacks_L2` per run; pair with AMAT to discuss trade-offs.
