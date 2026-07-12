import pandas as pd
import glob

csv_files = glob.glob("./data/*.csv")
if not csv_files:
    raise FileNotFoundError("No CSV found in ./data — check that the download unzipped correctly.")

csv_path = csv_files[0]
print(f"Reading: {csv_path}\n")

df = pd.read_csv(csv_path, nrows=100000)

print("Columns:", list(df.columns))
print("\nShape (sample of 100,000 rows):", df.shape)
print("\nTransaction types:\n", df['type'].value_counts())
print("\nFraud rate in this sample:", df['isFraud'].mean())
print("\nFlagged-fraud rate in this sample:", df['isFlaggedFraud'].mean())
print("\nFirst 5 rows:\n", df.head())
print("\nData types:\n", df.dtypes)