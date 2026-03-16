<h1>ROBOT</h1>

<p><strong>Research Object Builder for Open Toxicology</strong></p>

<p>
ROBOT is a web-based application for creating, validating, building, and depositing
<strong>FAIR toxicology model metadata</strong> as <strong>RO-Crates</strong>.
</p>

<p>
The system currently focuses on <strong>PBPK models</strong> and provides a practical workflow for:
</p>

<ul>
  <li>entering structured model metadata</li>
  <li>validating metadata against a schema</li>
  <li>generating RO-Crates</li>
  <li>downloading built crates</li>
  <li>depositing crates to Zenodo</li>
  <li>tracking draft, build, and deposition history</li>
</ul>

<p>
ROBOT is being developed as part of a broader effort to make
<strong>toxicological models FAIR (Findable, Accessible, Interoperable, Reusable)</strong>
and easier to share within the open science ecosystem.
</p>

<hr>

<h2>Why ROBOT?</h2>

<p>
Toxicology models are often difficult to:
</p>

<ul>
  <li>discover</li>
  <li>interpret</li>
  <li>validate</li>
  <li>reuse</li>
</ul>

<p>
because metadata is incomplete, inconsistent, or not packaged in machine-readable formats.
</p>

<p>ROBOT addresses this by combining:</p>

<ul>
  <li>structured metadata entry</li>
  <li>schema-based validation</li>
  <li>RO-Crate packaging</li>
  <li>repository deposition workflows</li>
  <li>future AI-assisted metadata generation</li>
</ul>

<p>
The goal is to support <strong>transparent, reproducible, and reusable toxicology model sharing</strong>.
</p>

<hr>

<h2>Current Features</h2>

<h3>Metadata Editor</h3>

<p>
ROBOT provides a structured UI for entering model metadata without manually editing JSON.
</p>

<p>Currently implemented:</p>

<ul>
  <li>PBPK metadata editor</li>
  <li>automatic draft creation</li>
  <li>JSON metadata import</li>
  <li>form-based editing</li>
</ul>

<h3>Draft Workflow</h3>

<p>Users can manage metadata drafts:</p>

<ul>
  <li>create draft</li>
  <li>edit draft</li>
  <li>validate metadata</li>
  <li>build RO-Crate</li>
  <li>duplicate draft</li>
  <li>archive draft</li>
  <li>delete draft</li>
  <li>restore draft from history</li>
</ul>

<p>Draft activity is recorded for traceability.</p>

<h3>Validation</h3>

<p>Metadata is validated against:</p>

<ul>
  <li>JSON schema constraints</li>
  <li>project-specific consistency checks</li>
</ul>

<p>Validation produces:</p>

<ul>
  <li><strong>errors</strong> (blocking)</li>
  <li><strong>warnings</strong> (non-blocking)</li>
</ul>

<h3>RO-Crate Generation</h3>

<p>
Validated drafts can be converted into a structured <strong>RO-Crate</strong> containing:
</p>

<ul>
  <li>metadata</li>
  <li>provenance information</li>
  <li>model description</li>
  <li>supporting metadata</li>
</ul>

<p>Users can download the generated crate as a ZIP archive.</p>

<h3>Deposition</h3>

<p>Built crates can be deposited to <strong>Zenodo</strong>.</p>

<p>Supported workflows:</p>

<ul>
  <li>Zenodo Sandbox deposition</li>
  <li>Zenodo production deposition</li>
  <li>draft creation</li>
  <li>record publishing</li>
</ul>

<p>Deposition history is stored and visible in the UI.</p>

<h3>Dashboard</h3>

<p>The landing page provides:</p>

<ul>
  <li>model type selection</li>
  <li>collapsible <strong>Recent Drafts</strong></li>
  <li>collapsible <strong>Recent Deposits</strong></li>
  <li>quick access to ongoing work</li>
</ul>

<hr>

<h2>Repository Structure</h2>

<pre><code>.
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
</code></pre>

<hr>

<h2>Implemented Model Types</h2>

<table>
  <thead>
    <tr>
      <th>Model Type</th>
      <th>Status</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>PBPK</td>
      <td>Implemented</td>
    </tr>
    <tr>
      <td>QSAR</td>
      <td>Planned</td>
    </tr>
    <tr>
      <td>qAOP</td>
      <td>Planned</td>
    </tr>
    <tr>
      <td>NAM</td>
      <td>Planned</td>
    </tr>
  </tbody>
</table>

<hr>

<h2>Local Development</h2>

<h3>Requirements</h3>

<ul>
  <li>Python 3.11+</li>
  <li><code>uv</code> (recommended) or <code>pip</code></li>
  <li>Git</li>
</ul>

<h3>Clone the Repository</h3>

<pre><code>git clone https://github.com/&lt;your-org&gt;/robot.git
cd robot
</code></pre>

<h3>Create Environment</h3>

<p>Using <strong>uv</strong> (recommended):</p>

<pre><code>uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
</code></pre>

<p>Or with pip:</p>

<pre><code>python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
</code></pre>

<h3>Run the Backend</h3>

<p>Start the server:</p>

<pre><code>PYTHONPATH=packages uvicorn pbpk_backend.app:app --reload
</code></pre>

<p>The application will start at:</p>

<pre><code>http://127.0.0.1:8000
</code></pre>

<h3>Access the UI</h3>

<p>Landing page:</p>

<pre><code>http://127.0.0.1:8000/ui
</code></pre>

<p>PBPK metadata editor:</p>

<pre><code>http://127.0.0.1:8000/ui/pbpk
</code></pre>

<hr>

<h2>Example Workflow</h2>

<ol>
  <li>Open the landing page (<code>/ui</code>)</li>
  <li>Select <strong>PBPK</strong></li>
  <li>Enter metadata or load example metadata</li>
  <li>Create a draft</li>
  <li>Validate the metadata</li>
  <li>Build the RO-Crate</li>
  <li>Download the crate</li>
  <li>Deposit the crate to Zenodo</li>
  <li>Review activity and deposition history</li>
</ol>

<hr>

<h2>Documentation</h2>

<p>Detailed documentation is available in the <code>docs</code> directory.</p>

<table>
  <thead>
    <tr>
      <th>Document</th>
      <th>Description</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>docs/architechture.md</code></td>
      <td>System architecture</td>
    </tr>
    <tr>
      <td><code>docs/governence.md</code></td>
      <td>Governance and project principles</td>
    </tr>
    <tr>
      <td><code>docs/roadmap.md</code></td>
      <td>Development roadmap</td>
    </tr>
  </tbody>
</table>

<hr>

<h2>Current Limitations</h2>

<p>ROBOT is currently a <strong>version one prototype</strong>.</p>

<p>Known limitations:</p>

<ul>
  <li>only <strong>PBPK models</strong> are currently supported</li>
  <li>frontend is static HTML and JavaScript</li>
  <li>filesystem storage is used instead of a database</li>
  <li>authentication and user accounts are not implemented</li>
  <li>multi-user concurrency is not yet handled</li>
  <li>deployment and operational hardening are ongoing</li>
</ul>

<p>These limitations will be addressed in future releases.</p>

<hr>

<h2>Vision</h2>

<p>
ROBOT aims to become a platform for preparing <strong>FAIR research objects for toxicology models</strong>.
</p>

<p>Long-term goals include:</p>

<ul>
  <li>support for multiple model classes</li>
  <li>metadata harmonization across toxicology domains</li>
  <li>automated metadata extraction</li>
  <li>AI-assisted metadata completion</li>
  <li>improved repository integrations</li>
  <li>reproducible model sharing workflows</li>
</ul>

<p>
The broader objective is to improve <strong>model transparency, discoverability, and reuse</strong>
in computational toxicology.
</p>

<hr>

<h2>Citation and Attribution</h2>

<p>
If you use ROBOT in your research, please cite this repository.
</p>

<p>
GitHub provides a ready-to-use citation via the
<strong>"Cite this repository"</strong> button.
</p>

<p>
Citation metadata is defined in the <code>CITATION.cff</code> file.
</p>

<hr>

<h2>License</h2>

<p>
This project is released under the <strong>MIT License</strong>.
</p>

<p>
See the <code>LICENSE</code> file for details.
</p>