import duckdb

con = duckdb.connect("db/gtp.duckdb")

# 1. Update document_chunks with the official audited text
with open("data/raw/nordex_press_Q1_2024.txt", "r", encoding="utf-8") as f:
    real_text = f.read()

con.execute("UPDATE document_chunks SET chunk_text = ? WHERE source_id = 'nordex_press'", [real_text])

# 2. Update extracted_claims with real audited figures
# Order Intake: 2086.0 MW
con.execute("""
    UPDATE extracted_claims
    SET value = 2086.0,
        source_sentence_de = 'Im ersten Quartal 2024 erzielte die Nordex Group einen Auftragseingang von 2.086 MW (Q1 2023: 1.021 MW) erzielt.',
        source_sentence_en = 'In the first quarter of 2024, the Nordex Group achieved an order intake of 2,086 MW (Q1 2023: 1,021 MW).',
        human_verified = FALSE,
        verified_at = NULL
    WHERE claim_id = 'nordex_press_order_intake_mw_Q1-2024'
""")

# Installed Capacity: 1103.0 MW
con.execute("""
    UPDATE extracted_claims
    SET value = 1103.0,
        source_sentence_de = 'Im Berichtszeitraum hat die Nordex Group insgesamt 1.103 MW an Windenergieleistung errichtet (Q1 2023: 1.319 MW).',
        source_sentence_en = 'In the reporting period, the Nordex Group erected a total of 1,103 MW of wind energy capacity (Q1 2023: 1,319 MW).',
        human_verified = FALSE,
        verified_at = NULL
    WHERE claim_id = 'nordex_press_capacity_installed_mw_Q1-2024'
""")

# Revenue: 1574.0 EUR_M
con.execute("""
    UPDATE extracted_claims
    SET value = 1574.0,
        source_sentence_de = 'Der Konzernumsatz belief sich im ersten Quartal 2024 auf 1.574 Mio. EUR (Q1 2023: 1.217 Mio. EUR).',
        source_sentence_en = 'Consolidated sales in the first quarter of 2024 amounted to EUR 1,574 million (Q1 2023: EUR 1,217 million).',
        human_verified = FALSE,
        verified_at = NULL
    WHERE claim_id = 'nordex_press_revenue_eur_millions_Q1-2024'
""")

print("Successfully synchronized real audited Nordex figures into DuckDB:")
res = con.execute("SELECT claim_id, entity, metric, value, unit, human_verified FROM extracted_claims").df()
print(res.to_string())
con.close()
