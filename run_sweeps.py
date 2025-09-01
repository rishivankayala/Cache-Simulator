#!/usr/bin/env python3
"""
Convenience sweeps + KPI summary.
Examples:
  python run_sweeps.py policies
  python run_sweeps.py assoc --l1_assoc "2,4,8,16"
  python run_sweeps.py blocks --block_size "32,64,128"
"""
import argparse
import os
import time

from simulator import run_simulation

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["policies","assoc","blocks","workload"], help="Sweep dimension")
    p.add_argument("--outdir", default="outputs")
    # Base config
    p.add_argument("--levels", type=int, default=2)
    p.add_argument("--l2_policy", default="LRU")
    p.add_argument("--l1_size_kb", type=int, default=32)
    p.add_argument("--l2_size_kb", type=int, default=256)
    p.add_argument("--l1_assoc", type=str, default="8")
    p.add_argument("--l2_assoc", type=int, default=8)
    p.add_argument("--l1_latency_ns", type=int, default=4)
    p.add_argument("--l2_latency_ns", type=int, default=12)
    p.add_argument("--mem_latency_ns", type=int, default=100)
    p.add_argument("--block_size", type=str, default="64")
    p.add_argument("--inclusive", action="store_true", default=True)
    p.add_argument("--n", type=int, default=10000)
    p.add_argument("--address_space_kb", type=int, default=1024)
    p.add_argument("--seq_frac", type=str, default="0.5")
    p.add_argument("--hot_frac", type=str, default="0.3")
    p.add_argument("--write_ratio", type=str, default="0.1")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()

def to_int_or_float_list(s):
    out = []
    for tok in s.split(","):
        tok = tok.strip()
        if "." in tok:
            out.append(float(tok))
        else:
            out.append(int(tok))
    return out

def main():
    args = parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    events_csv = os.path.join(args.outdir, "events.csv")
    results_csv = os.path.join(args.outdir, "results.csv")

    # reset outputs for clarity (remove if they exist so headers get written correctly)
    for pth in [events_csv, results_csv]:
        try:
            os.remove(pth)
        except FileNotFoundError:
            pass

    def levels_cfg_template(block_size, l1_assoc, l1_policy="LRU"):
        return [
            {"size_kb": args.l1_size_kb, "assoc": int(l1_assoc), "latency_ns": args.l1_latency_ns, "policy": l1_policy, "block_size": int(block_size)},
            {"size_kb": args.l2_size_kb, "assoc": args.l2_assoc, "latency_ns": args.l2_latency_ns, "policy": args.l2_policy, "block_size": int(block_size)}
        ]

    if args.mode == "policies":
        bs = int(to_int_or_float_list(args.block_size)[0])
        l1a = int(to_int_or_float_list(args.l1_assoc)[0])
        for pol in ["LRU","FIFO","OPT"]:
            levels_cfg = levels_cfg_template(bs, l1a, l1_policy=pol)
            run_id = f"pol_{pol}_{int(time.time())}"
            run_simulation(run_id, levels_cfg, args.mem_latency_ns, args.inclusive, args.n, args.address_space_kb,
                           bs, float(args.seq_frac), float(args.hot_frac), float(args.write_ratio), args.seed,
                           events_csv, results_csv)

    elif args.mode == "assoc":
        bs = int(to_int_or_float_list(args.block_size)[0])
        for a in to_int_or_float_list(args.l1_assoc):
            levels_cfg = levels_cfg_template(bs, a, l1_policy="LRU")
            run_id = f"assoc_{a}_{int(time.time())}"
            run_simulation(run_id, levels_cfg, args.mem_latency_ns, args.inclusive, args.n, args.address_space_kb,
                           bs, float(args.seq_frac), float(args.hot_frac), float(args.write_ratio), args.seed,
                           events_csv, results_csv)

    elif args.mode == "blocks":
        for bs in to_int_or_float_list(args.block_size):
            bs = int(bs)
            l1a = int(to_int_or_float_list(args.l1_assoc)[0])
            levels_cfg = levels_cfg_template(bs, l1a, l1_policy="LRU")
            run_id = f"block_{bs}_{int(time.time())}"
            run_simulation(run_id, levels_cfg, args.mem_latency_ns, args.inclusive, args.n, args.address_space_kb,
                           bs, float(args.seq_frac), float(args.hot_frac), float(args.write_ratio), args.seed,
                           events_csv, results_csv)

    elif args.mode == "workload":
        bs = int(to_int_or_float_list(args.block_size)[0])
        l1a = int(to_int_or_float_list(args.l1_assoc)[0])
        for seq in to_int_or_float_list(args.seq_frac):
            for hot in to_int_or_float_list(args.hot_frac):
                levels_cfg = levels_cfg_template(bs, l1a, l1_policy="LRU")
                run_id = f"wl_seq{seq}_hot{hot}_{int(time.time())}"
                run_simulation(run_id, levels_cfg, args.mem_latency_ns, args.inclusive, args.n, args.address_space_kb,
                               bs, float(seq), float(hot), float(args.write_ratio), args.seed,
                               events_csv, results_csv)

    # Compute simple KPI deltas vs first row as baseline (if multiple runs)
    try:
        import pandas as pd
        df = pd.read_csv(results_csv)
        required_cols = {"run_id","amat_ns","mpki"}
        if len(df) >= 2 and required_cols.issubset(df.columns):
            base = df.iloc[0]
            df["delta_amat_ns_vs_base"] = df["amat_ns"].astype(float) - float(base["amat_ns"])
            df["delta_mpki_vs_base"] = df["mpki"].astype(float) - float(base["mpki"])
            df.to_csv(results_csv, index=False)
            lines = ["KPI deltas vs baseline: " + str(base.get("run_id","<unknown>"))]
            for _, r in df.iterrows():
                lines.append(f"- {r['run_id']}: ΔAMAT={r['delta_amat_ns_vs_base']:.3f} ns, ΔMPKI={r['delta_mpki_vs_base']:.1f}")
            with open(os.path.join(args.outdir, "summary.txt"), "w") as f:
                f.write("\n".join(lines))
    except Exception as e:
        with open(os.path.join(args.outdir, "summary.txt"), "w") as f:
            f.write(f"Summary not generated due to: {e}\nRuns completed. See outputs/results.csv.")

if __name__ == "__main__":
    main()
