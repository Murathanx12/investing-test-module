#!/usr/bin/env bash
# DIAG-PF4-MEMORY-PLACEBO-2 driver: situations-only + N stratified shuffle seeds.
# Runs WAVE-wide concurrently; each arm is its own process so one crash costs
# one arm. Every arm is write-once, so re-running the driver resumes.
cd "$(dirname "$0")/.."
WAVE=${WAVE:-7}
SEEDS=${SEEDS:-20}
run() { python scripts/night3_memory_placebo2.py "$@" \
        > "runs/PF4/memory/logs/$(echo "$*" | tr ' -' '__').log" 2>&1; }

run --mode situations_only &
i=1
while [ $i -le $SEEDS ]; do
  run --mode shuffled --seed $i &
  if [ $(( (i+1) % WAVE )) -eq 0 ]; then wait; fi
  i=$((i+1))
done
wait
echo "ALL MEMORY ARMS DONE"
