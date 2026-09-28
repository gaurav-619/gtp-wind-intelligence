import duckdb

con = duckdb.connect("db/gtp.duckdb")

pdf_url = "https://ir.nordex-online.com/media/document/36513768-7bf3-40ac-bd9a-f283ff7cb92f/assets/DE000A0D6554-Q1-2024-EQ-E-00.pdf"

con.execute("UPDATE extracted_claims SET document_url = ? WHERE source_id = 'nordex_press'", [pdf_url])
con.execute("UPDATE sources SET source_url = ? WHERE source_id = 'nordex_press'", [pdf_url])
con.execute("UPDATE document_chunks SET document_url = ? WHERE source_id = 'nordex_press'", [pdf_url])

print("Updated document_url across extracted_claims, sources, and document_chunks:")
res = con.execute("SELECT claim_id, entity, metric, value, unit, document_url FROM extracted_claims").df()
print(res.to_string())
con.close()
