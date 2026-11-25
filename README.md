# HermesGov — ACM SIGMOD 2027 Industrial Track Artifact (v4.0)

**Paper**: *HermesGov: A Governed Multi-Path Semantic Query Engine and MCP Runtime for Enterprise Layered Data Warehouses*  
**Authors**: Hongsheng Wang (Zhejiang University & Loctek Ergonomic Technology Corp.) and Dazhen Deng (Zhejiang University)

## Repository Contents (Reviewer-Facing Artifacts)
- `benchmarks/run_stage2_formal_and_scale_bench.py`: Automated **10,000-Topology Property-Based Formal Model Checker** verifying Theorems 4.1–4.2 (`10,000/10,000` bounded termination, `0` uncertified primary leaks, `0.0` relative error vs. row-level ground-truth oracle) plus **Multi-Scale Estate Sweep (`36 → 105 → 500 → 1,599` tables × $\rho \in \{0..100\%\}$)** and calibrated Equation (1) silent-corruption model (`seed=42`).
- `benchmarks/run_tpcds_public_benchmark.py`: Reproducible public **TPC-DS** 36-table OneData layered micro-benchmark (1,000 runs/path latency, 180-fault orthogonal gate ablation, 40-case CTE-aware AST SQL Guard; `seed=42`).
- `benchmarks/run_6model_dual_benchmark_llmhub.py`: Dual-warehouse (Loctek 12 traps + Public TPC-DS 12 traps) live caliber-trap evaluation harness across 6 foundation models (`Claude-Opus-5.5`, `GPT-6.2-Sol`, `Gemini-4-Argon`, `Kimi-K3.1-Pro`, `DeepSeek-V4-Pro`, `Qwen3.8-27B`) with SQL-block-aware verification and tenant hygiene checks.
- `results/`: Frozen JSON experimental traces backing Figures 3–4 and Tables 6–7 (`experiments_stage2_formal_scale.json`, `experiments_microbench_results.json`, `experiments_tpcds_public_microbench.json`, `experiments_6model_dual_benchmark.json`).
- `figures/`: Vector PDF figures (`fig_architecture.pdf`, `fig_production_evolution.pdf`, `fig_ablation_latency.pdf`, `fig_caliber_traps.pdf`).

## Reproducing Formal Verification & Public Benchmarks (Zero External Dependencies)
```bash
python3 benchmarks/run_stage2_formal_and_scale_bench.py
python3 benchmarks/run_tpcds_public_benchmark.py
```
Expected verified output (`seed=42`):
- **10,000-Topology Formal Model Checker**: `10,000/10,000 (100.0%)` bounded termination (`depth <= 16`), `0/10,000` uncertified primary leaks, `0.0` max relative error across all `4,824` certified plans (vs. `8,232` ungoverned corruptions and `571.0%` mean error on coarse-grain ratio `AVG()`).
- **Multi-Scale Estate Invariance (`36 → 1,599` tables)**: HermesGov lineage-scoped planning stays constant at `0.78–0.83 µs` ($\rho=100\%$), `3.18–3.24 µs` ($\rho=50\%$), and `5.43–5.61 µs` ($\rho=0\%$), `203×` faster than unscoped graph BFS (`1,121.04 µs`) at `1,599` tables.
- **Public TPC-DS 36-Table Micro-Benchmark**: `180/180 (100.0%)` orthogonal fault interception, `40/40 (100.0%, 0 FP)` CTE-aware AST SQL Guard.
