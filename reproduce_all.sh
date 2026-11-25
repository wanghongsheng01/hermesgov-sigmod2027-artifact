#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "=================================================================="
echo " HermesGov — ACM SIGMOD 2027 Industrial Track Reproducibility Suite"
echo "=================================================================="

echo "[1/4] Running 105-Table OneData Recursive Planner, 8-Dim Gate Ablation & AST SQL Guard..."
python3 benchmarks/run_planner_and_guard_ablation.py

echo "[2/4] Running Public TPC-DS 36-Table Layered Micro-Benchmark & Fault Ablation..."
python3 benchmarks/run_tpcds_public_benchmark.py

echo "[3/4] Running 10,000-Topology Formal Model Checker & 36->1,599-Table Scale Sweep..."
python3 benchmarks/run_stage2_formal_and_scale_bench.py

echo "[4/4] Regenerating All 4 Paper Vector Figures (figures/*.pdf)..."
python3 benchmarks/generate_paper_figures.py

echo "=================================================================="
echo " ALL REPRODUCIBLE BENCHMARKS & PAPER FIGURES SUCCEEDED (EXIT 0)"
echo "=================================================================="
