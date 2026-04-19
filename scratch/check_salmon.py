import pandas as pd
try:
    df = pd.read_excel("data_set.xlsx")
    found = df[df.apply(lambda row: row.astype(str).str.contains('Salmon', case=False).any(), axis=1)]
    print(f"Found {len(found)} rows with 'Salmon'")
    if len(found) > 0:
        print(found)
except Exception as e:
    print(e)
