# Tan et al. (2020) PBPK Reporting Template → JSON-LD / RO-Crate Mapping (v1)

This document defines the authoritative mapping between the PBPK reporting
requirements extracted from Tan et al. (2020) (`tan2020.yaml`) and their
representation in a RO-Crate–native JSON-LD graph.

Version: 1.0  
Mapping style: **entity-per-node**  
Authorship model: **dataset-only**

The mapping is implemented using:
- RO-Crate 1.1 context
- schema.org as the default vocabulary
- a minimal PBPK extension namespace (`pbpk:`)

---

## Node conventions

| Concept | Node ID pattern |
|------|----------------|
| RO-Crate root | `./` |
| PBPK model | `#pbpk-model` |
| Person | `#person-n` |
| Organization | `#org-n` |
| Biological system | `#biosys-n` |
| Chemical | `#chem-n` |
| Chemical identifier | `#chem-n-id-m` |
| Parameter | `#param-n` |
| Calibration activity | `#calibration-n` |
| Evaluation activity | `#evaluation-n` |
| SUV analysis | `#suv-n` |
| File artifact | crate-relative path (e.g. `model/model.xml`) |

---

## Section 1 — General Model Information

| Step 1 field ID | JSON-LD node | JSON-LD property | Required | Cardinality | Notes |
|---|---|---|---:|---|---|
| model_name | `#pbpk-model` | `name` | ✅ | one | Human-readable model title. |
| model_version | `#pbpk-model` | `version` | ✅ | one | Version string. |
| model_description | `#pbpk-model` | `description` | ✅ | one | Narrative scope and purpose. |
| model_authors | `./` | `creator` | ✅ | many | Dataset-level authorship only (v1). |
| affiliations | `#org-n` | `name`, `address`, `location` | ⛔ | many | Linked from `Person.affiliation`. |
| software_platform | `#pbpk-model` | `programmingLanguage` | ✅ | one/many | SBML, Python, R, etc. |
| software_version | `#pbpk-model` | `softwareVersion` | ⛔ | one | Optional in v1. |
| model_availability | `#pbpk-model` | `codeRepository` | ✅ | many | URLs or DOIs. |
| license | `./` | `license` | ✅ | one | Applies to crate contents. |
| intended_application_category | `#pbpk-model` | `applicationCategory` | ✅ | one | High-level classification. |
| limitations_summary | `#pbpk-model` | `pbpk:limitationsSummary` | ⛔ | one | Short summary; detailed limits in Section 9. |

---

## Section 2 — Biological System Description

| Step 1 field ID | JSON-LD node | JSON-LD property | Required | Cardinality | Notes |
|---|---|---|---:|---|---|
| biological_systems | `#pbpk-model` → `#biosys-n` | `pbpk:hasBiologicalSystem` | ✅ | many | Each species/context is a node. |
| species | `#biosys-n` | `pbpk:species` | ✅ | one | String in v1; later taxonomy URI. |
| life_stages | `#biosys-n` | `pbpk:lifeStage` | ✅ | many | Adult, neonate, pregnant, etc. |
| population_description | `#biosys-n` | `description` | ⛔ | one | Free text. |
| physiological_scope | `#biosys-n` | `pbpk:physiologicalScope` | ✅ | one | Narrative description. |
| compartments | `#biosys-n` | `pbpk:compartments` | ✅ | many | Controlled-term-like strings. |
| anatomical_assumptions | `#biosys-n` | `pbpk:anatomicalAssumptions` | ⛔ | one | Free text. |

---

## Section 3 — Chemical(s) Description

| Step 1 field ID | JSON-LD node | JSON-LD property | Required | Cardinality | Notes |
|---|---|---|---:|---|---|
| chemicals | `#pbpk-model` → `#chem-n` | `pbpk:hasChemical` | ✅ | many | Multi-chemical supported. |
| chemical_name | `#chem-n` | `name` | ✅ | one | Human-readable name. |
| chemical_role | `#chem-n` | `pbpk:chemicalRole` | ✅ | one | Parent, metabolite, co-exposure. |
| chemical_identifiers | `#chem-n` → `#chem-n-id-m` | `identifier` | ✅ | many | Each as `PropertyValue`. |
| identifier_type | `#chem-n-id-m` | `name` | ✅ | one | CAS RN, InChI, SMILES, etc. |
| identifier_value | `#chem-n-id-m` | `value` | ✅ | one | Identifier string. |
| molecular_weight | `#chem-n` | `molecularWeight` | ⛔ | one | `QuantitativeValue`. |
| physicochemical_notes | `#chem-n` | `description` | ⛔ | one | Qualitative notes. |

---

## Section 4 — Model Structure and Mathematical Representation

| Step 1 field ID | JSON-LD node | JSON-LD property | Required | Cardinality | Notes |
|---|---|---|---:|---|---|
| model_structure_description | `#pbpk-model` | `pbpk:modelStructureDescription` | ✅ | one | Narrative structural overview. |
| structural_compartments | `#pbpk-model` | `pbpk:structuralCompartments` | ✅ | many | Embedded objects acceptable in v1. |
| compartment_name | compartment object | `name` | ✅ | one | Matches code identifiers. |
| biological_reference | compartment object | `pbpk:biologicalReference` | ✅ | one | Tissue/organ reference. |
| compartment_description | compartment object | `description` | ⛔ | one | Free text. |
| inter_compartmental_connections | `#pbpk-model` | `pbpk:connections` | ✅ | many | Source → target relations. |
| source_compartment | connection object | `pbpk:sourceCompartment` | ✅ | one | String reference. |
| target_compartment | connection object | `pbpk:targetCompartment` | ✅ | one | String reference. |
| connection_type | connection object | `pbpk:connectionType` | ✅ | one | Blood flow, diffusion, etc. |
| mathematical_representation | `#pbpk-model` | `pbpk:mathematicalRepresentation` | ✅ | one | ODE / algebraic / hybrid. |
| model_implementation_reference | `#pbpk-model` → `File` | `hasPart` | ✅ | many | References implementation files. |

---

## Section 5 — Parameterisation

| Step 1 field ID | JSON-LD node | JSON-LD property | Required | Cardinality | Notes |
|---|---|---|---:|---|---|
| parameters | `#pbpk-model` → `#param-n` | `pbpk:hasParameter` | ✅ | many | Each parameter is a node. |
| parameter_name | `#param-n` | `name` | ✅ | one | Code-level identifier. |
| parameter_category | `#param-n` | `category` | ✅ | one | Physiological, biochemical, etc. |
| parameter_value | `#param-n` | `value` | ✅ | one | Numeric. |
| parameter_unit | `#param-n` | `unitText` | ✅ | one | String in v1. |
| parameter_scope | `#param-n` | `pbpk:scope` | ✅ | one | Global/species/etc. |
| applicable_species | `#param-n` | `pbpk:appliesToSpecies` | ⛔ | many | Match `#biosys-n.species`. |
| applicable_compartments | `#param-n` | `pbpk:appliesToCompartments` | ⛔ | many | Match biosys compartments. |
| applicable_chemicals | `#param-n` | `pbpk:appliesToChemicals` | ⛔ | many | Match chemical names. |
| parameter_source | `#param-n` | `pbpk:parameterSource` | ✅ | one | Literature/experimental/etc. |
| source_reference | `#param-n` | `citation` | ⛔ | one | DOI, PMID, or citation text. |
| parameter_notes | `#param-n` | `description` | ⛔ | one | Assumptions or notes. |

---

## Section 6 — Calibration and Parameter Estimation (optional)

| Step 1 field ID | JSON-LD node | JSON-LD property | Required | Cardinality | Notes |
|---|---|---|---:|---|---|
| calibration_activities | `#pbpk-model` → `#calibration-n` | `pbpk:hasCalibration` | ⛔ | many | Optional activities. |
| calibration_description | `#calibration-n` | `description` | ✅ | one | Narrative procedure. |
| calibration_method | `#calibration-n` | `pbpk:method` | ✅ | one | Manual, LSQ, Bayesian. |
| calibration_data | `#calibration-n` | `pbpk:calibrationData` | ⛔ | one | Text or File reference. |
| calibrated_parameters | `#calibration-n` | `pbpk:calibratedParameters` | ⛔ | many | Names of parameters. |
| optimization_criteria | `#calibration-n` | `pbpk:optimizationCriteria` | ⛔ | one | Goodness-of-fit criteria. |
| calibration_notes | `#calibration-n` | `pbpk:notes` | ⛔ | one | Additional notes. |

---

## Section 7 — Model Evaluation and Validation

| Step 1 field ID | JSON-LD node | JSON-LD property | Required | Cardinality | Notes |
|---|---|---|---:|---|---|
| evaluation_activities | `#pbpk-model` → `#evaluation-n` | `pbpk:hasEvaluation` | ✅ | many | At least one required. |
| evaluation_description | `#evaluation-n` | `description` | ✅ | one | Narrative. |
| evaluation_data | `#evaluation-n` | `pbpk:evaluationData` | ⛔ | one | Text or File reference. |
| evaluation_method | `#evaluation-n` | `pbpk:method` | ✅ | one | Visual/statistical/etc. |
| performance_metrics | `#evaluation-n` | `pbpk:performanceMetrics` | ⛔ | many | Embedded metric objects. |
| metric_name | metric object | `name` | ✅ | one | RMSE, R², etc. |
| metric_value | metric object | `value` | ⛔ | one | String or number. |
| metric_interpretation | metric object | `description` | ⛔ | one | Interpretation. |
| evaluation_outcome | `#evaluation-n` | `pbpk:outcome` | ✅ | one | Summary implication. |
| evaluation_limitations | `#evaluation-n` | `pbpk:limitations` | ⛔ | one | Evaluation-specific limits. |

---

## Section 8 — Sensitivity, Uncertainty, and Variability Analyses (optional)

| Step 1 field ID | JSON-LD node | JSON-LD property | Required | Cardinality | Notes |
|---|---|---|---:|---|---|
| suv_analyses | `#pbpk-model` → `#suv-n` | `pbpk:hasSUVAnalysis` | ⛔ | many | Optional analyses. |
| analysis_type | `#suv-n` | `pbpk:analysisType` | ✅ | one | Sensitivity/uncertainty/etc. |
| analysis_method | `#suv-n` | `pbpk:method` | ⛔ | one | Monte Carlo, etc. |
| analyzed_parameters | `#suv-n` | `pbpk:analyzedParameters` | ⛔ | many | Parameter names. |
| analysis_results | `#suv-n` | `description` | ✅ | one | Summary results. |
| robustness_interpretation | `#suv-n` | `pbpk:robustnessInterpretation` | ⛔ | one | Narrative. |
| suv_notes | `#suv-n` | `pbpk:notes` | ⛔ | one | Additional notes. |

---

## Section 9 — Model Applicability, Intended Use, and Limitations

| Step 1 field ID | JSON-LD node | JSON-LD property | Required | Cardinality | Notes |
|---|---|---|---:|---|---|
| intended_use | `#pbpk-model` | `purpose` | ✅ | one | Narrative intended use. |
| applicability_domain | `#pbpk-model` | `pbpk:applicabilityDomain` | ✅ | one | Species, dose ranges, scenarios. |
| confidence_statement | `#pbpk-model` | `pbpk:confidenceStatement` | ✅ | one | Qualitative confidence. |
| known_limitations | `#pbpk-model` | `pbpk:limitations` | ✅ | one | Model-level limitations. |
| misuse_risks | `#pbpk-model` | `pbpk:misuseRisks` | ⛔ | one | Optional. |

---

## Section 10 — Electronic Files, Supporting Documents, and Reproducibility

| Step 1 field ID | JSON-LD node | JSON-LD property | Required | Cardinality | Notes |
|---|---|---|---:|---|---|
| digital_artifacts | `./` and/or `#pbpk-model` → `File` | `hasPart` | ✅ | many | Each artifact is a `File` entity. |
| artifact_name | `File` | `name` | ✅ | one | Human-readable name. |
| artifact_type | `File` | `pbpk:artifactType` | ✅ | one | Model code, parameter table, etc. |
| artifact_format | `File` | `pbpk:artifactFormat` + `encodingFormat` | ✅ | one | Prefer both if possible. |
| artifact_location | `File` | `@id` | ✅ | one | Crate-relative path. |
| artifact_description | `File` | `description` | ⛔ | one | Optional. |
| reproducibility_instructions | `File` | `pbpk:reproducibilityInstructions` | ✅ | one | Prefer dedicated documentation file. |
| documentation_practices | `#pbpk-model` | `pbpk:documentationPractices` | ⛔ | one | Optional narrative. |

---

## Notes on extensions

All `pbpk:` properties are v1 placeholders and will be:
- documented in `pbpk-context.jsonld`
- refined toward established ontologies (e.g. PROV-O, OBI) in later versions

They are intentionally lightweight and non-breaking.

---

## Mapping status

This mapping document, together with:
- `tan2020.yaml`
- `pbpk-context.jsonld`
- `pbpk-core-template.jsonld`

defines the **PBPK RO-Crate Profile v1.0**.