import pandas as pd
try:
    df = pd.read_excel("market_data.xlsx")
    print(df.head())
    print(df.columns)
    print(df.info())
except Exception as e:
    print(e)
