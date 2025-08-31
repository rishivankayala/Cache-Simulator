# Interview Talking Points (STAR)

**Situation** — Ad‑hoc performance questions around memory behavior were hard to answer without tooling.
**Task** — Build a flexible cache simulator + visualization to evaluate policies and identify bottlenecks.
**Action** — Implemented multi‑level inclusive caches (set‑associative) in Python with LRU/FIFO/OPT; added write‑back + write‑allocate, per‑access event logs, and aggregated metrics. Generated Tableau dashboards to compare policies and highlight hot sets.
**Result** — Demonstrated **AMAT reduction** and **miss‑rate improvements** vs FIFO; LRU tracked OPT closely on mixed workloads. Dashboard revealed conflict‑heavy sets and the effect of associativity/policy on evictions.

**Key Metrics to Read Off Your CSVs**
- AMAT (ns): `results.csv[amat_ns]`
- Hit rate (L1/L2/overall): `results.csv[l1_hit_rate], [l2_hit_rate], [overall_hit_rate]`
- MPKI: `results.csv[mpki]`
- Evictions: `results.csv[evictions_L1], [evictions_L2]`

**Proof Points**
- “In the L1 policy sweep, **OPT** improved overall miss rate by ~{Y}% vs **FIFO**, lowering **AMAT** by ~{X} ns.”
- “Heatmap of `set_index_L1` vs miss frequency exposed conflict in sets {S}, prompting an associativity increase test.”
