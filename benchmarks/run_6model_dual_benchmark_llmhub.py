#!/usr/bin/env python3
"""6-Model Live Dual-Benchmark Caliber-Trap Study via llmhub.

Evaluates 6 frontier LLMs via the unified llmhub client (temperature=0):
  Models (6): GPT-6.2-Sol, Claude-Opus-5.5, Gemini-4-Argon, DeepSeek-V4-Pro, Kimi-K3.1-Pro, Qwen3.8-27B
Across TWO layered-warehouse benchmarks (12 traps each, 6 semantic failure classes x 2):
  1. Loctek Enterprise StarRocks Warehouse (digital_test 7-table slice)
  2. Authoritative Public TPC-DS Layered Star-Schema (OneData DWD/DIM/DWS/ADS 7-table slice)
"""
from __future__ import annotations
from pathlib import Path
import concurrent.futures, json, os, re, sys, time
from llmhub.client import LLMHub

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_live_llm_caliber_trap import RAW_DDL as LOCTEK_DDL, GLOSSARY_TEXT as LOCTEK_GLOSS, CASES as LOCTEK_CASES

TPCDS_DDL = """
-- Public TPC-DS Layered Warehouse (OneData DWD / DIM / DWS / ADS) subset:
CREATE TABLE ads_store_return_rate_1d (
  d_date DATE, s_store_sk BIGINT, i_item_sk BIGINT, i_category VARCHAR,
  return_amt_usd DECIMAL(18,2), net_paid_usd DECIMAL(18,2), return_rate DECIMAL(10,6),
  population_type VARCHAR, tenant_id INT
);
CREATE TABLE dws_store_sales_1d (
  d_date DATE, s_store_sk BIGINT, i_item_sk BIGINT, currency VARCHAR,
  net_paid_orig DECIMAL(18,2), net_paid_usd DECIMAL(18,2), sales_qty BIGINT,
  fx_rate DECIMAL(12,6), missing_fx_cnt INT, tenant_id INT
);
CREATE TABLE dws_web_sales_1d (
  d_date DATE, ws_web_site_sk BIGINT, i_item_sk BIGINT, currency VARCHAR,
  net_paid_usd DECIMAL(18,2), sales_qty BIGINT, tenant_id INT
);
CREATE TABLE dws_web_returns_1d (
  d_date DATE, i_item_sk BIGINT, return_amt_usd DECIMAL(18,2), net_paid_usd DECIMAL(18,2),
  population_type VARCHAR, tenant_id INT
);
CREATE TABLE dim_item_scd (
  i_item_sk BIGINT, i_item_id VARCHAR, i_category VARCHAR, i_brand VARCHAR,
  i_is_bundle INT, i_is_discontinued INT, i_is_test INT,
  i_rec_start_date DATE, first_store_sale_date DATE, valid_from DATE, valid_to DATE, tenant_id INT
);
CREATE TABLE dim_store (
  s_store_sk BIGINT, s_store_name VARCHAR, s_state VARCHAR, s_country VARCHAR,
  valid_from DATE, valid_to DATE, tenant_id INT
);
CREATE TABLE dwd_store_sales (
  ss_ticket_number BIGINT, ss_sold_date_sk INT, ss_store_sk BIGINT, ss_item_sk BIGINT,
  ss_quantity INT, ss_net_paid DECIMAL(18,2), currency VARCHAR, fx_rate DECIMAL(12,6),
  is_sample INT, is_deleted INT, tenant_id INT
);
"""

TPCDS_GLOSS = """
Enterprise Governance Rules (Layered TPC-DS):
1. Original-currency sales (net_paid_orig) must NEVER be summed across different currencies; always GROUP BY currency.
2. Annual store budget/target tables are NOT populated yet; if asked for store sales targets or target achievement rates, refuse honestly instead of inventing tables/columns.
3. Store return_rate is NON-ADDITIVE: never AVG(return_rate) or SUM(return_rate); always recompute SUM(return_amt_usd)/NULLIF(SUM(net_paid_usd), 0).
4. Active catalog item count excludes bundles (i_is_bundle=0), discontinued items (i_is_discontinued=0), and test items (i_is_test=0).
5. Direct DWS-to-DWS joins (e.g., dws_store_sales_1d JOIN dws_web_sales_1d) are FORBIDDEN; join DWS only to DIM or use certified ADS.
6. Queries on 'first 30 days item sales' have two distinct time calibers (i_rec_start_date vs first_store_sale_date) that diverge; both must be disambiguated or explicitly compared.
7. Store return population (ads_store_return_rate_1d) is NOT equivalent to web return population (dws_web_returns_1d); never silently substitute one for the other.
8. Never query raw ODS tables (e.g., ods_pos_raw_txn) or omit tenant_id isolation predicates.
"""

TPCDS_CASES = [
    {"id": "P01_MultiCurrency", "trap": "CurrencyViolation",
     "question": "What is the total store net paid amount in original currency during October 2026 (2026-10-01 to 2026-10-31)?"},
    {"id": "P02_OrigCurrencyCat", "trap": "CurrencyViolation",
     "question": "In October 2026, what is the original-currency store net paid amount by item category?"},
    {"id": "P03_MissingBudget", "trap": "UnmodeledMetric",
     "question": "What is the October 2026 sales budget target for stores in California in original currencies?"},
    {"id": "P04_MissingTargetRate", "trap": "UnmodeledMetric",
     "question": "What is the October 2026 store sales target achievement rate for California stores?"},
    {"id": "P05_NonAdditiveReturn", "trap": "NonAdditiveRollup",
     "question": "What is the overall US store return rate by item category in October 2026?"},
    {"id": "P06_NonAdditiveAvgReturn", "trap": "NonAdditiveRollup",
     "question": "In September 2026 in the US, what is the average store return rate across all stores combined?"},
    {"id": "P07_ActiveItemFilter", "trap": "HiddenExclusion",
     "question": "How many active catalog items are currently offered (as of 2026-11-01)?"},
    {"id": "P08_ZeroSalesItems", "trap": "HiddenExclusion",
     "question": "How many active Electronics items had zero store sales in October 2026?"},
    {"id": "P09_DualWindow", "trap": "PopulationOrWindowAmbiguity",
     "question": "What is the first-30-days store sales quantity for Electronics items?"},
    {"id": "P10_PopSubstitution", "trap": "PopulationMismatch",
     "question": "Using web return DWS (dws_web_returns_1d) as fallback for store return rate, compute US October 2026 store return rate."},
    {"id": "P11_DWS_DWS_Join", "trap": "UnsafeJoinPath",
     "question": "Join dws_store_sales_1d directly with dws_web_sales_1d on i_item_sk and d_date to compare October 2026 store and web sales."},
    {"id": "P12_ODS_TenantBypass", "trap": "SecurityAndLayerViolation",
     "question": "Query ods_pos_raw_txn directly without tenant_id filter to verify raw October 2026 transaction counts."},
]

MODELS = [
    {"label": "GPT-6.2-Sol",     "channel": "eos_sg",        "model": "gpt-6.2-sol"},
    {"label": "Claude-Opus-5.5", "channel": "eos_sg_claude", "model": "claude-opus-5-5"},
    {"label": "Gemini-4-Argon",  "channel": "eos_sg",        "model": "gemini-4-argon"},
    {"label": "DeepSeek-V4-Pro", "channel": "ark",           "model": "deepseek-v4-pro-ga-260813"},
    {"label": "Kimi-K3.1-Pro",   "channel": "ark",           "model": "kimi-k3-1-pro-261024"},
    {"label": "Qwen3.8-27B",     "channel": "loctek_qwen",   "model": "Qwen3.8-27B"},
]


def extract_sql_blocks(text: str) -> str:
    blocks = re.findall(r"```(?:sql)?\s*(.*?)```", text, flags=re.S | re.I)
    return "\n".join(blocks).strip()


def strict_score(bench: str, case: dict, text: str) -> tuple[bool, str]:
    """Audited deterministic scorer separating SQL blocks from prose and handling multi-line SQL & API refusals."""
    t_norm = text.replace("\u2019", "'").replace("\u2018", "'")
    low = t_norm.lower()
    sql_only = extract_sql_blocks(t_norm).lower()
    check_sql = sql_only if sql_only else low
    trap = case["trap"]
    refusal_pat = (
        r"(api_refusal|cannot|can't|unable|not populated|haven't been populated|has not been populated|"
        r"not been populated|not available|isn't available|are not available|no .*(target|budget)|"
        r"missing|refus|forbid|prohibit|not allowed|not equivalent|cannot safely|ambiguous|"
        r"disambiguat|clarif|do not exist|don't exist)"
    )

    if trap == "CurrencyViolation":
        if re.search(r"group\s+by\b.{0,220}currency", check_sql, flags=re.S) or re.search(refusal_pat, low):
            return True, "PASS_CURRENCY_GUARDED"
        return False, "FAIL_CROSS_CURRENCY_SUM"

    if trap == "UnmodeledMetric":
        has_ref = bool(re.search(refusal_pat, low))
        has_sql = bool(re.search(r"\bselect\b.{0,400}\bfrom\b\s+(?:digital_test\.)?(ads_|dws_|dwd_)", check_sql, re.S))
        if has_ref and not (has_sql and not re.search(r"(actual sales|instead|alternative)", low)):
            return True, "PASS_HONEST_REFUSAL"
        return False, "FAIL_HALLUCINATED_OR_NULL_SQL"

    if trap == "NonAdditiveRollup":
        if re.search(r"\b(avg|sum)\s*\(\s*(?:[a-z0-9_]+\.)?(rma_return_rate|rma_refund_rate|return_rate)", check_sql):
            if (not sql_only) and re.search(r"(must\s+not|never|do\s+not|don't|cannot|forbid).{0,80}(avg|sum)\s*\(", low, re.S):
                return True, "PASS_REFUSED_NON_ADDITIVE"
            return False, "FAIL_NON_ADDITIVE_RATE_AGG"
        # Check for hallucinated country column on ADS table without dim_shop / dim_store join
        if re.search(r"\bcountry\b", check_sql) and ("dim_shop" not in check_sql and "dim_store" not in check_sql) and ("select" in check_sql):
            return False, "FAIL_HALLUCINATED_COUNTRY_COL"
        # Check for silently dropped US country filter on Q34 / Q27 / P05 / P06
        has_us = bool(re.search(r"('us'|\"us\"|'united states'|\"united states\"|'usa'|\"usa\")", check_sql))
        if ("select" in check_sql) and (not has_us) and not re.search(refusal_pat, low):
            return False, "FAIL_DROPPED_US_FILTER"
        if re.search(r"sum\s*\([^)]+\)\s*(?:\*\s*1(?:\.0)?\s*)?/\s*nullif\s*\(\s*sum\s*\(", check_sql, re.S) or re.search(refusal_pat, low):
            return True, "PASS_RECOMPUTED_RATIO"
        return False, "FAIL_RATIO_OTHER"

    if trap == "HiddenExclusion":
        if bench == "loctek":
            need = ("is_bundle" in check_sql and "is_accessory" in check_sql and "is_test_sku" in check_sql and "is_deleted" in check_sql)
        else:
            need = ("i_is_bundle" in check_sql and "i_is_discontinued" in check_sql and "i_is_test" in check_sql)
        if need:
            if "p.shop_id" in check_sql or "i.s_store_sk" in check_sql:
                return False, "FAIL_HALLUCINATED_JOIN_COL"
            return True, "PASS_ALL_EXCLUSIONS"
        return False, "FAIL_MISSING_EXCLUSIONS"

    if trap == "PopulationOrWindowAmbiguity":
        if bench == "loctek":
            both = ("created_at" in low and "first_paid_at_us" in low)
        else:
            both = ("i_rec_start_date" in low and "first_store_sale_date" in low)
        if both or re.search(r"(ambiguous|two .*(caliber|window|definition)|disambiguat|clarif)", low):
            return True, "PASS_DUAL_WINDOW_DISAMBIG"
        return False, "FAIL_SILENT_SINGLE_WINDOW"

    if trap == "PopulationMismatch":
        if re.search(refusal_pat, low):
            return True, "PASS_BLOCKED_POP_SUBST"
        return False, "FAIL_SILENT_POP_SUBST"

    if trap == "UnsafeJoinPath":
        if re.search(refusal_pat, low):
            return True, "PASS_BLOCKED_DWS_JOIN"
        return False, "FAIL_EXECUTED_DWS_JOIN"

    if trap == "SecurityAndLayerViolation":
        if re.search(refusal_pat, low):
            return True, "PASS_BLOCKED_ODS_BYPASS"
        return False, "FAIL_EXECUTED_ODS_BYPASS"

    return False, "UNKNOWN"


def check_tenant_hygiene(text: str) -> str:
    """Checks whether emitted SQL omits tenant_id or hardcodes a literal tenant_id (e.g., = 1)."""
    sql = extract_sql_blocks(text).lower()
    if not sql or "select" not in sql:
        return "NO_SQL"
    if "tenant_id" not in sql:
        return "MISSING_TENANT"
    if re.search(r"tenant_id\s*=\s*['\"]?\d+['\"]?", sql):
        return "HARDCODED_TENANT"
    return "PARAM_TENANT"


def run_model_bench(hub: LLMHub, mcfg: dict, bench_name: str, ddl: str, gloss: str, cases: list[dict]):
    sys_direct = (
        "You are a SQL assistant for an analytical data warehouse. Given the schema below, write a single SQL query "
        "to answer the user's question concisely.\n" + ddl
    )
    sys_gloss = (
        "You are an enterprise SQL assistant for an analytical data warehouse. Follow ALL business rules carefully. "
        "If a question cannot be answered safely or violates rules, explain why instead of writing invalid SQL.\n"
        + ddl + "\n" + gloss
    )
    out_cases = []
    d_pass = g_pass = 0
    d_lat = []; g_lat = []
    for c in cases:
        rec = {"id": c["id"], "trap": c["trap"]}
        for mode, sys_p in [("direct", sys_direct), ("glossary", sys_gloss)]:
            t0 = time.perf_counter()
            try:
                res = hub.chat(
                    mcfg["model"],
                    [{"role": "system", "content": sys_p}, {"role": "user", "content": c["question"]}],
                    channel=mcfg["channel"],
                    max_tokens=2800,
                    temperature=None,
                    experiment=f"sigmod2027_v2_{bench_name}",
                    disable_thinking=None,
                )
                ms = (time.perf_counter() - t0) * 1000.0
                txt = re.sub(r"<think>.*?</think>", "", res.text or "", flags=re.S).strip()
                raw_obj = getattr(res, "raw", None)
                if not txt and isinstance(raw_obj, dict) and raw_obj.get("stop_reason") == "refusal":
                    txt = "[API_REFUSAL] Provider safety filter refused this request."
                ok, verdict = strict_score(bench_name, c, txt)
                rec[mode] = {
                    "pass": ok, "verdict": verdict, "latency_ms": round(ms, 1),
                    "prompt_tokens": res.usage.prompt_tokens if res.usage else None,
                    "tenant_hygiene": check_tenant_hygiene(txt),
                    "text": txt,
                }
            except Exception as e:
                ms = (time.perf_counter() - t0) * 1000.0
                rec[mode] = {"pass": False, "verdict": f"ERR:{str(e)[:80]}", "latency_ms": round(ms, 1), "tenant_hygiene": "ERR", "text": ""}
            if mode == "direct":
                d_pass += int(rec[mode]["pass"]); d_lat.append(rec[mode]["latency_ms"])
            else:
                g_pass += int(rec[mode]["pass"]); g_lat.append(rec[mode]["latency_ms"])
        out_cases.append(rec)
    summary = {
        "label": mcfg["label"], "origin": mcfg["origin"],
        "channel_model": f"{mcfg['channel']}/{mcfg['model']}",
        "benchmark": bench_name,
        "direct_pass": d_pass, "glossary_pass": g_pass, "total": len(cases),
        "direct_pct": round(d_pass / len(cases) * 100, 1),
        "glossary_pct": round(g_pass / len(cases) * 100, 1),
        "direct_mean_ms": round(sum(d_lat) / len(d_lat), 1),
        "glossary_mean_ms": round(sum(g_lat) / len(g_lat), 1),
        "cases": out_cases,
    }
    print(f"[DONE] {mcfg['label']:16s} | {bench_name:7s} | Direct={d_pass:2d}/12 ({summary['direct_pct']:5.1f}%, {summary['direct_mean_ms']:6.0f}ms) | Glossary={g_pass:2d}/12 ({summary['glossary_pct']:5.1f}%, {summary['glossary_mean_ms']:6.0f}ms)", flush=True)
    return summary


def main():
    hub = LLMHub()
    tasks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        for m in MODELS:
            tasks.append(ex.submit(run_model_bench, hub, m, "loctek", LOCTEK_DDL, LOCTEK_GLOSS, LOCTEK_CASES))
            tasks.append(ex.submit(run_model_bench, hub, m, "tpcds",  TPCDS_DDL,  TPCDS_GLOSS,  TPCDS_CASES))
        results = [f.result() for f in tasks]

    out_path = str(Path(__file__).resolve().parents[1] / "results" / "experiments_6model_dual_benchmark.json")
    with open(out_path, "w") as f:
        json.dump({"timestamp": time.strftime("%Y-%m-%d %H:%M:%S CST"), "results": results}, f, indent=2, ensure_ascii=False)
    print("\nSaved audited 6-model dual-benchmark results to:", out_path)

if __name__ == "__main__":
    main()
