import os
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
pd.set_option("display.width", 200)
engine = create_engine(os.getenv("DATABASE_URL"))

df = pd.read_sql("SELECT * FROM drug_reaction_counts", engine)
a, b, c, d = (df[x].astype(float) for x in "abcd")
n = a + b + c + d

# If any cell is 0, add 0.5 to all cells (avoids dividing by zero)
zero = ((b == 0) | (c == 0) | (d == 0)).astype(float)
a2, b2, c2, d2 = (x + 0.5 * zero for x in (a, b, c, d))

# PRR: how much more often the reaction appears with this drug
df["prr"] = (a2 / (a2 + b2)) / (c2 / (c2 + d2))

# Chi-square (with Yates correction): is it statistically significant?
df["chi2"] = (n * (np.abs(a * d - b * c) - n / 2).clip(lower=0) ** 2
              / ((a + b) * (c + d) * (a + c) * (b + d)))

# ROR with a 95% confidence interval
df["ror"] = (a2 * d2) / (b2 * c2)
se = np.sqrt(1 / a2 + 1 / b2 + 1 / c2 + 1 / d2)
df["ror_lower"] = np.exp(np.log(df["ror"]) - 1.96 * se)
df["ror_upper"] = np.exp(np.log(df["ror"]) + 1.96 * se)

# Information Component (WHO's Bayesian method): shrinks small counts
df["expected"] = (a + b) * (a + c) / n
df["ic"] = np.log2((a + 0.5) / (df["expected"] + 0.5))
df["ic025"] = df["ic"] - 3.3 * (a + 0.5) ** -0.5 - 2 * (a + 0.5) ** -1.5

# Stricter signal rule: Evans criteria + ROR + IC, at least 5 reports
df["is_signal"] = ((df["a"] >= 5) & (df["prr"] >= 2) & (df["chi2"] >= 4)
                   & (df["ror_lower"] > 1) & (df["ic025"] > 0))

signals = df[df["is_signal"]].sort_values("ic025", ascending=False)
signals.round(3).to_sql("signals", engine, if_exists="replace", index=False)

print(f"Pairs tested: {len(df):,} | Signals found: {len(signals):,} "
      f"({100 * len(signals) / len(df):.1f}%) ✅ saved to 'signals' table")
print("\nTop signals (ranked by IC025, the most confident first):")
cols = ["drug", "reaction", "a", "expected", "prr", "ic025"]
print(signals[cols].head(15).round(1))