# Cache Simulator — Resume Bullets (ATS-Ready)

- **Built a Python cache & memory hierarchy simulator** with configurable N‑level inclusive caches (set‑associative), supporting **LRU, FIFO, and Belady’s OPT** replacement policies.
- **Streamlined system performance analysis** by modeling per‑level latencies, evictions, and write‑back behavior; produced **Tableau‑ready CSVs** (per‑access *events* and aggregated *results*).
- **Reduced simulated AMAT by _{X} ns_ and miss rate by _{Y}%_** using OPT vs FIFO on a 10k‑access mixed‑locality workload; LRU delivered near‑optimal performance with lower complexity. *(Replace {X}/{Y} with your run’s metrics.)*
- **Diagnosed bottlenecks** by visualizing hot sets, conflict misses, and latency distributions in **Tableau**; created dashboards for *Policy Comparison*, *Latency Breakdown*, and *Miss Analysis*.
- **Packaged as a reproducible CLI** with policy sweeps and synthetic workload generator (sequential/hot/random patterns); outputs **AMAT, hit/miss rates, MPKI, evictions** for each run.

## Optional one‑liner
Designed and analyzed a multi‑level cache simulator (LRU/FIFO/OPT) in Python; cut simulated latency and optimized memory usage, presenting findings in Tableau dashboards.
