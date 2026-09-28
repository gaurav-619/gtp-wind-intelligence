import duckdb

con = duckdb.connect('db/gtp.duckdb')

print("=== 1. STORAGE UNIT (BESS) ===")
bess_df = con.execute("""
    SELECT mastr_id, display_name, nettonennleistung_mw, postleitzahl, matched_wind_mastr_id, operator_name, operator_mastr_id
    FROM storage_units
    WHERE mastr_id = 'SEE906749239827'
""").df()
print(bess_df.to_string())

print("\n=== 2. MATCHED WIND TURBINE ===")
wind_df = con.execute("""
    SELECT mastr_id, display_name, nettonennleistung_mw, postleitzahl, bundesland, operator_name, operator_mastr_id
    FROM wind_plants
    WHERE mastr_id = 'SEE905058508594'
""").df()
print(wind_df.to_string())

print("\n=== 3. TOP 5 CO-LOCATED BESS UNITS BY CAPACITY ===")
top5_df = con.execute("""
    SELECT mastr_id, display_name, nettonennleistung_mw, postleitzahl, matched_wind_mastr_id, operator_name
    FROM storage_units
    WHERE matched_wind_mastr_id IS NOT NULL
    ORDER BY nettonennleistung_mw DESC
    LIMIT 5
""").df()
print(top5_df.to_string())
con.close()
