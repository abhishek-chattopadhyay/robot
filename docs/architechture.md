<h1>ROBOT Architecture</h1>

<p>
ROBOT (Research Object Builder for Open Toxicology) is designed as a modular system
for creating, validating, packaging, and depositing FAIR toxicology model metadata
as RO-Crates.
</p>

<p>
The architecture separates responsibilities into clear layers to support
maintainability and future extensibility.
</p>

<hr>

<h2>System Overview</h2>

<pre><code>
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
</code></pre>

<hr>

<h2>Core Components</h2>

<h3>1. Frontend UI</h3>

<p>
The frontend is a lightweight interface built using static HTML, CSS, and JavaScript.
It interacts with the backend through REST APIs.
</p>

<p>Responsibilities:</p>

<ul>
<li>metadata entry</li>
<li>draft management</li>
<li>validation triggering</li>
<li>crate building</li>
<li>deposition management</li>
<li>activity visualization</li>
</ul>

<p>UI entry points:</p>

<ul>
<li><code>/ui</code> – dashboard</li>
<li><code>/ui/pbpk</code> – PBPK metadata editor</li>
</ul>

<hr>

<h3>2. Backend API</h3>

<p>
The backend is implemented using <strong>FastAPI</strong>.
</p>

<p>
It provides REST endpoints used by the UI and handles
all application logic.
</p>

<p>Major API groups:</p>

<ul>
<li>Draft lifecycle APIs</li>
<li>Validation APIs</li>
<li>Build APIs</li>
<li>Deposition APIs</li>
<li>Activity APIs</li>
</ul>

<hr>

<h3>3. Draft Lifecycle Manager</h3>

<p>
The draft lifecycle manager controls the state of metadata drafts.
</p>

<p>Typical states include:</p>

<ul>
<li>draft</li>
<li>validated</li>
<li>built</li>
<li>archived</li>
</ul>

<p>Supported operations:</p>

<ul>
<li>Create draft</li>
<li>Edit draft</li>
<li>Validate draft</li>
<li>Build crate</li>
<li>Duplicate draft</li>
<li>Archive draft</li>
<li>Delete draft</li>
<li>Restore draft</li>
</ul>

<hr>

<h3>4. Metadata Validation</h3>

<p>
Validation ensures metadata consistency before a crate can be built.
</p>

<p>Validation includes:</p>

<ul>
<li>JSON schema validation</li>
<li>field completeness checks</li>
<li>consistency rules</li>
</ul>

<p>Validation results are returned as:</p>

<ul>
<li>errors</li>
<li>warnings</li>
</ul>

<hr>

<h3>5. RO-Crate Builder</h3>

<p>
The crate builder converts validated metadata into
a structured <strong>RO-Crate</strong>.
</p>

<p>Generated contents typically include:</p>

<ul>
<li>metadata JSON-LD</li>
<li>model description</li>
<li>provenance metadata</li>
<li>supporting files</li>
</ul>

<p>
Crates are stored locally and can be downloaded as ZIP archives.
</p>

<hr>

<h3>6. Deposition Integrations</h3>

<p>
ROBOT integrates with external repositories to publish crates.
</p>

<p>Currently implemented:</p>

<ul>
<li>Zenodo Sandbox</li>
<li>Zenodo Production</li>
</ul>

<p>Future integrations may include:</p>

<ul>
<li>BioModels</li>
<li>WorkflowHub</li>
<li>domain-specific toxicology repositories</li>
</ul>

<hr>

<h2>Storage Layout</h2>

<pre><code>
var/
 ├── drafts/
 ├── crates/
 └── logs/
</code></pre>

<p>
This simple filesystem storage approach is used during
early development.
</p>

<p>
Future versions may use database-backed storage.
</p>

<hr>

<h2>Design Principles</h2>

<ul>
<li>Modular architecture</li>
<li>Clear separation of concerns</li>
<li>FAIR-by-design metadata workflows</li>
<li>Extensible deposition system</li>
<li>Simple deployability</li>
</ul>