# FAVES V3 User Manual

## Overview

FAVES V3 (Fairness, Accountability, Validity, Ethics, Safety) is a three-tier regulatory compliance detection system for molecular databases. It identifies DEA-controlled substances and their structural analogues via a REST API.

**API Base URL:** `https://ai.novomcp.com`

---

## Quick Start

### Single Molecule Query

```bash
curl -X POST https://ai.novomcp.com/mcp/tools/get_molecule_profile \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"smiles": "CN1C2CCC1CC(C2)OC(=O)C(CO)c3ccccc3"}}'
```

### Python Example

```python
import requests

response = requests.post(
    "https://ai.novomcp.com/mcp/tools/get_molecule_profile",
    json={"arguments": {"smiles": "CN1C2CCC1CC(C2)OC(=O)C(CO)c3ccccc3"}},
    headers={"Content-Type": "application/json"},
    timeout=30,
)
data = response.json()["result"]
compliance = data["compliance"]

print(f"Controlled: {compliance['is_dea_controlled']}")
print(f"Status: {compliance['status']}")
```

---

## API Reference

### Endpoint: `get_molecule_profile`

**URL:** `POST /mcp/tools/get_molecule_profile`

**Request Body:**
```json
{
  "arguments": {
    "smiles": "<SMILES string>"
  }
}
```

**Response Structure:**
```json
{
  "result": {
    "in_database": true,
    "source": "precomputed",
    "compliance": {
      "status": "controlled | cleared | review",
      "is_dea_controlled": true,
      "is_whitelisted": false,
      "is_scaffold_match": false,
      "is_fda_banned": false,
      "is_cwc_scheduled": false,
      "faves_flag_count": 1
    }
  }
}
```

### Endpoint: `check_compliance`

**URL:** `POST /mcp/tools/check_compliance`

Provides context-dependent compliance assessment with jurisdiction-specific recommendations.

**Request Body:**
```json
{
  "arguments": {
    "smiles": "<SMILES string>",
    "context": {
      "intended_use": "pharmaceutical",
      "jurisdiction": "US"
    }
  }
}
```

---

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `is_dea_controlled` | boolean | Exact match against DEA reference database |
| `is_whitelisted` | boolean | Match against FDA-approved therapeutics whitelist |
| `is_scaffold_match` | boolean | Match against 37 SMARTS scaffold patterns |
| `is_fda_banned` | boolean | FDA banned substance flag |
| `is_cwc_scheduled` | boolean | Chemical Weapons Convention flag |
| `faves_flag_count` | integer | Total number of compliance flags raised |
| `status` | string | Overall status: "controlled", "cleared", or "review" |

### Status Values

- **`controlled`**: Molecule matched as a DEA-scheduled substance (Tier 2 direct match)
- **`cleared`**: Molecule matched the whitelist of known safe compounds (Tier 1)
- **`review`**: Molecule matched a controlled substance scaffold pattern (Tier 3) and may require manual review

---

## Detection Tiers

FAVES V3 processes molecules through three sequential tiers:

1. **Tier 1 — Whitelist Verification**: Checks against curated FDA-approved therapeutics. If matched, the molecule is immediately cleared. This prevents false positives on known safe drugs.

2. **Tier 2 — Direct Molecular Matching**: Checks against a reference database of DEA-scheduled substances using canonical SMILES and InChIKey. Exact matches are flagged as controlled.

3. **Tier 3 — Scaffold Pattern Analysis**: Applies 37 SMARTS patterns covering opioids, benzodiazepines, stimulants, cannabinoids, hypnotics/sedatives, and dissociatives/hallucinogens. Matches indicate potential controlled substance analogues.

---

## Batch Screening

For screening multiple compounds, use the benchmark script:

```bash
# Install dependencies
pip install requests pandas

# Prepare a CSV with columns: name, smiles
# Run validation
python faves_benchmark.py --validate
```

Or use Python directly:

```python
import requests
import time

smiles_list = ["CCO", "CN1C=NC2=C1C(=O)N(C(=O)N2C)C", ...]

results = []
for smiles in smiles_list:
    resp = requests.post(
        "https://ai.novomcp.com/mcp/tools/get_molecule_profile",
        json={"arguments": {"smiles": smiles}},
        timeout=30,
    )
    results.append(resp.json()["result"])
    time.sleep(0.1)  # Rate limiting: ~10 queries/sec recommended
```

---

## Rate Limits

| Tier | Queries/sec | Monthly Limit |
|------|-------------|---------------|
| Free | 10 | 1,000 |
| Academic | 50 | 50,000 |
| Commercial | 500 | Unlimited |

---

## Pre-computed Database

FAVES V3 has pre-screened 122,352,847 molecules from PubChem. Queries for pre-computed molecules return in <10 ms. Novel molecules not in the database are evaluated in real-time (50-200 ms) via scaffold pattern matching.

---

## Running the Benchmark

To reproduce the validation results from the paper:

```bash
# Step 1: Fetch ground truth SMILES from PubChem
python faves_benchmark.py --fetch-data

# Step 2: Validate against FAVES API
python faves_benchmark.py --validate

# Step 3: Generate report
python faves_benchmark.py --report

# Or run all steps:
python faves_benchmark.py --all
```

Output files:
- `data/ground_truth.csv` — Compound SMILES and expected classifications
- `results/validation_results_<timestamp>.csv` — Raw API responses
- `results/benchmark_report_<date>.md` — Formatted benchmark report

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| HTTP 429 (rate limited) | Reduce query frequency; add `time.sleep(0.2)` between requests |
| HTTP 500 on novel SMILES | Verify SMILES validity with RDKit before submitting |
| Molecule not in database | Expected for novel compounds; real-time scaffold matching will still run |
| Unexpected `review` status | Scaffold match detected; verify structure manually |

---

## Citation

If you use FAVES V3 in your research, please cite:

> Harrison, A. FAVES V3: A Three-Tier Regulatory Compliance Detection System for Molecular Databases. *J. Chem. Inf. Model.* **2026**. DOI: [pending]

---

## Contact

- **API issues:** support@novoquantnexus.com
- **Research inquiries:** ari@novoquantnexus.com
- **Bug reports:** https://github.com/quantnexusai/faves-v3-benchmark/issues
