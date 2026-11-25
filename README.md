# HermesGov — ACM SIGMOD 2027 Industrial Track Reproducibility Artifact

**Paper**: *HermesGov: A Governed Multi-Path Semantic Query Engine and MCP Runtime for Enterprise Layered Data Warehouses*  
**Authors**: Hongsheng Wang (Zhejiang University & Loctek Ergonomic Technology Corp.) and Dazhen Deng (Zhejiang University)

---

## 1. Scope of Released Artifacts vs. Proprietary Enterprise Boundaries

In alignment with ACM SIGMOD reproducibility guidelines for industrial deployments, this repository provides complete, standalone Python reference implementations, formal verification harnesses, public/synthetic benchmarks, frozen multi-LLM traces, and figure generation scripts for **HermesGov**:

- **Fully Reproducible Open-Source Components (Zero Proprietary Dependencies)**:
  - `benchmarks/run_planner_and_guard_ablation.py`: Standalone implementation of **Algorithm 1** (Recursive Multi-Path Metric Planner), **Algorithm 2** ($\le$3-Hop Unique-Path Verified Join BFS), the **Eight-Dimension Certification Gate**, the **40-case CTE-aware AST SQL Guard** (`sqlglot` StarRocks dialect), **180-fault orthogonal gate ablation**, and **1,000-run/path latency microbenchmarks** on the 105-table OneData topology (`seed=42`).
  - `benchmarks/run_tpcds_public_benchmark.py`: Public **TPC-DS** 36-table OneData layered benchmark (`seed=42`), reproducing 1,000-run/path latencies (`4.04–15.50 µs` P50), `180/180` fault interception, and `40/40` AST SQL Guard accuracy.
  - `benchmarks/run_stage2_formal_and_scale_bench.py`: **10,000-Topology Property-Based Formal Model Checker** verifying **Theorem 4.1** (Ratio Rollup Homomorphism Barrier) and **Theorem 4.2** (Bounded Termination, Fail-Closed Soundness, and $O(1)$ Warehouse-Scale Invariance), **Multi-Scale Estate Sweep (`36 → 105 → 500 → 1,599` tables × $\rho \in \{0..100\%\}$)**, and calibrated **Equation (1)** silent-corruption regime model (`seed=42`).
  - `benchmarks/run_6model_dual_benchmark_llmhub.py`: Dual-warehouse (**Loctek 12 traps + Public TPC-DS 12 traps**) live caliber-trap evaluation harness across six foundation models (`Claude-Opus-5.5`, `GPT-6.2-Sol`, `Gemini-4-Argon`, `Kimi-K3.1-Pro`, `DeepSeek-V4-Pro`, `Qwen3.8-27B`) with SQL-block-aware verification and tenant-isolation auditing (requires `LLM_API_KEY` and `LLM_BASE_URL` only when re-querying live LLM APIs; frozen 288-trial traces are included in `results/experiments_6model_dual_benchmark.json`).
  - `benchmarks/generate_paper_figures.py` & `benchmarks/sigmod_arch_primitives.py`: Regenerates all four vector PDF figures in the paper (`figures/fig_architecture.pdf`, `fig_production_evolution.pdf`, `fig_ablation_latency.pdf`, `fig_caliber_traps.pdf`) directly from `results/*.json`.
- **Enterprise Privacy Boundary**:
  - Loctek Ergonomic Technology Corp.'s internal StarRocks warehouse records, Casdoor SSO credentials, and live ERP connectors remain confidential under corporate data-governance policy. Redacted aggregate governance and contract-evolution metrics (97-day snapshot reconciliation counts, 213-query evolution statistics, and Q01–Q50 audit summaries) are provided in `results/experiments_live_prod_telemetry.json`.

---

## 2. One-Click Reproduction (< 30 Seconds on Any Laptop)

### Prerequisites
Python 3.10+ with `sqlglot`, `numpy`, and `matplotlib`:
```bash
pip install -r requirements.txt
```

### Run All Deterministic Benchmarks, Formal Proofs & Paper Figures
```bash
bash reproduce_all.sh
```

### Expected Verified Output (`seed=42`)
- **10,000-Topology Formal Model Checker (Theorems 4.1 & 4.2)**:
  - `10,000/10,000 (100.0%)` bounded termination (`depth <= 16`, `BFS <= 256`), `0/10,000` uncertified primary leaks, and `0.0` maximum relative error vs. row-level ground-truth oracle across all `4,824` certified plans (vs. `8,232` ungoverned corruptions and `571.0%` mean error under naive `AVG(rate)`).
- **105-Table OneData & 36-Table Public TPC-DS Ablations (Section 6.4 & Table 6)**:
  - `180/180 (100.0%)` orthogonal fault interception on both warehouses; `40/40 (100.0%, 0 FP)` CTE-aware AST SQL Guard.
- **Warehouse-Scale Planning Invariance (`36 → 1,599` Tables, Figure 3b)**:
  - Lineage-scoped planning remains flat across `36` to `1,599` tables (`~0.8 µs` at $\rho=100\%$, `~3.2 µs` at $\rho=50\%$, `~5.5 µs` at $\rho=0\%$), `~203×` faster than unscoped BFS at `1,599` tables.
- **Figures Regenerated**:
  - `figures/fig_architecture.pdf`, `figures/fig_production_evolution.pdf`, `figures/fig_ablation_latency.pdf`, `figures/fig_caliber_traps.pdf`.

---

## 3. Re-Running Live 6-Model LLM Caliber-Trap Trials (Optional)

All 288 live LLM outputs used in Section 6.5 (Figure 4 & Table 7) are archived in `results/experiments_6model_dual_benchmark.json`. To run fresh live API calls against an OpenAI-compatible endpoint:
```bash
export LLM_BASE_URL="https://your-openai-compatible-endpoint/v1"
export LLM_API_KEY="your-api-key"
python3 benchmarks/run_6model_dual_benchmark_llmhub.py
```

---

## License
Released under the [MIT License](LICENSE).
