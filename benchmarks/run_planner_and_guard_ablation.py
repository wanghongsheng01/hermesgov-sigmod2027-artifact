#!/usr/bin/env python3
"""Reproducible Micro-Benchmark & Fault-Injection Ablation for HermesGov
Unified Recursive Metric Planner, 8-Dim Certification Gate, Bounded Join BFS,
and Non-Additive / Currency / Version-Fence Invariants.

Directly mirrors the exact production algorithms in:
  - data-agent-console-platform (isolated pilot branch):
      backend/app/services/metric_pilot_planner.py (find_path, validate_relation, _plan_node)
      backend/app/services/metric_pilot_semantics.py (assess_implementation, _exact_precomputed_match)
  - data-agent-console-platform (uat):
      backend/mcp_services/governed/additivity.py
      backend/mcp_services/warehouse/guard.py

Seed: 42 (fully deterministic & reproducible).
"""

from __future__ import annotations
from pathlib import Path
from collections import deque
import hashlib
import json
import random
import re
import statistics
import time
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# 1. Production-faithful Core Planner & Certification Gate Components
# ---------------------------------------------------------------------------

INTEGRAL_TYPES = {"tinyint", "smallint", "int", "integer", "bigint", "largeint"}
TEMPORAL_TYPES = {"date", "datetime", "timestamp"}
EXFIL_PATTERNS = [
    re.compile(r"\bINTO\s+OUTFILE\b", re.I),
    re.compile(r"\bLOAD\s+DATA\b", re.I),
    re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b", re.I),
    re.compile(r";\s*\S+", re.S),
]


def profile_fingerprint(profile: dict) -> str:
    canonical = json.dumps(profile, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def find_path(root: str, target: str, relations: list[dict], allowed: set[str],
              max_hops: int = 3, max_expansions: int = 256) -> tuple[list[dict] | None, str | None]:
    """Exact BFS from metric_pilot_planner.py::find_path."""
    if root == target:
        return [], None
    queue = deque([(root, [], {root})])
    found, shortest, expansions = [], None, 0
    while queue:
        table, path, visited = queue.popleft()
        if len(path) >= max_hops + 1 or (shortest is not None and len(path) >= shortest):
            continue
        for edge in relations:
            if (
                edge["left_table"] != table
                or edge["right_table"] not in allowed
                or edge.get("status") not in {"verified", "test_validated", "test_rule"}
                or not edge.get("enabled", True)
            ):
                continue
            right = edge["right_table"]
            if right in visited:
                continue
            expansions += 1
            if expansions > max_expansions:
                return None, "JOIN_BUDGET_EXCEEDED"
            next_path = path + [edge]
            if right == target:
                shortest = len(next_path)
                if next_path not in found:
                    found.append(next_path)
            else:
                queue.append((right, next_path, visited | {right}))
    if not found:
        return None, "NO_VERIFIED_PATH_WITHIN_3_HOPS"
    if len(found) != 1:
        return None, "AMBIGUOUS_JOIN_PATH"
    return found[0], None


def validate_relation(edge: dict, profiles: dict) -> str | None:
    """Exact validation from metric_pilot_planner.py::validate_relation."""
    left, right = edge["left_table"], edge["right_table"]
    if left not in profiles or right not in profiles:
        return "MISSING_ENDPOINT_PROFILE"
    # Ban DWS-to-DWS direct joins per Loctek OneData governance rule
    if left.startswith("dws_") and right.startswith("dws_"):
        return "DWS_TO_DWS_JOIN_FORBIDDEN"
    lfields = profiles[left]["fields"]
    rfields = profiles[right]["fields"]
    for a, b in zip(edge["left_columns"], edge["right_columns"]):
        if a not in lfields or b not in rfields:
            return "JOIN_KEY_NOT_IN_PROFILE"
        lt, rt = lfields[a].lower(), rfields[b].lower()
        if lt != rt and not ({lt, rt} <= INTEGRAL_TYPES):
            return "IMPLICIT_CAST_FANOUT_RISK"
    if edge.get("attribution") == "historical":
        for f in (edge.get("valid_from"), edge.get("valid_to")):
            if not f or f not in rfields or rfields[f].lower() not in TEMPORAL_TYPES:
                return "INVALID_SCD_VALIDITY_FIELD"
        as_of = edge.get("as_of_field")
        if not as_of or as_of not in lfields or lfields[as_of].lower() not in TEMPORAL_TYPES:
            return "INVALID_FACT_AS_OF_FIELD"
    return None


def assess_implementation(defn: dict, logical: dict, profile: dict, req: dict,
                          enabled_gates: set[str]) -> dict:
    """Production-faithful 8-dimension certification gate from metric_pilot_semantics.py."""
    reasons = []
    # Gate 1: OneData layer anchoring (atomic -> DWD only)
    if "onedata_anchor" in enabled_gates:
        if logical["type"] == "atomic" and defn["layer"] != "dwd":
            reasons.append("ATOMIC_MUST_ANCHOR_DWD")

    # Gate 2: Non-additive precomputed guard (ratio/avg/growth_rate exact match)
    if "non_additive_guard" in enabled_gates:
        if logical.get("additivity") == "non_additive" and defn.get("materialization") == "precomputed":
            ev = defn.get("exact_match_evidence", {})
            req_keys = ("same_population", "same_time_grain", "same_dimensions",
                        "same_filters", "same_unit_currency", "same_coverage")
            if not all(ev.get(k) is True for k in req_keys):
                reasons.append("PRECOMPUTED_NON_ADDITIVE_MISMATCH")
        if logical.get("additivity") == "distinct_additive":
            if defn.get("aggregation") != "BITMAP_UNION_COUNT" and not defn.get("deduplication_key"):
                reasons.append("MISSING_DEDUP_KEY")

    # Gate 3: Population equivalence & certified substitution gate
    if "population_gate" in enabled_gates:
        if defn.get("population_ref") != logical.get("population_ref"):
            if not defn.get("substitution_certified", False):
                reasons.append("UNCERTIFIED_POPULATION_MISMATCH")

    # Gate 4: Multi-currency non-summable & single-FX guard
    if "currency_guard" in enabled_gates:
        if req.get("currency_mode") == "original" and req.get("cross_currency_sum", False):
            reasons.append("CROSS_CURRENCY_SUM_FORBIDDEN")
        if req.get("currency_mode") == "fixed_usd":
            if not (defn.get("fx_field") and defn.get("fx_missing_policy")):
                reasons.append("INCOMPLETE_FX_RULE")

    # Gate 5: Canonical version-set & profile fingerprint stale fence
    if "version_fence" in enabled_gates:
        actual_fp = profile_fingerprint(profile)
        if defn.get("profile_fingerprint") != actual_fp or defn.get("snapshot_rev") != req.get("active_snapshot_rev"):
            reasons.append("STALE_CERTIFICATION_DRIFT")

    # Gate 6: Coverage & future-partition watermark check
    if "coverage_gate" in enabled_gates:
        if req.get("end_date", "2026-10-31") > defn.get("watermark_date", "2026-11-09"):
            reasons.append("UNKNOWN_FUTURE_PARTITION")

    # Gate 7: Join path & relation safety (when enrichment needed)
    if "join_guard" in enabled_gates and req.get("enrichment_target"):
        path, err = find_path(defn["table"], req["enrichment_target"],
                              req["relations"], req["allowed_tables"])
        if err:
            reasons.append(err)
        else:
            for e in path:
                rerr = validate_relation(e, req["profiles"])
                if rerr:
                    reasons.append(rerr)

    return {
        "primary_eligible": len(reasons) == 0,
        "diagnostic_only": (len(reasons) > 0 and all(r in {"UNCERTIFIED_POPULATION_MISMATCH", "PRECOMPUTED_NON_ADDITIVE_MISMATCH"} for r in reasons)),
        "reasons": reasons,
    }


def guard_raw_sql(sql: str, allowed_tables: set[str], tenant_col: str | None = "tenant_id") -> tuple[bool, str]:
    """Production-faithful SQL Guard from warehouse/guard.py."""
    s = sql.strip().rstrip(";")
    if len(s) > 200_000:
        return False, "SQL_TOO_LONG"
    for pat in EXFIL_PATTERNS:
        if pat.search(s):
            return False, "FORBIDDEN_STATEMENT_OR_EXFIL"
    if not re.match(r"^(SELECT|WITH)\b", s, re.I):
        return False, "NON_SELECT_REJECTED"
    cte_names = set(re.findall(r"\b(?:WITH|,)\s*`?([a-zA-Z0-9_]+)`?\s+AS\s*\(", s, re.I))
    tables = re.findall(r"\b(?:FROM|JOIN)\s+`?([a-zA-Z0-9_.]+)`?", s, re.I)
    for t in tables:
        base_t = t.split(".")[-1]
        if base_t in cte_names:
            continue
        if base_t not in allowed_tables:
            return False, f"TABLE_NOT_ALLOWED:{base_t}"
    if tenant_col and tenant_col not in s:
        return False, "MISSING_TENANT_PREDICATE"
    return True, "OK"


# ---------------------------------------------------------------------------
# 2. Construct Realistic Loctek 4-Domain Warehouse Graph (105-Table Scale)
# ---------------------------------------------------------------------------

def build_loctek_graph(seed: int = 42):
    rng = random.Random(seed)
    profiles = {
        "ads_afs_rma_event_rate_metric_1d": {"fields": {"shop_id": "bigint", "sku_id": "bigint", "dt": "date", "rma_cnt": "bigint", "sale_cnt": "bigint", "rma_rate": "decimal", "currency": "varchar"}},
        "ads_trd_sale_metric_1d": {"fields": {"shop_id": "bigint", "sku_id": "bigint", "dt": "date", "sales_qty": "bigint", "sales_usd": "decimal", "fx_rate": "decimal", "currency": "varchar"}},
        "dws_trd_sale_metric_1d": {"fields": {"shop_id": "bigint", "sku_id": "bigint", "dt": "date", "sales_qty": "bigint", "sales_orig": "decimal", "fx_rate": "decimal", "currency": "varchar"}},
        "dws_trade_rma_period_1d": {"fields": {"shop_id": "bigint", "sku_id": "bigint", "dt": "date", "refund_usd": "decimal", "sale_usd": "decimal"}},
        "dwd_trd_sale_order_detail_di": {"fields": {"order_id": "bigint", "shop_id": "bigint", "sku_id": "bigint", "pay_dt": "date", "qty": "bigint", "orig_amt": "decimal", "fx_rate": "decimal", "currency": "varchar"}},
        "dim_shop_scd": {"fields": {"shop_id": "bigint", "platform_id": "bigint", "market_id": "bigint", "dept_id": "bigint", "valid_from": "date", "valid_to": "date"}},
        "dim_platform": {"fields": {"platform_id": "bigint", "platform_name": "varchar", "channel_id": "bigint"}},
        "dim_market_geo_scd": {"fields": {"market_id": "bigint", "country_code": "varchar", "region_name": "varchar", "valid_from": "date", "valid_to": "date"}},
        "dim_product_sku_scd": {"fields": {"sku_id": "bigint", "category_id": "bigint", "brand_id": "bigint", "valid_from": "date", "valid_to": "date"}},
        "dim_product_category_scd": {"fields": {"category_id": "bigint", "erp_l1_cat": "varchar", "valid_from": "date", "valid_to": "date"}},
        "dim_channel": {"fields": {"channel_id": "bigint", "channel_name": "varchar"}},
        "dim_bad_cast": {"fields": {"shop_id": "varchar", "extra_attr": "varchar"}},
    }
    # Expand to 105 realistic non-ODS tables to stress BFS at real digital_test scale
    for i in range(105 - len(profiles)):
        layer = ["dim", "br", "dwd", "dws", "ads"][i % 5]
        profiles[f"{layer}_domain_tbl_{i:03d}"] = {"fields": {"id": "bigint", "shop_id": "bigint", "sku_id": "bigint", "dt": "date", "val": "decimal"}}

    relations = [
        {"left_table": "dws_trd_sale_metric_1d", "right_table": "dim_shop_scd", "left_columns": ["shop_id"], "right_columns": ["shop_id"], "status": "verified", "enabled": True, "attribution": "historical", "valid_from": "valid_from", "valid_to": "valid_to", "as_of_field": "dt"},
        {"left_table": "dim_shop_scd", "right_table": "dim_platform", "left_columns": ["platform_id"], "right_columns": ["platform_id"], "status": "verified", "enabled": True},
        {"left_table": "dim_platform", "right_table": "dim_channel", "left_columns": ["channel_id"], "right_columns": ["channel_id"], "status": "verified", "enabled": True},
        {"left_table": "dim_shop_scd", "right_table": "dim_market_geo_scd", "left_columns": ["market_id"], "right_columns": ["market_id"], "status": "verified", "enabled": True},
        {"left_table": "dws_trd_sale_metric_1d", "right_table": "dim_product_sku_scd", "left_columns": ["sku_id"], "right_columns": ["sku_id"], "status": "verified", "enabled": True},
        {"left_table": "dim_product_sku_scd", "right_table": "dim_product_category_scd", "left_columns": ["category_id"], "right_columns": ["category_id"], "status": "verified", "enabled": True},
        # Adversarial edges for fault injection
        {"left_table": "dws_trd_sale_metric_1d", "right_table": "dws_trade_rma_period_1d", "left_columns": ["shop_id"], "right_columns": ["shop_id"], "status": "verified", "enabled": True},
        {"left_table": "dws_trd_sale_metric_1d", "right_table": "dim_bad_cast", "left_columns": ["shop_id"], "right_columns": ["shop_id"], "status": "verified", "enabled": True},
    ]
    # Add realistic background edges across the 105-table catalog (preserving unique paths on core dims)
    extra_tables = [t for t in profiles if t.startswith(("dim_domain_", "br_domain_"))]
    for idx, t in enumerate(extra_tables[:-1]):
        relations.append({
            "left_table": t, "right_table": extra_tables[idx + 1],
            "left_columns": ["id"], "right_columns": ["id"],
            "status": "verified", "enabled": True,
        })
    return profiles, relations


# ---------------------------------------------------------------------------
# 3. Run Fault-Injection Ablation (6 Failure Classes × 30 Cases = 180 Faults)
#    + 1,000-Query Planning Latency Micro-Benchmark
# ---------------------------------------------------------------------------

def run_benchmark():
    profiles, relations = build_loctek_graph(seed=42)
    allowed_tables = set(profiles.keys())
    all_gates = {"onedata_anchor", "non_additive_guard", "population_gate",
                 "currency_guard", "version_fence", "coverage_gate", "join_guard"}

    fp_ads_rma = profile_fingerprint(profiles["ads_afs_rma_event_rate_metric_1d"])
    fp_dws_sale = profile_fingerprint(profiles["dws_trd_sale_metric_1d"])
    fp_dwd_sale = profile_fingerprint(profiles["dwd_trd_sale_order_detail_di"])

    # A. 1,000-Query Planning Overhead Micro-Benchmark across 3 Paths
    path_scenarios = {
        "ADS_Direct_Reuse": (
            {"table": "ads_trd_sale_metric_1d", "layer": "ads", "materialization": "additive", "population_ref": "pop_trade_paid", "fx_field": "fx_rate", "fx_missing_policy": "reject", "profile_fingerprint": profile_fingerprint(profiles["ads_trd_sale_metric_1d"]), "snapshot_rev": 10, "watermark_date": "2026-11-09"},
            {"type": "derived", "additivity": "fully_additive", "population_ref": "pop_trade_paid"},
            {"currency_mode": "fixed_usd", "active_snapshot_rev": 10, "end_date": "2026-10-31", "profiles": profiles, "relations": relations, "allowed_tables": allowed_tables},
        ),
        "DWS_Plus_DIM_3Hop": (
            {"table": "dws_trd_sale_metric_1d", "layer": "dws", "materialization": "additive", "population_ref": "pop_trade_paid", "fx_field": "fx_rate", "fx_missing_policy": "reject", "profile_fingerprint": fp_dws_sale, "snapshot_rev": 10, "watermark_date": "2026-11-09"},
            {"type": "derived", "additivity": "fully_additive", "population_ref": "pop_trade_paid"},
            {"currency_mode": "fixed_usd", "active_snapshot_rev": 10, "end_date": "2026-10-31", "enrichment_target": "dim_channel", "profiles": profiles, "relations": relations, "allowed_tables": allowed_tables},
        ),
        "Hybrid_Derivative_Ratio": (
            {"table": "ads_afs_rma_event_rate_metric_1d", "layer": "ads", "materialization": "precomputed", "population_ref": "pop_rma_finished", "substitution_certified": False, "exact_match_evidence": {"same_population": True, "same_time_grain": True, "same_dimensions": False, "same_filters": True, "same_unit_currency": True, "same_coverage": True}, "fx_field": "fx_rate", "fx_missing_policy": "reject", "profile_fingerprint": fp_ads_rma, "snapshot_rev": 10, "watermark_date": "2026-11-09"},
            {"type": "derivative", "additivity": "non_additive", "population_ref": "pop_rma_finished"},
            {"currency_mode": "fixed_usd", "active_snapshot_rev": 10, "end_date": "2026-10-31", "profiles": profiles, "relations": relations, "allowed_tables": allowed_tables},
        ),
    }

    latency_results = {}
    N_RUNS = 1000
    for name, (defn, logical, req) in path_scenarios.items():
        prof = profiles[defn["table"]]
        times_us = []
        for _ in range(N_RUNS):
            t0 = time.perf_counter_ns()
            res = assess_implementation(defn, logical, prof, req, all_gates)
            if name == "Hybrid_Derivative_Ratio" and not res["primary_eligible"]:
                # Recursive expansion to DWS numerator + DWD denominator
                assess_implementation(
                    {"table": "dws_trd_sale_metric_1d", "layer": "dws", "materialization": "additive", "population_ref": "pop_rma_finished", "fx_field": "fx_rate", "fx_missing_policy": "reject", "profile_fingerprint": fp_dws_sale, "snapshot_rev": 10, "watermark_date": "2026-11-09"},
                    {"type": "derived", "additivity": "fully_additive", "population_ref": "pop_rma_finished"},
                    profiles["dws_trd_sale_metric_1d"],
                    {"currency_mode": "fixed_usd", "active_snapshot_rev": 10, "end_date": "2026-10-31", "enrichment_target": "dim_product_category_scd", "profiles": profiles, "relations": relations, "allowed_tables": allowed_tables},
                    all_gates,
                )
                assess_implementation(
                    {"table": "dwd_trd_sale_order_detail_di", "layer": "dwd", "materialization": "additive", "population_ref": "pop_rma_finished", "fx_field": "fx_rate", "fx_missing_policy": "reject", "profile_fingerprint": fp_dwd_sale, "snapshot_rev": 10, "watermark_date": "2026-11-09"},
                    {"type": "atomic", "additivity": "fully_additive", "population_ref": "pop_rma_finished"},
                    profiles["dwd_trd_sale_order_detail_di"],
                    {"currency_mode": "fixed_usd", "active_snapshot_rev": 10, "end_date": "2026-10-31", "profiles": profiles, "relations": relations, "allowed_tables": allowed_tables},
                    all_gates,
                )
            t1 = time.perf_counter_ns()
            times_us.append((t1 - t0) / 1000.0)
        times_us.sort()
        latency_results[name] = {
            "runs": N_RUNS,
            "p50_us": round(times_us[int(N_RUNS * 0.50)], 2),
            "p95_us": round(times_us[int(N_RUNS * 0.95)], 2),
            "p99_us": round(times_us[int(N_RUNS * 0.99)], 2),
            "mean_us": round(statistics.mean(times_us), 2),
        }

    # B. Fault-Injection Ablation Suite (180 Deterministic Adversarial Cases)
    fault_suite = []
    # 1. Non-additive precomputed rollup trap (30 cases)
    for i in range(30):
        ev = {k: True for k in ("same_population", "same_time_grain", "same_dimensions", "same_filters", "same_unit_currency", "same_coverage")}
        ev[list(ev.keys())[i % 6]] = False
        fault_suite.append(("NonAdditiveRollup", "non_additive_guard",
            {"table": "ads_afs_rma_event_rate_metric_1d", "layer": "ads", "materialization": "precomputed", "population_ref": "pop_rma_finished", "exact_match_evidence": ev, "fx_field": "fx_rate", "fx_missing_policy": "reject", "profile_fingerprint": fp_ads_rma, "snapshot_rev": 10, "watermark_date": "2026-11-09"},
            {"type": "derivative", "additivity": "non_additive", "population_ref": "pop_rma_finished"},
            {"currency_mode": "fixed_usd", "active_snapshot_rev": 10, "end_date": "2026-10-31", "profiles": profiles, "relations": relations, "allowed_tables": allowed_tables}))

    # 2. Uncertified population-mismatch fallback (30 cases: finished-product RMA vs issue-type RMA)
    for i in range(30):
        fault_suite.append(("PopulationMismatch", "population_gate",
            {"table": "dws_trd_sale_metric_1d", "layer": "dws", "materialization": "additive", "population_ref": "pop_rma_issue_type", "substitution_certified": False, "fx_field": "fx_rate", "fx_missing_policy": "reject", "profile_fingerprint": fp_dws_sale, "snapshot_rev": 10, "watermark_date": "2026-11-09"},
            {"type": "derived", "additivity": "fully_additive", "population_ref": "pop_rma_finished"},
            {"currency_mode": "fixed_usd", "active_snapshot_rev": 10, "end_date": "2026-10-31", "profiles": profiles, "relations": relations, "allowed_tables": allowed_tables}))

    # 3. Stale profile fingerprint / snapshot version drift (30 cases)
    for i in range(30):
        bad_fp = "0000000000000000" if i % 2 == 0 else fp_dws_sale
        bad_rev = 9 if i % 2 == 1 else 10
        fault_suite.append(("StaleVersionDrift", "version_fence",
            {"table": "dws_trd_sale_metric_1d", "layer": "dws", "materialization": "additive", "population_ref": "pop_trade_paid", "fx_field": "fx_rate", "fx_missing_policy": "reject", "profile_fingerprint": bad_fp, "snapshot_rev": bad_rev, "watermark_date": "2026-11-09"},
            {"type": "derived", "additivity": "fully_additive", "population_ref": "pop_trade_paid"},
            {"currency_mode": "fixed_usd", "active_snapshot_rev": 10, "end_date": "2026-10-31", "profiles": profiles, "relations": relations, "allowed_tables": allowed_tables}))

    # 4. Multi-currency cross-sum & incomplete FX rule (30 cases)
    for i in range(30):
        if i % 2 == 0:
            fault_suite.append(("CurrencyViolation", "currency_guard",
                {"table": "dws_trd_sale_metric_1d", "layer": "dws", "materialization": "additive", "population_ref": "pop_trade_paid", "fx_field": "fx_rate", "fx_missing_policy": "reject", "profile_fingerprint": fp_dws_sale, "snapshot_rev": 10, "watermark_date": "2026-11-09"},
                {"type": "derived", "additivity": "fully_additive", "population_ref": "pop_trade_paid"},
                {"currency_mode": "original", "cross_currency_sum": True, "active_snapshot_rev": 10, "end_date": "2026-10-31", "profiles": profiles, "relations": relations, "allowed_tables": allowed_tables}))
        else:
            fault_suite.append(("CurrencyViolation", "currency_guard",
                {"table": "dws_trd_sale_metric_1d", "layer": "dws", "materialization": "additive", "population_ref": "pop_trade_paid", "fx_field": None, "fx_missing_policy": None, "profile_fingerprint": fp_dws_sale, "snapshot_rev": 10, "watermark_date": "2026-11-09"},
                {"type": "derived", "additivity": "fully_additive", "population_ref": "pop_trade_paid"},
                {"currency_mode": "fixed_usd", "active_snapshot_rev": 10, "end_date": "2026-10-31", "profiles": profiles, "relations": relations, "allowed_tables": allowed_tables}))

    # 5. Unsafe join traps: DWS-to-DWS, implicit type-cast fan-out, >3-hop unreachable (30 cases)
    for i in range(30):
        target = ["dws_trade_rma_period_1d", "dim_bad_cast", "dim_domain_tbl_090"][i % 3]
        fault_suite.append(("UnsafeJoinPath", "join_guard",
            {"table": "dws_trd_sale_metric_1d", "layer": "dws", "materialization": "additive", "population_ref": "pop_trade_paid", "fx_field": "fx_rate", "fx_missing_policy": "reject", "profile_fingerprint": fp_dws_sale, "snapshot_rev": 10, "watermark_date": "2026-11-09"},
            {"type": "derived", "additivity": "fully_additive", "population_ref": "pop_trade_paid"},
            {"currency_mode": "fixed_usd", "active_snapshot_rev": 10, "end_date": "2026-10-31", "enrichment_target": target, "profiles": profiles, "relations": relations, "allowed_tables": allowed_tables}))

    # 6. OneData atomic layer violation & future partition watermark (30 cases)
    for i in range(30):
        if i % 2 == 0:
            fault_suite.append(("LayerOrCoverageViolation", "onedata_anchor",
                {"table": "dws_trd_sale_metric_1d", "layer": "dws", "materialization": "additive", "population_ref": "pop_trade_paid", "fx_field": "fx_rate", "fx_missing_policy": "reject", "profile_fingerprint": fp_dws_sale, "snapshot_rev": 10, "watermark_date": "2026-11-09"},
                {"type": "atomic", "additivity": "fully_additive", "population_ref": "pop_trade_paid"},
                {"currency_mode": "fixed_usd", "active_snapshot_rev": 10, "end_date": "2026-10-31", "profiles": profiles, "relations": relations, "allowed_tables": allowed_tables}))
        else:
            fault_suite.append(("LayerOrCoverageViolation", "coverage_gate",
                {"table": "dws_trd_sale_metric_1d", "layer": "dws", "materialization": "additive", "population_ref": "pop_trade_paid", "fx_field": "fx_rate", "fx_missing_policy": "reject", "profile_fingerprint": fp_dws_sale, "snapshot_rev": 10, "watermark_date": "2026-11-09"},
                {"type": "derived", "additivity": "fully_additive", "population_ref": "pop_trade_paid"},
                {"currency_mode": "fixed_usd", "active_snapshot_rev": 10, "end_date": "2026-11-30", "profiles": profiles, "relations": relations, "allowed_tables": allowed_tables}))

    ablation_configs = {
        "Full_HermesGov": all_gates,
        "No_NonAdditiveGuard": all_gates - {"non_additive_guard"},
        "No_PopulationGate": all_gates - {"population_gate"},
        "No_VersionFence": all_gates - {"version_fence"},
        "No_CurrencyGuard": all_gates - {"currency_guard"},
        "No_JoinGuard": all_gates - {"join_guard"},
        "No_LayerOrCoverage": all_gates - {"onedata_anchor", "coverage_gate"},
        "Ungoverned_Baseline": set(),
    }

    ablation_results = {}
    for cfg_name, gates in ablation_configs.items():
        blocked_total = 0
        by_class = {}
        for cls, _, defn, logical, req in fault_suite:
            res = assess_implementation(defn, logical, profiles[defn["table"]], req, gates)
            blocked = not res["primary_eligible"]
            blocked_total += int(blocked)
            by_class.setdefault(cls, [0, 0])
            by_class[cls][0] += int(blocked)
            by_class[cls][1] += 1
        ablation_results[cfg_name] = {
            "blocked": blocked_total,
            "total": len(fault_suite),
            "interception_rate_pct": round(blocked_total / len(fault_suite) * 100.0, 2),
            "by_class": {k: f"{v[0]}/{v[1]}" for k, v in by_class.items()},
        }

    # C. SQL Guard Adversarial Suite (40 cases)
    sql_cases = [
        ("SELECT sum(sales_usd) FROM ads_trd_sale_metric_1d WHERE tenant_id = 1", True),
        ("SELECT * FROM ads_trd_sale_metric_1d", False),  # missing tenant_id
        ("SELECT * FROM ods_secret_hr_salary WHERE tenant_id = 1", False),  # disallowed table
        ("SELECT * FROM ads_trd_sale_metric_1d WHERE tenant_id = 1; DROP TABLE dim_shop_scd", False),
        ("SELECT * FROM ads_trd_sale_metric_1d INTO OUTFILE '/tmp/x' WHERE tenant_id = 1", False),
        ("DELETE FROM ads_trd_sale_metric_1d WHERE tenant_id = 1", False),
        ("UPDATE ads_trd_sale_metric_1d SET sales_usd=0 WHERE tenant_id = 1", False),
        ("WITH t AS (SELECT shop_id FROM dws_trd_sale_metric_1d WHERE tenant_id = 1) SELECT * FROM t", True),
    ] * 5  # 40 deterministic checks (10 valid, 30 adversarial)
    sql_ok, sql_block_tp, sql_fp = 0, 0, 0
    t_sql = []
    for sql, expect_allow in sql_cases:
        t0 = time.perf_counter_ns()
        allow, _ = guard_raw_sql(sql, allowed_tables)
        t_sql.append((time.perf_counter_ns() - t0) / 1000.0)
        if allow == expect_allow:
            sql_ok += 1
        if not expect_allow and not allow:
            sql_block_tp += 1
        if expect_allow and not allow:
            sql_fp += 1
    t_sql.sort()

    out = {
        "seed": 42,
        "catalog_scale_tables": len(profiles),
        "planning_latency_us": latency_results,
        "fault_injection_ablation": ablation_results,
        "sql_guard_eval": {
            "total_cases": len(sql_cases),
            "accuracy_pct": round(sql_ok / len(sql_cases) * 100.0, 2),
            "adversarial_blocked": f"{sql_block_tp}/30",
            "false_positives": sql_fp,
            "p50_us": round(t_sql[len(t_sql)//2], 2),
            "p95_us": round(t_sql[int(len(t_sql)*0.95)], 2),
        },
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    with open(str(Path(__file__).resolve().parents[1] / "results" / "reproduced_microbench_results.json"), "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    run_benchmark()
