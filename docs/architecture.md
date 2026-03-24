# ROBOT Architecture

ROBOT (Research Object Builder for Open Toxicology) is designed as a modular system for creating, validating, packaging, and depositing FAIR toxicology model metadata as RO-Crates.

The architecture separates responsibilities into clear layers to support maintainability and future extensibility.

- - -

## System Overview

```

User
 │
 │ Browser
 ▼
Frontend (Static UI)
 │
 ▼
FastAPI Backend
 │
 ├── Draft lifecycle management
 ├── Metadata validation
 ├── RO-Crate builder
 ├── Deposition integrations
 │
 ▼
Local Storage
 │
 ├── drafts
 ├── crates
 └── logs
```

- - -

## Core Components

### 1\. Frontend UI

The frontend is a lightweight interface built using static HTML, CSS, and JavaScript. It interacts with the backend through REST APIs.

Responsibilities:

*   metadata entry
*   draft management
*   validation triggering
*   crate building
*   deposition management
*   activity visualization

UI entry points:

*   `/ui` – dashboard
*   `/ui/pbpk` – PBPK metadata editor

- - -

### 2\. Backend API

The backend is implemented using **FastAPI**.

It provides REST endpoints used by the UI and handles all application logic.

Major API groups:

*   Draft lifecycle APIs
*   Validation APIs
*   Build APIs
*   Deposition APIs
*   Activity APIs

- - -

### 3\. Draft Lifecycle Manager

The draft lifecycle manager controls the state of metadata drafts.

Typical states include:

*   draft
*   validated
*   built
*   archived

Supported operations:

*   Create draft
*   Edit draft
*   Validate draft
*   Build crate
*   Duplicate draft
*   Archive draft
*   Delete draft
*   Restore draft

- - -

### 4\. Metadata Validation

Validation ensures metadata consistency before a crate can be built.

Validation includes:

*   JSON schema validation
*   field completeness checks
*   consistency rules

Validation results are returned as:

*   errors
*   warnings

- - -

### 5\. RO-Crate Builder

The crate builder converts validated metadata into a structured **RO-Crate**.

Generated contents typically include:

*   metadata JSON-LD
*   model description
*   provenance metadata
*   supporting files

Crates are stored locally and can be downloaded as ZIP archives.

- - -

### 6\. Deposition Integrations

ROBOT integrates with external repositories to publish crates.

Currently implemented:

*   Zenodo Sandbox
*   Zenodo Production

Future integrations may include:

*   BioModels
*   WorkflowHub
*   domain-specific toxicology repositories

- - -

## Storage Layout

```

var/
 ├── drafts/
 ├── crates/
 └── logs/
```

This simple filesystem storage approach is used during early development.

Future versions may use database-backed storage.

- - -

## Design Principles

*   Modular architecture
*   Clear separation of concerns
*   FAIR-by-design metadata workflows
*   Extensible deposition system
*   Simple deployability