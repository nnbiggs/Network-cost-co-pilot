"""Generate synthetic wireless/fiber/benchmark workbooks for local demo."""
from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RNG = np.random.default_rng(42)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)

    # --- Wireless: messy rows, multiple naming conventions ---
    n_sites = 420
    regions = ["North MS", "South MS", "AL Panhandle", "TN Border", "Rural West"]
    wireless_rows = []
    for i in range(n_sites):
        urban = RNG.choice(["Urban", "Suburban", "Rural"], p=[0.25, 0.45, 0.3])
        region = RNG.choice(regions)
        base = 85000 + (18000 if urban == "Rural" else 0)
        vendor_adj = 1.12  # regional premium
        # Fragmented spend lines
        lines = [
            ("Tower / Collocation", "tower_lease", base * 0.22 * vendor_adj),
            ("MW transport — 3rd party", "microwave_vendor", base * 0.14 * vendor_adj * 1.08),
            ("Fiber backhaul circuit", "fiber_bh", base * 0.11 * vendor_adj),
            ("Field workforce (contract)", "contract_labor", base * 0.18 * (1.15 if urban == "Rural" else 1.0)),
            ("OEM RAN maint.", "vendor_oem", base * 0.12 * vendor_adj),
            ("Power & gen fuel", "ops_maint", base * 0.06),
            ("Small cell attach fees", "infra_misc", base * 0.05),
            ("NOC / dispatch (allocated)", "ops_maint", base * 0.07),
            ("Spares & logistics", "ops_maint", base * 0.05),
        ]
        site_id = f"SITE-{10000 + i}"
        traffic_tb = float(RNG.uniform(8, 95) * (1.4 if urban == "Rural" else 1.0))
        for raw_label, internal_hint, amt in lines:
            wireless_rows.append(
                {
                    "Site_ID": site_id,
                    "Market": region,
                    "Density": urban,
                    "FY": 2025,
                    "Cost_Line_Description": raw_label,
                    "_hint": internal_hint,
                    "Amount_USD": round(amt * RNG.uniform(0.92, 1.08), 2),
                    "Traffic_TB_annual": round(traffic_tb, 2),
                }
            )

    wdf = pd.DataFrame(wireless_rows)
    wdf.drop(columns=["_hint"], inplace=True)
    wdf.to_excel(DATA / "wireless_costs.xlsx", index=False)
    # Legacy .xls name alias: copy as xlsx is what pandas reads; user asked for xls — write csv for xls confusion
    wdf.to_csv(DATA / "wireless_costs.csv", index=False)

    # --- Fiber: homes, build vs run ---
    markets = ["MS Delta", "AL Wiregrass", "TN Tri-Cities", "MS Gulf Coast"]
    fiber_rows = []
    for m in markets:
        hp = int(RNG.integers(45000, 120000))
        take = RNG.uniform(0.38, 0.52)
        hc = int(hp * take)
        build_annual = hp * RNG.uniform(42, 58)  # pass cost amortized proxy
        labor = hc * RNG.uniform(95, 140) * (1.12 if "Delta" in m or "Wiregrass" in m else 1.0)
        vendor = hp * RNG.uniform(18, 28) * 1.1
        transport = hc * RNG.uniform(8, 15) * 1.15
        infra = hp * RNG.uniform(22, 35)
        opex_misc = (build_annual + labor + vendor) * 0.06
        fiber_rows.append(
            {
                "Market_Segment": m,
                "Homes_Passed": hp,
                "Homes_Connected": hc,
                "Build_Capex_Alloc_USD": round(build_annual, 2),
                "Labor_install_support_USD": round(labor, 2),
                "Third_party_construction_MSOC": round(vendor * 0.4, 2),
                "Transport_agg_USD": round(transport, 2),
                "Fiber_asset_OPEX_USD": round(infra, 2),
                "Ops_and_field_USD": round(opex_misc + vendor * 0.6, 2),
            }
        )
    fdf = pd.DataFrame(fiber_rows)
    fdf.to_excel(DATA / "fiber_costs.xlsx", index=False)
    fdf.to_csv(DATA / "fiber_costs.csv", index=False)

    # --- Benchmarks: peers by segment ---
    cats = [
        "Labor / Workforce",
        "Vendor / Third-party",
        "Transport / Backhaul",
        "Infrastructure",
        "Operations & Maintenance",
    ]
    bench_rows = []
    for peer in [
        ("National Tier-1 A", "National", "Mixed"),
        ("National Tier-1 B", "National", "Urban"),
        ("Regional Integrated X", "Regional", "Mixed"),
        ("Regional Fiber-Heavy Y", "Regional", "Rural"),
        ("Your Network (observed)", "Regional", "Mixed"),
    ]:
        name, op_type, density = peer
        rural_pen = 1.08 if density == "Rural" else 1.0
        reg_pen = 1.05 if op_type == "Regional" else 1.0
        for j, c in enumerate(cats):
            base = [0.22, 0.28, 0.14, 0.18, 0.18][j]
            val = base * rural_pen * reg_pen * RNG.uniform(0.94, 1.06)
            cps_usd = 105000 * reg_pen * rural_pen * RNG.uniform(0.97, 1.03)
            cpt_usd = 7800 * (1.04 if op_type == "Regional" else 1.0) * rural_pen * RNG.uniform(0.95, 1.05)
            bench_rows.append(
                {
                    "Peer_Operator": name,
                    "Operator_Type": op_type,
                    "Density_Segment": density,
                    "Category": c,
                    "Share_of_Network_Cost": round(val, 4),
                    "Cost_per_site_index": round(100 * reg_pen * rural_pen * RNG.uniform(0.96, 1.04), 1),
                    "Cost_per_TB_index": round(100 * (1.02 if op_type == "Regional" else 0.98) * rural_pen, 1),
                    "Cost_per_site_USD": round(cps_usd, 0),
                    "Cost_per_TB_USD": round(cpt_usd, 0),
                }
            )

    bdf = pd.DataFrame(bench_rows)
    bdf.to_excel(DATA / "benchmarks.xlsx", index=False)
    bdf.to_csv(DATA / "benchmarks.csv", index=False)

    print("Wrote:", DATA / "wireless_costs.xlsx", DATA / "fiber_costs.xlsx", DATA / "benchmarks.xlsx")


if __name__ == "__main__":
    main()
