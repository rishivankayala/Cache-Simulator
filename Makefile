.PHONY: sweep policies assoc blocks workload clean
sweep:
	python3 run_experiments.py --sweep

policies:
	python3 run_sweeps.py policies

assoc:
	python3 run_sweeps.py assoc --l1_assoc "2,4,8,16"

blocks:
	python3 run_sweeps.py blocks --block_size "32,64,128"

workload:
	python3 run_sweeps.py workload --seq_frac "0.2,0.5,0.8" --hot_frac "0.1,0.3,0.6"

clean:
	rm -f outputs/*.csv outputs/*.txt
