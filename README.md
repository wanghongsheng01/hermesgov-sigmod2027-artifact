# HermesGov — ACM SIGMOD 2027 Industrial Track Artifact

**Paper**: *HermesGov: A Governed Multi-Path Semantic Query Engine and MCP Runtime for Enterprise Layered Data Warehouses*  
**Authors**: Hongsheng Wang (Zhejiang University & Loctek Ergonomic Technology Corp.) and Dazhen Deng (Zhejiang University)

## Repository Contents (Reviewer-Facing Artifacts)
- `benchmarks/run_tpcds_public_benchmark.py`: Reproducible public **TPC-DS** 36-table OneData layered micro-benchmark (1,000 runs/path latency, 180-fault orthogonal gate ablation, 40-case CTE-aware AST SQL Guard; `seed=42`).
- `benchmarks/run_6model_dual_benchmark_llmhub.py`: Dual-warehouse (Loctek 12 traps + Public TPC-DS 12 traps) live caliber-trap evaluation harness across 6 foundation models (3 International + 3 Domestic) with SQL-block-aware verification and tenant hygiene checks.
- `results/`: Frozen JSON experimental traces backing Figures 3–4 and Tables 6–7 (`experiments_microbench_results.json`, `experiments_tpcds_public_microbench.json`, `experiments_6model_dual_benchmark.json`).
- `figures/`: Vector PDF figures (`fig_architecture.pdf`, `fig_production_evolution.pdf`, `fig_ablation_latency.pdf`, `fig_caliber_traps.pdf`).

## Reproducing the Public TPC-DS Benchmark (Zero External Dependencies)
```bash
python3 benchmarks/run_tpcds_public_benchmark.py
```
Expected verified output (`seed=42`, 36-table TPC-DS OneData graph):
- Planning median latency: ADS Direct Reuse `4.04 µs`, DWS+DIM 3-Hop BFS `8.17 µs`, Hybrid Derivative Ratio `15.50 µs`, AST SQL Guard `6.42 µs`.
- Orthogonal 180-Fault Ablation: Full HermesGov `180/180 (100.0%)`, every single-gate ablation `150/180 (83.3%, 0/30 on exposed class)`, ungoverned baseline `0/180 (0.0%)`.
- CTE-Aware AST SQL Guard: `40/40 (100.0%, 30/30 adversarial attacks blocked, 0 false positives)`.
