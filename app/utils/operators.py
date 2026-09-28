"""
app/utils/operators.py
Corporate hierarchy heuristics and market concentration rollup engine.

Maps individual registered project SPVs and operating entities in the MaStR
to consolidated parent utility and developer groups via substring/regex heuristics.
"""

import re
import pandas as pd
from typing import Tuple, Dict

# Heuristic Parent Brand Rules
# Order matters: more specific patterns come before generic ones
PARENT_BRAND_RULES = [
    ("RWE Group", r"\bRWE\b"),
    ("EnBW Group", r"\bEnBW\b"),
    ("Alterric (Aloys Wobben / EWE)", r"\bAlterric\b"),
    ("PROKON", r"\bPROKON\b|\bProkon\b"),
    ("enercity (Stadtwerke Hannover)", r"\benercity\b"),
    ("Trianel", r"\bTrianel\b"),
    ("PNE Group", r"\bPNE\b"),
    ("Statkraft", r"\bStatkraft\b"),
    ("Energiekontor", r"\bEnergiekontor\b"),
    ("MVV Energie", r"\bMVV\b"),
    ("Stadtwerke München (SWM)", r"\bSWM\b|Stadtwerke München"),
    ("Swisspower Renewables", r"\bSwisspower\b"),
    ("VSB Group", r"\bVSB\b|\bVsb\b"),
    ("E.ON / E.DIS Group", r"\bE\.ON\b|\bE\.DIS\b|\be\.disnatur\b|\bEDIS\b"),
    ("VERBUND", r"\bVERBUND\b|\bVerbund\b"),
    ("wpd", r"\bwpd\b|\bWPD\b"),
    ("BOREAS Energie", r"\bBOREAS\b"),
    ("BKW Energie", r"\bBKW\b"),
    ("Mainova", r"\bMainova\b"),
    ("Juwi", r"\bJuwi\b|\bjuwi\b"),
    ("Vattenfall", r"\bVattenfall\b"),
    ("ABO Wind / ABO Energy", r"\bABO\s*Wind\b|\bABO\s*Energy\b"),
    ("BayWa r.e.", r"\bBayWa\b"),
    ("Boralex", r"\bBoralex\b"),
    ("Iberdrola", r"\bIberdrola\b"),
    ("Ørsted", r"Ørsted|Orsted"),
    ("Qualitas Energy", r"\bQualitas\b"),
    ("UKA Group", r"\bUKA\b"),
]


def map_to_parent_company(operator_name: str) -> str:
    """
    Maps an individual operator entity name to a parent company group.
    
    Returns:
        - Parent company name if matched
        - 'Unregistered / Private Operator (ABR)' if redacted under BDSG/GDPR
        - 'Independent / Unmapped' if entity has no recognized corporate group keyword
    """
    if not operator_name or pd.isna(operator_name):
        return "Unregistered / Private Operator (ABR)"
    
    clean_name = str(operator_name).replace("\uff06", "&").strip()
    if clean_name.startswith("ABR"):
        return "Unregistered / Private Operator (ABR)"
        
    for parent_name, pattern in PARENT_BRAND_RULES:
        if re.search(pattern, clean_name, re.IGNORECASE):
            return parent_name
            
    return "Independent / Unmapped"


def compute_leaderboards(df_operating: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """
    Computes both the Registered Legal Entity leaderboard and the Parent Company Group rollup.
    
    Args:
        df_operating: DataFrame of operating wind turbines with columns:
                      operator_name, nettonennleistung_mw, bruttoleistung_mw, bundesland, inbetriebnahmedatum
                      
    Returns:
        (top20_entities, top20_parents, summary_stats)
    """
    total_market_mw = df_operating["nettonennleistung_mw"].sum()
    
    # 1. Individual Legal Entity Rollup
    entity_agg = df_operating.groupby("operator_name").agg(
        unit_count=("operator_name", "count"),
        total_mw=("nettonennleistung_mw", "sum"),
        gross_mw=("bruttoleistung_mw", "sum"),
        state_count=("bundesland", "nunique"),
        first_commissioned=("inbetriebnahmedatum", "min"),
        last_commissioned=("inbetriebnahmedatum", "max")
    ).reset_index()
    
    entity_agg["operator_display"] = entity_agg["operator_name"].str.replace("\uff06", "&", regex=False)
    top20_entities = entity_agg.sort_values(by="total_mw", ascending=False).head(20).copy()
    top20_entities["rank"] = range(1, len(top20_entities) + 1)
    top20_entities["market_share_pct"] = (top20_entities["total_mw"] / total_market_mw) * 100
    
    # 2. Parent Company Group Rollup
    df_with_parent = df_operating.copy()
    df_with_parent["parent_group"] = df_with_parent["operator_name"].apply(map_to_parent_company)
    
    parent_agg = df_with_parent[
        ~df_with_parent["parent_group"].isin(["Independent / Unmapped", "Unregistered / Private Operator (ABR)"])
    ].groupby("parent_group").agg(
        unit_count=("parent_group", "count"),
        total_mw=("nettonennleistung_mw", "sum"),
        gross_mw=("bruttoleistung_mw", "sum"),
        subsidiary_count=("operator_name", "nunique"),
        state_count=("bundesland", "nunique"),
        first_commissioned=("inbetriebnahmedatum", "min"),
        last_commissioned=("inbetriebnahmedatum", "max")
    ).reset_index()
    
    top20_parents = parent_agg.sort_values(by="total_mw", ascending=False).head(20).copy()
    top20_parents["rank"] = range(1, len(top20_parents) + 1)
    top20_parents["market_share_pct"] = (top20_parents["total_mw"] / total_market_mw) * 100
    
    # 3. Market Share Comparisons
    top5_entity_mw = top20_entities.head(5)["total_mw"].sum()
    top5_entity_share = (top5_entity_mw / total_market_mw) * 100
    
    top5_parent_mw = top20_parents.head(5)["total_mw"].sum()
    top5_parent_share = (top5_parent_mw / total_market_mw) * 100
    
    # Check EnBW vs RWE comparison specifically
    rwe_single = top20_entities[top20_entities["operator_display"].str.contains("RWE", case=False, na=False)]["total_mw"].iloc[0]
    enbw_single = top20_entities[top20_entities["operator_display"].str.contains("EnBW", case=False, na=False)]["total_mw"].iloc[0]
    
    rwe_parent_sub = top20_parents[top20_parents["parent_group"] == "RWE Group"]
    rwe_parent = rwe_parent_sub["total_mw"].iloc[0] if not rwe_parent_sub.empty else 0.0
    
    enbw_parent_sub = top20_parents[top20_parents["parent_group"] == "EnBW Group"]
    enbw_parent = enbw_parent_sub["total_mw"].iloc[0] if not enbw_parent_sub.empty else 0.0
    
    summary_stats = {
        "total_operating_mw": total_market_mw,
        "top5_entity_mw": top5_entity_mw,
        "top5_entity_share_pct": top5_entity_share,
        "top5_parent_mw": top5_parent_mw,
        "top5_parent_share_pct": top5_parent_share,
        "rwe_single_mw": rwe_single,
        "enbw_single_mw": enbw_single,
        "rwe_parent_mw": rwe_parent,
        "enbw_parent_mw": enbw_parent,
        "enbw_group_exceeds_rwe_single": enbw_parent > rwe_single,
        "rwe_retains_parent_crown": rwe_parent > enbw_parent
    }
    
    return top20_entities, top20_parents, summary_stats
