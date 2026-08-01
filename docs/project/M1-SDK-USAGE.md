# M1 SDK, CLI, registries, and plugin boundary

The M1 interface is a dependency-light local foundation for validating, inspecting, storing, and
projecting Generic DNC-IR graphs. It does not turn the process-local reference stores into durable
enterprise infrastructure, and it does not sandbox Python plugins.

## Command line

Installing the package creates the `dnc` command. The same interface is available as
`python -m dnc`.

```bash
dnc graph validate graph.json
dnc graph inspect graph.json
dnc graph project graph.json --output executable.json
```

Governed graphs fail admission without an execution context. Supply one with `--context`:

```json
{
  "tenant_id": "tenant-a",
  "permissions": ["provider:invoke"],
  "isolation_grade": "I3_RECORDED_EXTERNALS",
  "region": "IN",
  "device": "cpu",
  "runtime": "python",
  "capabilities": ["provider-recording"],
  "trust_zone": "enclave",
  "confidential_compute": true
}
```

```bash
dnc graph validate graph.json --context execution-context.json
dnc graph project graph.json --context execution-context.json
```

`validate` exits with status 1 for an invalid or unadmitted graph. `--structural-only` reports graph
validity without claiming execution admission. `inspect` can examine a structurally invalid graph and
includes its validation report. Command failures are emitted as JSON on standard error.

## Python SDK

`DNCSDK` is the maintained facade. It accepts a `StructuralGraph`, mapping, JSON string, or UTF-8 JSON
bytes.

```python
from pathlib import Path

from dnc import DNCSDK

sdk = DNCSDK()
payload = Path("graph.json").read_text(encoding="utf-8")

report = sdk.validate_graph(payload)
inspection = sdk.inspect_graph(payload)
projection = sdk.project_graph(payload)
```

`GraphValidationReport` distinguishes structural validity, whether a context is required, and whether
the supplied context is execution-admissible. Projection always fails closed when admission is not
satisfied.

## Artifact and graph registries

Both registries wrap `ContentAddressedObjectStore`; content references use `sha256:<digest>` and every
operation requires a tenant ID. Artifact descriptors are immutable for a given tenant and digest.
Graph registration and load both repeat schema, invariant, and execution-context admission.

```python
artifact = sdk.register_artifact(
    b"evidence",
    tenant_id="tenant-a",
    media_type="application/octet-stream",
)
graph = sdk.register_graph(payload, tenant_id="tenant-a")
restored = sdk.load_graph(graph.content_ref, tenant_id="tenant-a")
```

The M1 stores and descriptor indexes are process-local. External durability, replication, retention,
signing, and promotion remain later adapter and qualification work.

## Plugin boundary

A plugin first supplies the packaged `dnc.plugin.manifest` 1.0.0 contract. The caller must pin its
canonical SHA-256 fingerprint and explicitly grant its declared capabilities and permissions before
any entry-point import occurs.

```python
from dnc.plugins import PluginLoadPolicy, PluginManifest, PluginRegistry

manifest = PluginManifest.from_json(manifest_json)
policy = PluginLoadPolicy.trust(manifest)
plugins = PluginRegistry(policy)
plugins.register(manifest)
plugin = plugins.load(manifest.plugin_id)
```

The entry point is a zero-argument factory returning an object with the admitted `manifest` and an
`activate(runtime)` method. Load-time admission repeats the compatibility, fingerprint, capability,
permission, and manifest-match checks.

Python import executes code inside the current process. Fingerprint pinning and least-authority
declarations are governance controls, not a sandbox. Untrusted plugins require a separate process or
stronger isolation boundary. Plugins are explicit and optional; the core package has no new runtime
dependency and does not auto-import discovered packages.

## Compatibility

- Python SDK API: `1.0.0`.
- Plugin manifest schema: `1.0.0`.
- Plugin API: `1.0.0`.
- Current Generic DNC-IR: `1.3.0`; plugins must explicitly include it in their supported versions.
- The graph reader retains the shipped 1.1.0 and 1.2.0 compatibility paths and normalizes registered
  content to canonical 1.3.0.
