# Reproducibility instructions (v1 example)

## Contents
- SBML model: `model/model.xml`
- Parameter table: `data/parameters.csv`
- Metadata: `ro-crate-metadata.json`

## How to reproduce (template)
1. Open `model/model.xml` in an SBML-compatible tool (e.g., COPASI or tellurium).
2. Confirm compartments exist (Blood, Liver).
3. Use `data/parameters.csv` to populate parameter values in your simulator.
4. Run a simple simulation (this example is a scaffold; kinetics are not fully specified).
5. Use the evaluation narrative in the metadata to understand limitations.

## Notes
This is a minimal example crate intended to demonstrate metadata structure and packaging.
