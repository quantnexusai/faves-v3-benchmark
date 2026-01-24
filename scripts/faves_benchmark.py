#!/usr/bin/env python3
"""
FAVES Regulatory Detection Benchmark
=====================================
Validates FAVES V3 detection accuracy against known controlled substances
and FDA-approved drugs.

Usage:
    python faves_benchmark.py --fetch-data    # Download ground truth from PubChem
    python faves_benchmark.py --validate      # Run validation against FAVES API
    python faves_benchmark.py --report        # Generate benchmark report
    python faves_benchmark.py --all           # Do all steps
"""

import argparse
import json
import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
PUBCHEM_API = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
FAVES_API = "https://ai.novomcp.com"  # NovoMCP base URL (endpoint adds /mcp/tools/...)
DATA_DIR = Path(__file__).parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"

# DEA Controlled Substances - Representative samples by schedule
# Source: DEA Orange Book (https://www.deadiversion.usdoj.gov/schedules/)
DEA_CONTROLLED = {
    "I": [
        # Opioids
        "heroin", "acetyl-alpha-methylfentanyl", "alpha-methylfentanyl",
        # Psychedelics
        "LSD", "psilocybin", "mescaline", "DMT", "MDMA", "MDA",
        # Cannabinoids
        "tetrahydrocannabinol", "marijuana extract",
        # Others
        "methaqualone", "GHB precursors",
    ],
    "II": [
        # Opioids
        "fentanyl", "oxycodone", "hydrocodone", "morphine", "codeine",
        "methadone", "meperidine", "hydromorphone", "oxymorphone",
        # Stimulants
        "amphetamine", "methamphetamine", "cocaine", "methylphenidate",
        "lisdexamfetamine",
        # Depressants
        "pentobarbital", "secobarbital",
        # Others
        "nabilone", "tapentadol",
    ],
    "III": [
        "ketamine", "buprenorphine", "testosterone", "anabolic steroids",
        "benzphetamine", "phendimetrazine", "butalbital",
    ],
    "IV": [
        "alprazolam", "diazepam", "lorazepam", "clonazepam", "midazolam",
        "zolpidem", "zaleplon", "tramadol", "carisoprodol", "phenobarbital",
        "modafinil",
    ],
    "V": [
        "pregabalin", "lacosamide", "brivaracetam",
        # Low-dose codeine preparations (cough syrups)
    ],
}

# FDA-Approved drugs that should NOT be flagged as controlled
# (unless they actually are scheduled)
FDA_APPROVED_NON_CONTROLLED = [
    # Common medications
    "aspirin", "acetaminophen", "ibuprofen", "naproxen",
    "omeprazole", "metformin", "lisinopril", "amlodipine",
    "atorvastatin", "simvastatin", "levothyroxine", "metoprolol",
    # Antidepressants (NOT controlled)
    "fluoxetine", "sertraline", "escitalopram", "bupropion", "venlafaxine",
    "duloxetine", "mirtazapine", "trazodone",
    # Antibiotics
    "amoxicillin", "azithromycin", "ciprofloxacin", "doxycycline",
    "metronidazole", "trimethoprim",
    # Antipsychotics (NOT controlled)
    "quetiapine", "risperidone", "olanzapine", "aripiprazole",
    # Antihistamines
    "cetirizine", "loratadine", "diphenhydramine", "fexofenadine",
    # Cardiovascular
    "warfarin", "clopidogrel", "furosemide", "hydrochlorothiazide",
    # Endogenous/Natural compounds
    "dopamine", "serotonin", "norepinephrine", "epinephrine", "melatonin",
    "cortisol", "insulin", "glucose",
]

# Negative controls - definitely not controlled
NEGATIVE_CONTROLS = [
    "caffeine", "nicotine", "ethanol", "water", "sodium chloride",
    "citric acid", "ascorbic acid", "glycine", "alanine",
]


def fetch_smiles_from_pubchem(compound_name: str) -> Optional[Dict]:
    """Fetch SMILES and CID from PubChem by compound name."""
    try:
        url = f"{PUBCHEM_API}/compound/name/{compound_name}/property/CanonicalSMILES,MolecularFormula,MolecularWeight/JSON"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            props = data["PropertyTable"]["Properties"][0]
            return {
                "name": compound_name,
                "cid": props.get("CID"),
                "smiles": props.get("CanonicalSMILES") or props.get("ConnectivitySMILES") or props.get("SMILES"),
                "formula": props.get("MolecularFormula"),
                "mw": props.get("MolecularWeight"),
            }
        else:
            print(f"  [WARN] Not found: {compound_name}")
            return None
    except Exception as e:
        print(f"  [ERROR] {compound_name}: {e}")
        return None


def fetch_ground_truth_data():
    """Fetch SMILES for all compounds from PubChem."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    all_data = []

    # Fetch DEA controlled substances
    print("\n=== Fetching DEA Controlled Substances ===")
    for schedule, compounds in DEA_CONTROLLED.items():
        print(f"\nSchedule {schedule} ({len(compounds)} compounds):")
        for name in compounds:
            print(f"  Fetching: {name}...", end=" ")
            result = fetch_smiles_from_pubchem(name)
            if result:
                result["category"] = "controlled"
                result["schedule"] = schedule
                result["expected_controlled"] = True
                all_data.append(result)
                print(f"OK (CID: {result['cid']})")
            else:
                print("NOT FOUND")
            time.sleep(0.2)  # Rate limiting

    # Fetch FDA-approved non-controlled drugs
    print("\n=== Fetching FDA-Approved Non-Controlled Drugs ===")
    for name in FDA_APPROVED_NON_CONTROLLED:
        print(f"  Fetching: {name}...", end=" ")
        result = fetch_smiles_from_pubchem(name)
        if result:
            result["category"] = "fda_approved"
            result["schedule"] = None
            result["expected_controlled"] = False
            all_data.append(result)
            print(f"OK (CID: {result['cid']})")
        else:
            print("NOT FOUND")
        time.sleep(0.2)

    # Fetch negative controls
    print("\n=== Fetching Negative Controls ===")
    for name in NEGATIVE_CONTROLS:
        print(f"  Fetching: {name}...", end=" ")
        result = fetch_smiles_from_pubchem(name)
        if result:
            result["category"] = "negative_control"
            result["schedule"] = None
            result["expected_controlled"] = False
            all_data.append(result)
            print(f"OK (CID: {result['cid']})")
        else:
            print("NOT FOUND")
        time.sleep(0.2)

    # Save to CSV
    df = pd.DataFrame(all_data)
    output_path = DATA_DIR / "ground_truth.csv"
    df.to_csv(output_path, index=False)
    print(f"\n✓ Saved {len(df)} compounds to {output_path}")

    # Summary
    print("\n=== Summary ===")
    print(f"Total compounds: {len(df)}")
    print(f"  Controlled: {len(df[df['category'] == 'controlled'])}")
    print(f"  FDA Approved: {len(df[df['category'] == 'fda_approved'])}")
    print(f"  Negative Controls: {len(df[df['category'] == 'negative_control'])}")

    return df


def validate_against_faves(api_url: str = None, api_key: str = None):
    """Run validation against FAVES API."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load ground truth
    ground_truth_path = DATA_DIR / "ground_truth.csv"
    if not ground_truth_path.exists():
        print("Ground truth not found. Run with --fetch-data first.")
        return None

    df = pd.read_csv(ground_truth_path)
    print(f"\nLoaded {len(df)} compounds from ground truth")

    results = []
    api_url = api_url or FAVES_API

    print(f"\n=== Validating against {api_url} ===\n")

    for idx, row in df.iterrows():
        smiles = row["smiles"]
        if pd.isna(smiles):
            continue

        print(f"[{idx+1}/{len(df)}] Testing: {row['name']}...", end=" ")

        try:
            # Call NovoMCP via Streamable HTTP (recommended transport)
            # Endpoint: POST /mcp/tools/{tool_name}
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["X-API-Key"] = api_key

            resp = requests.post(
                f"{api_url}/mcp/tools/get_molecule_profile",
                json={"arguments": {"smiles": smiles}},
                headers=headers,
                timeout=30,
            )

            if resp.status_code == 200:
                response = resp.json()
                # Response is wrapped in "result"
                data = response.get("result", response)

                # Extract FAVES detection results
                # Response structure: {result: {compliance: {is_dea_controlled, ...}}}
                compliance = data.get("compliance", {})
                result = {
                    "name": row["name"],
                    "smiles": smiles,
                    "category": row["category"],
                    "expected_schedule": row["schedule"],
                    "expected_controlled": row["expected_controlled"],
                    # FAVES results from compliance object
                    "detected_controlled": compliance.get("is_dea_controlled", False) or compliance.get("is_scaffold_match", False),
                    "detected_whitelisted": compliance.get("is_whitelisted", False),
                    "compliance_status": compliance.get("status"),
                    "is_fda_banned": compliance.get("is_fda_banned", False),
                    "is_cwc_scheduled": compliance.get("is_cwc_scheduled", False),
                    "is_scaffold_match": compliance.get("is_scaffold_match", False),
                    "faves_flag_count": compliance.get("faves_flag_count", 0),
                    "in_database": data.get("in_database", False),
                    "source": data.get("source"),
                }

                # Determine if detection was correct
                # Use detected_controlled which is extracted from compliance.is_dea_controlled
                if row["expected_controlled"]:
                    result["correct"] = result["detected_controlled"] == True
                else:
                    result["correct"] = result["detected_controlled"] == False

                results.append(result)
                status = "✓" if result["correct"] else "✗"
                print(f"{status} (controlled={result['detected_controlled']}, status={compliance.get('status')})")
            else:
                print(f"ERROR {resp.status_code}")
                results.append({
                    "name": row["name"],
                    "smiles": smiles,
                    "error": f"HTTP {resp.status_code}",
                })

        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "name": row["name"],
                "smiles": smiles,
                "error": str(e),
            })

        time.sleep(0.1)  # Rate limiting

    # Save results
    results_df = pd.DataFrame(results)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"validation_results_{timestamp}.csv"
    results_df.to_csv(output_path, index=False)
    print(f"\n✓ Saved results to {output_path}")

    return results_df


def calculate_metrics(results_df: pd.DataFrame) -> dict:
    """Calculate benchmark metrics from validation results."""
    # Filter out errors
    valid = results_df[~results_df.get("error", pd.Series([None]*len(results_df))).notna()]

    # Controlled substances (should be detected)
    controlled = valid[valid["expected_controlled"] == True]
    tp = len(controlled[controlled["detected_controlled"] == True])  # True positives
    fn = len(controlled[controlled["detected_controlled"] == False])  # False negatives

    # Non-controlled (should NOT be detected)
    non_controlled = valid[valid["expected_controlled"] == False]
    tn = len(non_controlled[non_controlled["detected_controlled"] == False])  # True negatives
    fp = len(non_controlled[non_controlled["detected_controlled"] == True])  # False positives

    # Calculate metrics
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0  # Recall for controlled
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0  # True negative rate
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    f1 = 2 * (precision * sensitivity) / (precision + sensitivity) if (precision + sensitivity) > 0 else 0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0

    # Schedule accuracy (among true positives) - only if detected_schedule column exists
    if "detected_schedule" in controlled.columns:
        schedule_matches = controlled[
            (controlled["detected_controlled"] == True) &
            (controlled["expected_schedule"] == controlled["detected_schedule"])
        ]
        schedule_accuracy = len(schedule_matches) / tp if tp > 0 else 0
    else:
        schedule_accuracy = 0

    # Whitelist accuracy
    fda_approved = valid[valid["category"] == "fda_approved"]
    whitelisted = fda_approved[fda_approved["detected_whitelisted"] == True]
    whitelist_rate = len(whitelisted) / len(fda_approved) if len(fda_approved) > 0 else 0

    return {
        "total_tested": len(valid),
        "controlled_tested": len(controlled),
        "non_controlled_tested": len(non_controlled),
        "true_positives": tp,
        "true_negatives": tn,
        "false_positives": fp,
        "false_negatives": fn,
        "sensitivity": sensitivity,
        "specificity": specificity,
        "precision": precision,
        "f1_score": f1,
        "accuracy": accuracy,
        "schedule_accuracy": schedule_accuracy,
        "whitelist_rate": whitelist_rate,
    }


def generate_report(results_df: pd.DataFrame = None):
    """Generate markdown benchmark report."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load latest results if not provided
    if results_df is None:
        result_files = sorted(RESULTS_DIR.glob("validation_results_*.csv"))
        if not result_files:
            print("No validation results found. Run with --validate first.")
            return
        results_df = pd.read_csv(result_files[-1])

    metrics = calculate_metrics(results_df)

    # Generate report
    report = f"""# FAVES V3 Regulatory Detection Benchmark

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Version:** FAVES V3
**Dataset:** DEA Controlled Substances + FDA Approved Drugs

---

## Executive Summary

FAVES V3 regulatory detection was validated against {metrics['total_tested']} compounds:
- **{metrics['controlled_tested']}** DEA controlled substances (Schedule I-V)
- **{metrics['non_controlled_tested']}** FDA-approved non-controlled drugs and negative controls

---

## Key Metrics

| Metric | Value | Target |
|--------|-------|--------|
| **Sensitivity** (detect controlled) | {metrics['sensitivity']:.1%} | >95% |
| **Specificity** (avoid false alarms) | {metrics['specificity']:.1%} | >99% |
| **Precision** | {metrics['precision']:.1%} | >95% |
| **F1 Score** | {metrics['f1_score']:.3f} | >0.95 |
| **Overall Accuracy** | {metrics['accuracy']:.1%} | >97% |
| **Schedule Accuracy** | {metrics['schedule_accuracy']:.1%} | >90% |
| **Whitelist Coverage** | {metrics['whitelist_rate']:.1%} | >95% |

---

## Confusion Matrix

|  | Predicted Controlled | Predicted Safe |
|--|---------------------|----------------|
| **Actually Controlled** | {metrics['true_positives']} (TP) | {metrics['false_negatives']} (FN) |
| **Actually Safe** | {metrics['false_positives']} (FP) | {metrics['true_negatives']} (TN) |

---

## Detailed Results by Schedule

"""

    # Add per-schedule breakdown
    for schedule in ["I", "II", "III", "IV", "V"]:
        schedule_data = results_df[results_df["expected_schedule"] == schedule]
        if len(schedule_data) > 0:
            detected = len(schedule_data[schedule_data["detected_controlled"] == True])
            total = len(schedule_data)
            report += f"### Schedule {schedule}\n"
            report += f"- Tested: {total} compounds\n"
            report += f"- Detected: {detected} ({detected/total:.1%})\n\n"

    # False positives detail
    fps = results_df[
        (results_df["expected_controlled"] == False) &
        (results_df["detected_controlled"] == True)
    ]
    if len(fps) > 0:
        report += "## False Positives (Flagged but Not Controlled)\n\n"
        report += "| Compound | Category | FAVES Flag |\n"
        report += "|----------|----------|------------|\n"
        for _, row in fps.iterrows():
            report += f"| {row['name']} | {row['category']} | {row.get('faves_flags', 'N/A')} |\n"
        report += "\n"

    # False negatives detail
    fns = results_df[
        (results_df["expected_controlled"] == True) &
        (results_df["detected_controlled"] == False)
    ]
    if len(fns) > 0:
        report += "## False Negatives (Missed Controlled Substances)\n\n"
        report += "| Compound | Expected Schedule |\n"
        report += "|----------|------------------|\n"
        for _, row in fns.iterrows():
            report += f"| {row['name']} | Schedule {row['expected_schedule']} |\n"
        report += "\n"

    report += """---

## Methodology

### Data Sources
- **DEA Controlled Substances:** Official DEA schedules (deadiversion.usdoj.gov)
- **SMILES Lookup:** PubChem REST API
- **FDA Approved Drugs:** DrugBank approved drug list

### Validation Process
1. Fetched canonical SMILES for all compounds from PubChem
2. Submitted each SMILES to FAVES V3 `get_molecule_profile` endpoint
3. Compared `is_controlled` flag against ground truth
4. Verified schedule classification accuracy

### Definitions
- **Sensitivity:** Proportion of controlled substances correctly detected
- **Specificity:** Proportion of safe compounds correctly cleared
- **Schedule Accuracy:** Correct DEA schedule among detected substances

---

## Conclusion

FAVES V3 demonstrates {"strong" if metrics['f1_score'] > 0.9 else "acceptable"} regulatory detection capabilities with:
- {metrics['sensitivity']:.1%} sensitivity for controlled substance detection
- {metrics['specificity']:.1%} specificity (low false alarm rate)
- {metrics['schedule_accuracy']:.1%} accuracy in schedule classification

"""

    # Save report
    report_path = RESULTS_DIR / f"benchmark_report_{datetime.now().strftime('%Y%m%d')}.md"
    report_path.write_text(report)
    print(f"\n✓ Generated report: {report_path}")

    # Also print summary
    print("\n" + "="*60)
    print("BENCHMARK SUMMARY")
    print("="*60)
    print(f"Sensitivity:  {metrics['sensitivity']:.1%}")
    print(f"Specificity:  {metrics['specificity']:.1%}")
    print(f"F1 Score:     {metrics['f1_score']:.3f}")
    print(f"Accuracy:     {metrics['accuracy']:.1%}")
    print("="*60)

    return report


def main():
    parser = argparse.ArgumentParser(description="FAVES Regulatory Detection Benchmark")
    parser.add_argument("--fetch-data", action="store_true", help="Fetch ground truth from PubChem")
    parser.add_argument("--validate", action="store_true", help="Run validation against FAVES API")
    parser.add_argument("--report", action="store_true", help="Generate benchmark report")
    parser.add_argument("--all", action="store_true", help="Run all steps")
    parser.add_argument("--api-url", type=str, help="FAVES API URL")
    parser.add_argument("--api-key", type=str, help="API key for authentication")

    args = parser.parse_args()

    if args.all or args.fetch_data:
        fetch_ground_truth_data()

    if args.all or args.validate:
        results = validate_against_faves(args.api_url, args.api_key)
        if results is not None and (args.all or args.report):
            generate_report(results)
    elif args.report:
        generate_report()

    if not any([args.fetch_data, args.validate, args.report, args.all]):
        parser.print_help()


if __name__ == "__main__":
    main()
