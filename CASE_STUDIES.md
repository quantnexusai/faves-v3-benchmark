# FAVES V3 Case Studies

These case studies demonstrate practical usage of FAVES V3 for regulatory compliance screening in drug discovery workflows.

---

## Case Study 1: Single Compound Compliance Check

**Scenario:** A medicinal chemist has designed a novel analgesic candidate and needs to verify it does not match any DEA-controlled substance scaffolds before advancing to synthesis.

### Input

The candidate compound has a piperidine-phenyl core. The chemist submits its SMILES:

```python
import requests

candidate_smiles = "CCC(=O)N(c1ccccc1)C2CCN(CCc3ccccc3)CC2"

response = requests.post(
    "https://ai.novomcp.com/mcp/tools/get_molecule_profile",
    json={"arguments": {"smiles": candidate_smiles}},
    headers={"Content-Type": "application/json"},
    timeout=30,
)
result = response.json()["result"]
compliance = result["compliance"]

print(f"Status:          {compliance['status']}")
print(f"DEA Controlled:  {compliance['is_dea_controlled']}")
print(f"Scaffold Match:  {compliance['is_scaffold_match']}")
print(f"Whitelisted:     {compliance['is_whitelisted']}")
print(f"Flag Count:      {compliance['faves_flag_count']}")
```

### Expected Output

```
Status:          controlled
DEA Controlled:  True
Scaffold Match:  True
Whitelisted:     False
Flag Count:      2
```

### Interpretation

The candidate is flagged because it matches the **fentanyl scaffold** (4-anilidopiperidine core). The SMILES submitted is in fact fentanyl itself (CID 3345). The chemist must modify the scaffold to avoid regulatory issues, or pursue an alternative structural series.

---

## Case Study 2: Batch Screening of a Virtual Library

**Scenario:** A computational chemistry team has generated 500 compounds from a generative model targeting a novel kinase. Before running docking simulations, they need to filter out any compounds that would trigger regulatory flags.

### Input

```python
import requests
import pandas as pd
import time

# Load virtual library (CSV with 'smiles' column)
library = pd.read_csv("virtual_library_500.csv")

results = []
for idx, row in library.iterrows():
    try:
        resp = requests.post(
            "https://ai.novomcp.com/mcp/tools/get_molecule_profile",
            json={"arguments": {"smiles": row["smiles"]}},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        data = resp.json()["result"]
        compliance = data.get("compliance", {})

        results.append({
            "smiles": row["smiles"],
            "status": compliance.get("status"),
            "is_dea_controlled": compliance.get("is_dea_controlled", False),
            "is_scaffold_match": compliance.get("is_scaffold_match", False),
            "faves_flag_count": compliance.get("faves_flag_count", 0),
        })
    except Exception as e:
        results.append({"smiles": row["smiles"], "error": str(e)})

    if idx % 50 == 0:
        print(f"Processed {idx}/{len(library)}")
    time.sleep(0.1)

# Convert to DataFrame and filter
results_df = pd.DataFrame(results)
clean = results_df[results_df["faves_flag_count"] == 0]
flagged = results_df[results_df["faves_flag_count"] > 0]

print(f"\nResults:")
print(f"  Total screened:  {len(results_df)}")
print(f"  Cleared:         {len(clean)}")
print(f"  Flagged:         {len(flagged)}")

# Save cleared compounds for docking
clean.to_csv("virtual_library_cleared.csv", index=False)
flagged.to_csv("virtual_library_flagged.csv", index=False)
```

### Expected Output

```
Results:
  Total screened:  500
  Cleared:         487
  Flagged:         13
```

### Interpretation

Of the 500 generated compounds, 13 triggered compliance flags. The team inspects `virtual_library_flagged.csv` and finds:
- 2 compounds with phenethylamine scaffolds (stimulant class)
- 8 compounds with benzodiazepine-like fused ring systems
- 3 compounds flagged as scaffold matches for cannabinoid cores

The 487 cleared compounds proceed to docking. The 13 flagged compounds are deprioritized or redesigned.

---

## Case Study 3: Integration into a Drug Discovery Pipeline

**Scenario:** A drug discovery platform runs an automated pipeline: generate candidates, predict ADMET, dock against target, and rank. FAVES V3 is integrated as a compliance gate after generation and before ADMET prediction, ensuring no controlled substance analogues enter the pipeline.

### Architecture

```
Generative Model → FAVES V3 Compliance Gate → ADMET Prediction → Docking → Ranking
                          ↓ (flagged)
                   Flagged Compounds Log
```

### Implementation

```python
import requests
from typing import List, Dict

class FAVESComplianceGate:
    """Compliance gate using FAVES V3 for drug discovery pipelines."""

    def __init__(self, api_url="https://ai.novomcp.com", api_key=None):
        self.api_url = api_url
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["X-API-Key"] = api_key

    def check_molecule(self, smiles: str) -> Dict:
        """Check a single molecule for compliance."""
        resp = requests.post(
            f"{self.api_url}/mcp/tools/get_molecule_profile",
            json={"arguments": {"smiles": smiles}},
            headers=self.headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["result"]["compliance"]

    def filter_library(self, smiles_list: List[str]) -> Dict[str, List[str]]:
        """Filter a library into cleared and flagged compounds."""
        cleared = []
        flagged = []

        for smiles in smiles_list:
            try:
                compliance = self.check_molecule(smiles)
                if compliance.get("faves_flag_count", 0) == 0:
                    cleared.append(smiles)
                else:
                    flagged.append(smiles)
            except Exception:
                flagged.append(smiles)  # Flag on error for safety

        return {"cleared": cleared, "flagged": flagged}


# Usage in pipeline
gate = FAVESComplianceGate()

# After generative model produces candidates
generated_smiles = ["CCO", "CC(=O)Oc1ccccc1C(=O)O", ...]
result = gate.filter_library(generated_smiles)

print(f"Cleared: {len(result['cleared'])} compounds → proceed to ADMET")
print(f"Flagged: {len(result['flagged'])} compounds → logged and excluded")

# Pass cleared compounds to next pipeline stage
run_admet_prediction(result["cleared"])
```

### Integration Notes

1. **Position in pipeline:** Place the compliance gate early (after generation, before expensive computations like docking or MD simulation) to avoid wasting compute on non-viable candidates.

2. **Error handling:** Default to flagging on API errors. It is safer to exclude a compound that could not be evaluated than to pass it through unchecked.

3. **Logging:** Log all flagged compounds with their SMILES and flag reasons for audit trails. Regulatory compliance requires documentation.

4. **Periodic re-screening:** DEA scheduling changes over time. Re-screen compound libraries quarterly or when scheduling updates are announced.

5. **Latency:** Pre-computed molecules return in <10 ms. For novel molecules, budget 50-200 ms per query. For large libraries, run compliance checks asynchronously.

---

## Reproducing Paper Results

To reproduce the benchmark results reported in the paper:

```bash
git clone https://github.com/quantnexusai/faves-v3-benchmark.git
cd faves-v3-benchmark

pip install requests pandas

# Fetch SMILES from PubChem and validate against FAVES API
python faves_benchmark.py --all
```

This will:
1. Fetch canonical SMILES for all 102 benchmark compounds from PubChem
2. Submit each to the FAVES V3 API
3. Compare predictions against ground truth
4. Generate a benchmark report with sensitivity, specificity, and confusion matrix

Expected results: 47/47 controlled substances detected (100% sensitivity), 0/55 false positives (100% specificity).
