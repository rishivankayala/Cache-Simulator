#!/usr/bin/env python3
import csv
import json
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from collections import OrderedDict, defaultdict, deque

# ---------------- Policies ----------------
class Policy:
    LRU = "LRU"
    FIFO = "FIFO"
    OPT = "OPT"

@dataclass
class CacheLine:
    tag: int
    valid: bool = True
    dirty: bool = False
    last_used: int = 0
    inserted_at: int = 0

class CacheSet:
    def __init__(self, assoc: int, policy: str):
        self.assoc = assoc
        self.policy = policy
        self.lines: Dict[int, CacheLine] = {}         # tag -> line
        # order structures for LRU/FIFO
        self.lru_order: "OrderedDict[int, None]" = OrderedDict()
        self.fifo_order: "OrderedDict[int, None]" = OrderedDict()

    def access_update(self, tag: int):
        if self.policy == Policy.LRU:
            if tag in self.lru_order:
                self.lru_order.move_to_end(tag, last=True)

    def insert_line(self, line: CacheLine):
        self.lines[line.tag] = line
        if self.policy == Policy.LRU:
            self.lru_order[line.tag] = None
        elif self.policy == Policy.FIFO:
            self.fifo_order[line.tag] = None

    def remove_line(self, tag: int):
        self.lines.pop(tag, None)
        self.lru_order.pop(tag, None)
        self.fifo_order.pop(tag, None)

    def choose_victim(self, next_use_lookup) -> Optional[int]:
        """
        Return victim tag for eviction, based on policy.
        - For LRU/FIFO: use maintained orders.
        - For OPT: consult next_use_lookup(tag) -> next access index or None (never).
        """
        if len(self.lines) < self.assoc:
            return None  # no need to evict
        if self.policy == Policy.LRU:
            return next(iter(self.lru_order))
        if self.policy == Policy.FIFO:
            return next(iter(self.fifo_order))
        # OPT: farthest next use (or never used)
        farthest = -1
        victim = None
        for tag in self.lines.keys():
            nxt = next_use_lookup(tag)  # int or None
            score = nxt if nxt is not None else float("inf")
            if score > farthest:
                farthest = score
                victim = tag
        return victim

class CacheLevel:
    def __init__(self, name: str, size_kb: int, assoc: int, block_size: int, latency_ns: int, policy: str):
        self.name = name
        self.size_kb = size_kb
        self.assoc = assoc
        self.block_size = block_size
        self.latency_ns = latency_ns
        self.policy = policy

        self.num_lines = (size_kb * 1024) // block_size
        self.num_sets = max(1, self.num_lines // assoc)
        self.sets = [CacheSet(assoc, policy) for _ in range(self.num_sets)]

        # stats
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.writebacks = 0  # dirty evictions

    def _index_tag(self, address: int) -> Tuple[int, int, int]:
        block_addr = address // self.block_size
        index = block_addr % self.num_sets
        tag = block_addr // self.num_sets
        return block_addr, index, tag

    def probe(self, address: int) -> Tuple[bool, int, int, int]:
        """Return (hit?, block_addr, set_index, tag). Does not modify sets."""
        block_addr, idx, tag = self._index_tag(address)
        hit = tag in self.sets[idx].lines
        return hit, block_addr, idx, tag

    def access(self, address: int, is_write: bool, tick: int, next_use_provider) -> Tuple[bool, int, int, Optional[int], bool]:
        """
        Access this level.
        Returns (hit, set_index, tag, evicted_tag_or_None, writeback_happened)
        """
        hit, block_addr, idx, tag = self.probe(address)
        cset = self.sets[idx]
        if hit:
            self.hits += 1
            line = cset.lines[tag]
            line.last_used = tick
            if is_write:
                line.dirty = True
            cset.access_update(tag)
            return True, idx, tag, None, False

        # miss path
        self.misses += 1
        evicted = None
        writeback = False

        if len(cset.lines) >= cset.assoc:
            # Provide a closure for OPT to query "next use" for each tag currently in set
            def next_use_lookup(existing_tag: int):
                return next_use_provider(idx, existing_tag)  # may return None

            victim_tag = cset.choose_victim(next_use_lookup)
            if victim_tag is not None:
                victim = cset.lines[victim_tag]
                if victim.dirty:
                    self.writebacks += 1
                    writeback = True
                cset.remove_line(victim_tag)
                self.evictions += 1
                evicted = victim_tag

        # Insert fetched line
        newline = CacheLine(tag=tag, last_used=tick, inserted_at=tick, dirty=is_write)
        cset.insert_line(newline)
        return False, idx, tag, evicted, writeback

class Memory:
    def __init__(self, latency_ns: int):
        self.latency_ns = latency_ns

class CacheHierarchy:
    def __init__(self, levels: List[CacheLevel], memory: Memory, inclusive: bool = True):
        self.levels = levels
        self.memory = memory
        self.inclusive = inclusive

    def access(self, address: int, is_write: bool, tick: int, next_use_providers):
        """
        Perform an access across levels.
        next_use_providers: list (per level) of callables (set_idx, tag)->next_use_pos or None.
        Returns tuple:
            (level_hit_name, path_latency_ns, set_indices, evictions, writebacks)
        """
        cum_latency = 0
        set_indices = []
        evictions = []
        writebacks = []
        level_hit_name = "Memory"

        for lvl_idx, level in enumerate(self.levels):
            # Access this level (which may insert on miss)
            provider = next_use_providers[lvl_idx]
            hit, idx, tag, evicted, writeback = level.access(address, is_write, tick, provider)
            set_indices.append((level.name, idx))
            evictions.append((level.name, evicted))
            writebacks.append((level.name, writeback))
            cum_latency += level.latency_ns
            if hit:
                level_hit_name = level.name
                break
        else:
            cum_latency += self.memory.latency_ns

        return level_hit_name, cum_latency, set_indices, evictions, writebacks

# ---------------- Workload ----------------
def generate_synthetic_trace(n: int, address_space_kb: int, block_size: int, seq_frac: float, hot_frac: float, write_ratio: float, seed: int = 42):
    rnd = random.Random(seed)
    space_bytes = address_space_kb * 1024
    hot_space = max(block_size, int(0.1 * space_bytes))

    trace = []
    access_id = 0
    i = 0
    while i < n:
        mode = rnd.random()
        if mode < seq_frac:
            start = rnd.randrange(0, max(block_size, space_bytes - 64*block_size), block_size)
            length = rnd.randint(8, 64)  # burst in blocks
            for j in range(length):
                if i >= n:
                    break
                addr = (start + j * block_size) % space_bytes
                op = "W" if rnd.random() < write_ratio else "R"
                trace.append((access_id, op, addr))
                access_id += 1
                i += 1
        elif mode < seq_frac + hot_frac:
            base = rnd.randrange(0, max(1, space_bytes - hot_space), block_size)
            addr = base + rnd.randrange(0, max(1, hot_space // block_size)) * block_size
            op = "W" if rnd.random() < write_ratio else "R"
            trace.append((access_id, op, addr))
            access_id += 1
            i += 1
        else:
            addr = rnd.randrange(0, max(1, space_bytes // block_size)) * block_size
            op = "W" if rnd.random() < write_ratio else "R"
            trace.append((access_id, op, addr))
            access_id += 1
            i += 1
    return trace

# ---------------- OPT next-use provider (memory efficient) ----------------
def build_next_use_deques(trace, levels_cfg, block_size):
    """
    For each cache level, build: list[num_sets] of dict[tag]->deque of future positions.
    We then pop-left the current position at runtime and peek left for "next use".
    """
    # Precompute for each level separately (mapping depends on num_sets / block_size)
    per_level = []
    for lvl in levels_cfg:
        num_lines = (lvl["size_kb"]*1024)//block_size
        num_sets = max(1, num_lines // lvl["assoc"])
        sets = [defaultdict(deque) for _ in range(num_sets)]
        per_level.append(sets)

    # Append all positions
    for pos, (_, _, addr) in enumerate(trace):
        for li, lvl in enumerate(levels_cfg):
            num_lines = (lvl["size_kb"]*1024)//block_size
            num_sets = max(1, num_lines // lvl["assoc"])
            block = addr // block_size
            idx = block % num_sets
            tag = block // num_sets
            per_level[li][idx][tag].append(pos)
    return per_level

# ---------------- Simulation runner ----------------
def run_simulation(run_id: str, levels_cfg: List[dict], mem_latency_ns: int, inclusive: bool,
                   n: int, address_space_kb: int, block_size: int, seq_frac: float, hot_frac: float, write_ratio: float, seed: int,
                   events_csv_path: str, results_csv_path: str):
    # Build levels
    levels = []
    for i, cfg in enumerate(levels_cfg):
        levels.append(CacheLevel(
            name=f"L{i+1}",
            size_kb=cfg["size_kb"],
            assoc=cfg["assoc"],
            block_size=block_size,
            latency_ns=cfg["latency_ns"],
            policy=cfg["policy"]
        ))
    memory = Memory(latency_ns=mem_latency_ns)
    hierarchy = CacheHierarchy(levels, memory, inclusive=inclusive)

    trace = generate_synthetic_trace(n, address_space_kb, block_size, seq_frac, hot_frac, write_ratio, seed)

    # Build next-use deques once (memory efficient)
    next_use_deques = build_next_use_deques(trace, levels_cfg, block_size)

    # Prepare CSV writers
    events_f = open(events_csv_path, "w", newline="")
    evw = csv.writer(events_f)
    evw.writerow(["run_id","access_id","op","address","block_addr","policy_L1","policy_L2","level_hit","total_latency_ns",
                  "l1_hit","l2_hit","set_index_L1","set_index_L2","writeback_L1","writeback_L2"])

    total_latency_sum = 0
    overall_hits = 0

    for access_id, op, addr in trace:
        is_write = (op == "W")

        # For each level, pop-left this position from the deque for the *current* block so "next use" is truly future
        providers = []
        for li, lvl in enumerate(levels):
            # compute set/tag for this address at level li
            block_addr = addr // block_size
            num_sets = lvl.num_sets
            idx = block_addr % num_sets
            tag = block_addr // num_sets
            dq = next_use_deques[li][idx][tag]
            if dq and dq[0] == access_id:
                dq.popleft()

            if lvl.policy == Policy.OPT:
                # Capture references so the closure sees current li
                def make_provider(level_index):
                    def provider(set_index, some_tag):
                        d = next_use_deques[level_index][set_index].get(some_tag)
                        if not d:
                            return None
                        return d[0] if len(d) > 0 else None
                    return provider
                providers.append(make_provider(li))
            else:
                # Non-OPT policies don't need next-use; return a provider that always says "unknown"
                providers.append(lambda _si, _t: None)

        level_hit, latency, set_indices, evictions, writebacks = hierarchy.access(addr, is_write, access_id, providers)
        total_latency_sum += latency
        if level_hit != "Memory":
            overall_hits += 1

        set_idx_L1 = set_indices[0][1] if len(set_indices) > 0 else ""
        set_idx_L2 = set_indices[1][1] if len(set_indices) > 1 else ""
        l1_hit = 1 if level_hit == "L1" else 0
        l2_hit = 1 if level_hit == "L2" else 0
        block_addr = addr // block_size
        pol1 = levels[0].policy if len(levels)>=1 else ""
        pol2 = levels[1].policy if len(levels)>=2 else ""

        wb1 = 1 if len(writebacks)>0 and writebacks[0][1] else 0
        wb2 = 1 if len(writebacks)>1 and writebacks[1][1] else 0

        evw.writerow([run_id, access_id, op, addr, block_addr, pol1, pol2, level_hit, latency,
                      l1_hit, l2_hit, set_idx_L1, set_idx_L2, wb1, wb2])

    events_f.close()

    # Aggregate results
    n_accesses = len(trace)
    amat = total_latency_sum / n_accesses if n_accesses else 0.0
    mpki = (n_accesses - overall_hits) / (n_accesses/1000.0) if n_accesses else 0.0

    # Write results row
    write_header = False
    try:
        open(results_csv_path, "r").close()
    except FileNotFoundError:
        write_header = True

    with open(results_csv_path, "a", newline="") as rf:
        import csv as _csv
        rw = _csv.writer(rf)
        if write_header:
            rw.writerow(["run_id","n_accesses","policy_L1","policy_L2","l1_hit_rate","l2_hit_rate","overall_hit_rate","amat_ns","mpki",
                         "evictions_L1","evictions_L2","writebacks_L1","writebacks_L2","config_json"])
        l1 = levels[0] if len(levels) > 0 else None
        l2 = levels[1] if len(levels) > 1 else None
        l1_hit_rate = l1.hits / n_accesses if l1 else 0.0
        l2_hit_rate = l2.hits / n_accesses if l2 else 0.0
        overall_hit_rate = overall_hits / n_accesses if n_accesses else 0.0
        cfg = {
            "levels": levels_cfg,
            "memory_latency_ns": mem_latency_ns,
            "inclusive": inclusive,
            "workload": {
                "n": n,
                "address_space_kb": address_space_kb,
                "block_size": block_size,
                "seq_frac": seq_frac,
                "hot_frac": hot_frac,
                "write_ratio": write_ratio,
                "seed": seed
            }
        }
        rw.writerow([
            run_id, n_accesses,
            levels[0].policy if l1 else "",
            levels[1].policy if l2 else "",
            l1_hit_rate, l2_hit_rate, overall_hit_rate,
            amat, mpki,
            l1.evictions if l1 else 0,
            l2.evictions if l2 else 0,
            l1.writebacks if l1 else 0,
            l2.writebacks if l2 else 0,
            json.dumps(cfg)
        ])

if __name__ == "__main__":
    print("Use run_experiments.py or run_sweeps.py to run experiments and generate CSVs.")
