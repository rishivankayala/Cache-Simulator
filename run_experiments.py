#!/usr/bin/env python3
import argparse
import os
import time
from simulator import run_simulation

def parse_args():
    p = argparse.ArgumentParser(description="Cache Simulator Experiment Runner")
    p.add_argument("--levels", type=int, default=2, help="Number of cache levels (1 or 2).")
    p.add_argument("--l1_policy", type=str, default="LRU", choices=["LRU","FIFO","OPT"])
    p.add_argument("--l2_policy", type=str, default="LRU", choices=["LRU","FIFO","OPT"])
    p.add_argument("--l1_size_kb", type=int, default=32)
    p.add_argument("--l2_size_kb", type=int, default=256)
    p.add_argument("--l1_assoc", type=int, default=8)
    p.add_argument("--l2_assoc", type=int, default=8)
    p.add_argument("--l1_latency_ns", type=int, default=4)
    p.add_argument("--l2_latency_ns", type=int, default=12)
    p.add_argument("--mem_latency_ns", type=int, default=100)
    p.add_argument("--block_size", type=int, default=64)
    p.add_argument("--inclusive", action="store_true", default=True)
    p.add_argument("--n", type=int, default=10000, help="Number of accesses")
    p.add_argument("--address_space_kb", type=int, default=1024)
    p.add_argument("--seq_frac", type=float, default=0.5, help="Fraction of accesses as sequential bursts")
    p.add_argument("--hot_frac", type=float, default=0.3, help="Fraction of accesses targeting hot region")
    p.add_argument("--write_ratio", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--outdir", type=str, default="outputs")
    p.add_argument("--sweep", action="store_true", help="Run L1 policy sweep (LRU/FIFO/OPT) keeping L2 fixed.")
    return p.parse_args()

def main():
    args = parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    events_csv = os.path.join(args.outdir, "events.csv")
    results_csv = os.path.join(args.outdir, "results.csv")

    levels_cfg = [{"size_kb": args.l1_size_kb, "assoc": args.l1_assoc, "latency_ns": args.l1_latency_ns, "policy": args.l1_policy}]
    if args.levels >= 2:
        levels_cfg.append({"size_kb": args.l2_size_kb, "assoc": args.l2_assoc, "latency_ns": args.l2_latency_ns, "policy": args.l2_policy})

    if args.sweep:
        for pol in ["LRU","FIFO","OPT"]:
            levels_cfg[0]["policy"] = pol
            run_id = f"lvl{args.levels}_{pol}_L2{levels_cfg[1]['policy'] if args.levels>=2 else 'NA'}_{int(time.time())}"
            run_simulation(run_id, levels_cfg, args.mem_latency_ns, args.inclusive, args.n, args.address_space_kb,
                           args.block_size, args.seq_frac, args.hot_frac, args.write_ratio, args.seed,
                           events_csv, results_csv)
    else:
        run_id = f"custom_{int(time.time())}"
        run_simulation(run_id, levels_cfg, args.mem_latency_ns, args.inclusive, args.n, args.address_space_kb,
                       args.block_size, args.seq_frac, args.hot_frac, args.write_ratio, args.seed,
                       events_csv, results_csv)

if __name__ == "__main__":
    main()
