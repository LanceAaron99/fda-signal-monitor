import os, re
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)
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

# Signal rule: Evans criteria + ROR + IC, at least 5 reports
df["is_signal"] = ((df["a"] >= 5) & (df["prr"] >= 2) & (df["chi2"] >= 4)
                   & (df["ror_lower"] > 1) & (df["ic025"] > 0))
signals = df[df["is_signal"]].sort_values("ic025", ascending=False).copy()

# ---- Flag possible indication bias ----
ind = pd.read_sql("SELECT drug, indication FROM drug_indications", engine)
ind = ind[~ind["indication"].str.contains("UNKNOWN|OFF LABEL", na=True)]

STOP = {"DISEASE", "DISORDER", "SYNDROME", "CHRONIC", "ACUTE", "SEVERE",
        "PRIMARY", "CONDITION", "AGGRAVATED", "INCREASED", "DECREASED", "ABNORMAL"}

def words(text):
    """Key words (5+ letters, not generic) used for matching."""
    return {w for w in re.findall(r"[A-Z]+", text) if len(w) >= 5 and w not in STOP}

ind_exact = ind.groupby("drug")["indication"].apply(set).to_dict()
ind_words = {drug: set().union(*(words(x) for x in s)) for drug, s in ind_exact.items()}

def looks_like_indication(drug, reaction):
    if reaction in ind_exact.get(drug, set()):
        return True
    return bool(words(reaction) & ind_words.get(drug, set()))

signals["possible_indication"] = [looks_like_indication(r.drug, r.reaction)
                                  for r in signals.itertuples()]

signals.round(3).to_sql("signals", engine, if_exists="replace", index=False)

flagged = signals["possible_indication"].sum()
print(f"Pairs tested: {len(df):,} | Signals: {len(signals):,} | "
      f"Flagged as possible indication: {flagged:,} ✅ saved to 'signals' table")

cols = ["drug", "reaction", "a", "expected", "prr", "ic025"]
print("\nTop CLEAN signals (indication bias removed):")
print(signals.loc[~signals["possible_indication"], cols].head(15).round(1))
print("\nExamples flagged as possible indication:")
print(signals.loc[signals["possible_indication"], cols].head(8).round(1))