# ROBOT

**Research Object Builder for Open Toxicology**

![](https://img.shields.io/badge/python-3.11%2B-blue.svg) 
![](https://img.shields.io/badge/license-MIT-green.svg) 
![](https://img.shields.io/badge/status-prototype-orange) 
![](https://img.shields.io/badge/RO--Crate-supported-blueviolet) 
![](https://img.shields.io/badge/toxicology-FAIR-important)
<img src="https://github.com/abhishek-chattopadhyay/robot/actions/workflows/docker-build.yml/badge.svg" alt="Docker Build">

ROBOT is a web-based application for creating, validating, building, and depositing **FAIR toxicology model metadata** as **RO-Crates**.

The system currently focuses on **PBPK models** and provides a practical workflow for:

*   entering structured model metadata
*   validating metadata against a schema
*   generating RO-Crates
*   downloading built crates
*   depositing crates to Zenodo
*   tracking draft, build, and deposition history

ROBOT is being developed as part of a broader effort to make **toxicological models FAIR (Findable, Accessible, Interoperable, Reusable)** and easier to share within the open science ecosystem.

- - -

## Why ROBOT?

Toxicology models are often difficult to:

*   discover
*   interpret
*   validate
*   reuse

because metadata is incomplete, inconsistent, or not packaged in machine-readable formats.

ROBOT addresses this by combining:

*   structured metadata entry
*   schema-based validation
*   RO-Crate packaging
*   repository deposition workflows
*   future AI-assisted metadata generation

The goal is to support **transparent, reproducible, and reusable toxicology model sharing**.

- - -

## Current Features

### Metadata Editor

ROBOT provides a structured UI for entering model metadata without manually editing JSON.

Currently implemented:

*   PBPK metadata editor
*   automatic draft creation
*   JSON metadata import
*   form-based editing

### Draft Workflow

Users can manage metadata drafts:

*   create draft
*   edit draft
*   validate metadata
*   build RO-Crate
*   duplicate draft
*   archive draft
*   delete draft
*   restore draft from history

Draft activity is recorded for traceability.

### Validation

Metadata is validated against:

*   JSON schema constraints
*   project-specific consistency checks

Validation produces:

*   **errors** (blocking)
*   **warnings** (non-blocking)

### RO-Crate Generation

Validated drafts can be converted into a structured **RO-Crate** containing:

*   metadata
*   provenance information
*   model description
*   supporting metadata

Users can download the generated crate as a ZIP archive.

### Deposition

Built crates can be deposited to **Zenodo**.

Supported workflows:

*   Zenodo Sandbox deposition
*   Zenodo production deposition
*   draft creation
*   record publishing

Deposition history is stored and visible in the UI.

### Dashboard

The landing page provides:

*   model type selection
*   collapsible **Recent Drafts**
*   collapsible **Recent Deposits**
*   quick access to ongoing work

- - -

## Repository Structure

```
.
├── docs/
│   ├── architechture.md
│   ├── governence.md
│   └── roadmap.md
│
├── packages/
│   ├── pbpk_backend/
│   ├── pbpk_deposition/
│   ├── pbpk_validation/
│   └── ...
│
├── var/
│   ├── drafts/
│   ├── crates/
│   └── logs/
│
└── README.md
```

- - -

## Implemented Model Types

| Model Type | Status |
| --- | --- |
| PBPK | Implemented |
| QSAR | Planned |
| qAOP | Planned |
| NAM | Planned |

- - -

## Local Development

### Requirements

*   Python 3.11+
*   `uv` (recommended) or `pip`
*   Git

### Clone the Repository

```
git clone https://github.com/<your-org>/robot.git
cd robot
```

### Create Environment

Using **uv** (recommended):

```
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Or with pip:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run the Backend

Start the server:

```
PYTHONPATH=packages uvicorn pbpk_backend.app:app --reload
```

### Run with Docker

Build and start ROBOT with Docker Compose:

```
docker compose build
docker compose up
```

The application will start at:

```
http://127.0.0.1:8000/ui
```

### Access the UI

PBPK metadata editor:

```
http://127.0.0.1:8000/ui/pbpk
```

- - -

## Example Workflow

1.  Open the landing page (`/ui`)
2.  Select **PBPK**
3.  Enter metadata or load example metadata
4.  Create a draft
5.  Validate the metadata
6.  Build the RO-Crate
7.  Download the crate
8.  Deposit the crate to Zenodo
9.  Review activity and deposition history

- - -

## Documentation

Detailed documentation is available in the `docs` directory.

| Document | Description |
| --- | --- |
| `docs/architechture.md` | System architecture |
| `docs/governence.md` | Governance and project principles |
| `docs/roadmap.md` | Development roadmap |

- - -

## Current Limitations

ROBOT is currently a **version one prototype**.

Known limitations:

*   only **PBPK models** are currently supported
*   frontend is static HTML and JavaScript
*   filesystem storage is used instead of a database
*   authentication and user accounts are not implemented
*   multi-user concurrency is not yet handled
*   deployment and operational hardening are ongoing

These limitations will be addressed in future releases.

- - -

## Vision

ROBOT aims to become a platform for preparing **FAIR research objects for toxicology models**.

Long-term goals include:

*   support for multiple model classes
*   metadata harmonization across toxicology domains
*   automated metadata extraction
*   AI-assisted metadata completion
*   improved repository integrations
*   reproducible model sharing workflows

The broader objective is to improve **model transparency, discoverability, and reuse** in computational toxicology.

- - -

## Citation and Attribution

If you use ROBOT in your research, please cite this repository.

GitHub provides a ready-to-use citation via the **"Cite this repository"** button.

Citation metadata is defined in the `CITATION.cff` file.

- - -

## License

This project is released under the **MIT License**.

See the `LICENSE` file for details.