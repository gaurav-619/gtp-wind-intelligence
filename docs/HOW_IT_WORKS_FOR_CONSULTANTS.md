# GTP Wind Intelligence — How It Works: A Consultant's Guide

## 1. What This Tool Is

GTP Wind Intelligence is an institutional market analytics platform that transforms raw regulatory energy filings into decision-ready commercial intelligence on Germany's onshore wind and battery storage infrastructure. It gives consulting project teams, investment partners, and transaction advisors instant, auditable answers to market due diligence questions that previously required weeks of manual data engineering and registry cross-referencing.

---

## 2. What Question Each Page Answers and Why a Consultant Would Care

### Executive Overview
- **Question Answered:** *What is the macro health, operating size, and commercial velocity of Germany's onshore wind sector right now?*
- **Why a Consultant Cares:** When kicking off a strategy engagement or preparing an executive steering committee deck, consultants need trusted, board-ready macro totals without spending days validating numbers. The Executive Overview delivers high-level portfolio KPIs—71.0 GW operating capacity, 33.1 GW development pipeline, 13.1 GW of post-subsidy merchant exposure, and co-located storage metrics—alongside a transparent summary of data health and active analytical modules.

### Market Landscape (formerly Q1 Capacity)
- **Question Answered:** *Which German federal states (Bundesländer) have the highest installed onshore wind capacity, and where has installation velocity grown fastest over time?*
- **Why a Consultant Cares:** Energy infrastructure investments require granular geographic prioritization. This page allows a consultant to interactively scrub through commissioning history from 2000 to the present day across all 16 federal states using an interactive density map and comparative growth trajectories. It immediately highlights that states like Niedersachsen (~13.1 GW), Brandenburg (~9.0 GW), and Schleswig-Holstein (~8.6 GW) dominate aggregate capacity, while southern industrial states (Bayern, Baden-Württemberg) lag behind due to historic distance restrictions (*10H rules*), framing regional expansion opportunities.

### Development Pipeline & Permitting Radar (formerly Q2 Pipeline)
- **Question Answered:** *How healthy is the forward project pipeline, how long does environmental permitting take, and where are approval bottlenecks threatening project realization?*
- **Why a Consultant Cares:** In M&A due diligence and commercial advisory, buying a pipeline is only as good as its probability of reaching Commercial Operation Date (COD). This radar reveals the ratio of planned capacity to operating assets (+46.6% nationally) and computes actual median permitting cycle times under the Federal Immission Control Act (*BImSchG*). Consultants can immediately see where permitting moves swiftly (< 12 months) versus where grid congestion and regulatory scrutiny extend timelines beyond 24 months, enabling teams to discount pipeline valuations in slow-moving jurisdictions.

### Operator Intelligence & Repowering Radar (formerly Q3 Operators)
- **Question Answered:** *Who actually owns and controls Germany's operating wind farms, and which specific turbine assets face imminent merchant market exposure as their 20-year EEG subsidies end?*
- **Why a Consultant Cares:** German wind ownership is notoriously fragmented across thousands of project SPVs and farmer cooperatives. This page provides a dual-lens view: consultants can examine individual registered legal entities or toggle to consolidated parent company groups (rolling up project entities into parent utilities like RWE, EnBW, Alterric, and PROKON). Crucially, it identifies Germany's **13.1 GW repowering cliff**—turbines that have exceeded their statutory 20-year feed-in tariff under § 25 EEG—pinpointing exactly which operating entities own aging assets that must be acquired, repowered with modern multi-megawatt turbines, or shifted to corporate Power Purchase Agreements (PPAs).

### Storage Co-Location Screener (formerly Q4 BESS)
- **Question Answered:** *Where is commercial battery storage (BESS) being deployed alongside onshore wind, and where are the prime opportunities for hybrid asset retrofits?*
- **Why a Consultant Cares:** Wholesale power price volatility and frequent negative electricity pricing hours (*Abregelung*) make standalone wind farms financially vulnerable without storage arbitrage. This screener maps where battery storage units share an operator and postal code with existing wind farms. It reveals that co-location is at an early frontier (54.5 MW operating across 637 battery units, representing <0.1% penetration), allowing consultants to advise clients on which regional wind hubs offer the strongest grid-connection synergy for hybrid battery additions.

### Data Trust Center (formerly Provenance)
- **Question Answered:** *Can I put these numbers in front of a client with 100% confidence, where did each data point originate, and what was verified by a human?*
- **Why a Consultant Cares:** Consulting credibility hinges on defensible data. The Data Trust Center provides complete transparency into the platform's multi-tier governance model. It displays real-time platform health traffic lights (freshness, audit coverage, human verification rates), full audit logs of every automated data ingestion run, and an interactive human-in-the-loop workflow where company-published press claims (Tier 2) must be explicitly reviewed and approved by an analyst before they can be cited in deliverables.

---

## 3. Where the Numbers Come From and How Much to Trust Them

All figures in GTP Wind Intelligence are strictly categorized into two confidence tiers:

### Tier 1 — Official Regulatory Registry (Fact-Grade)
- **Origin:** The German Federal Network Agency (*Bundesnetzagentur*) Marktstammdatenregister (MaStR), supplemented by official federal postal mappings and statutory law texts (*gesetze-im-internet.de*).
- **Coverage:** All 38,488 wind turbines (30,358 operating, 8,130 planned) and over 2.8 million energy storage records.
- **Trust Level:** **100% Authoritative.** Zero synthetic or simulated assets. Sourced directly from German government databases where registration is mandated by federal statute (*MaStRV*). These numbers can be quoted directly in client presentations, financial models, and fairness opinions.

### Tier 2 — Company Disclosures & Press Announcements (Claim-Grade)
- **Origin:** Corporate press releases, quarterly filings, and OEM disclosures (e.g., Nordex SE order intake).
- **Processing:** Extracted using natural language processing and structured into metrics (e.g., quarterly turbine orders, average selling price).
- **Trust Level:** **Requires Human Verification.** Corporate announcements may be hedged with preliminary language (e.g., *"vorläufig"*, *"rund"*). Tier 2 figures are locked with an "Unverified" warning badge until a consultant or analyst reviews the original German sentence against the English translation and marks it as verified in the Data Trust Center.

---

## 4. How Fresh is the Data and How Do I Know?

Every page features an integrated Data Freshness Banner and timestamp:
- **🟢 Operational (Synced within 7 days):** Data reflects the current regulatory snapshot. Fully cleared for live client presentations.
- **🟡 Moderate (Synced within 8–30 days):** Pipeline is operational, with the scheduled monthly regulatory refresh upcoming.
- **🔴 Stale (> 30 days):** Data has not synced within the standard monthly cycle; an analyst should trigger a pipeline refresh before issuing final deliverables.

The exact regulatory snapshot date (e.g., *"2026-09-27"*) and cryptographic audit execution ID are embedded in the footer of every page and every exported Excel sheet.

---

## 5. What This Tool Cannot Yet Do (Honest Scope & Limitations)

To maintain intellectual honesty when presenting to sophisticated investment partners, consultants must be clear on current prototype boundaries:

1. **Parent Company Ownership is Heuristic, Not Legal Chain-of-Title:** The corporate rollup groups SPVs using deterministic brand keyword matching across 28 leading German utilities and developers. While highly accurate for market concentration screening, it does not replace a formal title search in the German Commercial Register (*Handelsregister*) for complex cross-holdings.
2. **BESS Co-Location Uses a Statistical Proxy:** Because the public MaStR export does not provide a direct foreign key between wind turbines and batteries, co-location is identified when an operating battery shares both the exact operator registration ID (*ABR number*) and 5-digit postal code with a wind farm. It does not verify single-line electrical diagrams behind the meter.
3. **Tier 2 Press Scraper is Currently Scoped to Nordex:** The machine extraction of unstructured press releases is fully functional but currently seeded with Nordex SE filings as a demonstration. Vestas, Enercon, and Siemens Gamesa integrations are roadmap items.
4. **National Percentile Benchmarking is Scheduled for Phase 2:** The underlying database supports benchmarking, but the automated "Compare any client asset to the national median" scoring widget is scheduled for the next release.

---

## 6. Worked Example: Answering a Real Client Acquisition Question

### Client Question:
> *"We are an infrastructure fund with €150M to deploy into German onshore wind repowering. Which Bundesland should we target for asset acquisitions, who are the primary operators to approach, and how fast can we permit replacement turbines?"*

### Step-by-Step Consulting Workflow:

1. **Step 1: Identify the Repowering Target Pool (Open: *Operator Intelligence & Repowering Radar*)**
   - Look at the **Statutory 20-Year Subsidy Cliff (§ 25 EEG)** banner.
   - Note the headline: Germany has **13.1 GW (10,524 turbines)** operating entirely post-subsidy on merchant prices, plus **3.3 GW (1,747 turbines)** entering the cliff within 24 months.
   - Check the **Top Expired Repowering States**: Niedersachsen leads with **3.24 GW (2,659 turbines)** past subsidy, followed by Brandenburg (**2.34 GW**) and Sachsen-Anhalt (**1.76 GW**).
   - *Recommendation:* Prioritize **Niedersachsen** as the primary acquisition hunt ground due to the deepest volume of post-subsidy assets.

2. **Step 2: Evaluate Market Concentration & Operator Targets (On the same page)**
   - Set the toggle to **"View by: Parent Company Group"**.
   - Review the Top 5 market share: The top 5 parent groups control just **4.83%** of national operating capacity (3,428 MW), confirming severe market fragmentation.
   - *Recommendation:* Avoid trying to buy large utility portfolios from RWE or EnBW (who repower in-house). Instead, scroll down to the **Searchable Operator Lookup** and inspect independent regional developers and citizen energy cooperatives (*Bürgerwindparks*), which hold over 90% of the repowering candidates.

3. **Step 3: Audit Permitting Lead Times (Open: *Development Pipeline & Permitting Radar*)**
   - Review the **Permitting Speed by Bundesland** chart.
   - Locate **Niedersachsen**: Check the median permitting cycle time (typically ~18.5 months, color-coded 🟡 Amber).
   - Compare against lagging states like Bayern or Baden-Württemberg (🔴 Red, > 25 months).
   - *Recommendation:* Niedersachsen offers an acceptable regulatory timeline under regional planning laws, avoiding the multi-year litigation bottlenecks seen in southern forested ridges.

4. **Step 4: Screen for Storage Upside (Open: *Storage Co-Location Screener*)**
   - Filter the state dropdown to **Niedersachsen**.
   - Note current BESS penetration: Despite high wind capacity, co-located battery storage penetration in Niedersachsen remains under 0.05%.
   - *Recommendation:* Structure the acquisition business case with a **hybrid repowering thesis**: replace aging 1.5 MW turbines with 6 MW turbines and add co-located BESS at the existing grid connection point to capture curtailment arbitrage.

5. **Step 5: Verify Data Provenance (Open: *Data Trust Center*)**
   - Confirm the platform status shows **🟢 Operational**.
   - Verify that all turbine counts and capacity metrics are **Tier 1 Official** sourced from Bundesnetzagentur.
   - Click the export button to download the audit CSV for your pitch deck appendix.
