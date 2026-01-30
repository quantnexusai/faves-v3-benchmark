# FAVES V3 Regulatory Detection Benchmark

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18357496.svg)](https://doi.org/10.5281/zenodo.18357496)

Validation benchmark for FAVES V3, a three-tier regulatory compliance detection system for identifying DEA-controlled substances in molecular databases.

## Overview

This repository contains the benchmark dataset and validation scripts used to evaluate FAVES V3 performance, as described in:

> Harrison, A. (2026). FAVES V3: A Three-Tier Regulatory Compliance Detection System for Molecular Databases. *ChemRxiv*. DOI: [10.26434/chemrxiv.10001641](https://doi.org/10.26434/chemrxiv.10001641)

## Dataset

The benchmark comprises **102 compounds**:

| Category | Count | Description |
|----------|-------|-------------|
| Schedule I | 9 | Heroin, LSD, MDMA, psilocybin, etc. |
| Schedule II | 18 | Fentanyl, oxycodone, cocaine, amphetamine, etc. |
| Schedule III | 6 | Ketamine, buprenorphine, testosterone, etc. |
| Schedule IV | 11 | Alprazolam, diazepam, zolpidem, etc. |
| Schedule V | 3 | Pregabalin, lacosamide, brivaracetam |
| Non-controlled | 55 | FDA-approved therapeutics and negative controls |

## Files

```
├── data/
│   ├── ground_truth.csv          # Benchmark compounds with regulatory status
│   └── scaffold_patterns.csv     # 37 SMARTS patterns for scaffold detection
├── results/
│   └── validation_results.csv    # FAVES V3 predictions vs ground truth
├── scripts/
│   └── faves_benchmark.py        # Validation script
└── README.md
```

### Scaffold Patterns

The `scaffold_patterns.csv` file contains 37 SMARTS patterns used for Tier 3 scaffold-based detection:

| Category | Count |
|----------|-------|
| Opioid | 8 |
| Benzodiazepine | 6 |
| Stimulant | 7 |
| Cannabinoid | 6 |
| Hypnotic/Sedative | 5 |
| Dissociative/Hallucinogen | 5 |

## Results

FAVES V3 achieved perfect classification on this benchmark:

| Metric | Value | 95% CI |
|--------|-------|--------|
| Sensitivity | 100.0% | [92.5%, 100.0%] |
| Specificity | 100.0% | [93.5%, 100.0%] |
| Precision | 100.0% | [92.5%, 100.0%] |
| F1 Score | 1.000 | — |
| Accuracy | 100.0% | [96.5%, 100.0%] |

*Confidence intervals calculated using the Clopper-Pearson exact method.*

**Confusion Matrix:**

|  | Predicted Controlled | Predicted Safe |
|--|---------------------|----------------|
| Actually Controlled | 47 (TP) | 0 (FN) |
| Actually Safe | 0 (FP) | 55 (TN) |

## Usage

### Running the benchmark

```bash
# Install dependencies
pip install pandas requests rdkit

# Fetch SMILES from PubChem (optional - data already included)
python scripts/faves_benchmark.py --fetch-data

# Run validation against FAVES API
python scripts/faves_benchmark.py --validate --api-url https://ai.novomcp.com

# Generate report
python scripts/faves_benchmark.py --report
```

### API Access

FAVES V3 is accessible via REST API at https://ai.novomcp.com. A free tier is available for evaluation.

## Data Sources

- **DEA Controlled Substances:** [DEA Drug Scheduling](https://www.dea.gov/drug-information/drug-scheduling)
- **SMILES Structures:** [PubChem](https://pubchem.ncbi.nlm.nih.gov/)
- **FDA Approved Drugs:** [DrugBank](https://go.drugbank.com/)

## Citation

If you use this benchmark, please cite:

```bibtex
@article{harrison2026faves,
  title={FAVES V3: A Three-Tier Regulatory Compliance Detection System for Molecular Databases},
  author={Harrison, Ari},
  journal={ChemRxiv},
  year={2026},
  doi={10.26434/chemrxiv.10001641}
}
```

For the benchmark dataset specifically:
```bibtex
@dataset{harrison2026faves_benchmark,
  title={FAVES V3 Regulatory Detection Benchmark},
  author={Harrison, Ari},
  year={2026},
  publisher={Zenodo},
  doi={10.5281/zenodo.18357496}
}
```

## License

This dataset is released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Author

**Ari Harrison**
NovoQuant Nexus
ORCID: [0009-0006-5836-7528](https://orcid.org/0009-0006-5836-7528)
