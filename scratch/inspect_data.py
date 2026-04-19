import pandas as pd

try:
    df = pd.read_excel("data_set.xlsx")
    print("Columns:", df.columns.tolist())
    print("\nFirst 10 rows:")
    print(df.head(10).to_string())
    print("\nSummary Statistics for numeric columns:")
    print(df.describe())
except Exception as e:
    print(f"Error reading Excel: {e}")
