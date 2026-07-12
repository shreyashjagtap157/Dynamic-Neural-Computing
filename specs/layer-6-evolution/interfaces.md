# Execution Provider Interface

## Metadata

| Field | Value |
|---|---|
| Document | interfaces.md |
| Title | Execution Provider Interface |
| Document ID | SPEC-IFACE |
| State | Frozen |
| Version | Architecture v1.0 |
| Owner | DNC Specification |
| Layer | 6 |
| Owner Question | What interfaces must execution providers implement? |
| Last Updated | 2026-07-11 |

---

## Status

| Property | Value |
|---|---|
| Normative | Yes |
| Depends on | core-terminology.md, execution-semantics.md, architecture.md |
| Defines | ExecutionCapability, ExecutionProvider interface, capability flags, provider metadata |
| Referenced by | execution-trace-format.md, conformance-model.md |

---

## Section 1 — Overview

### 1.A Purpose

This document defines the abstract interfaces for execution capabilities and execution providers. These interfaces are the contract between DNC's scheduler and the computational resources it orchestrates.

### 1.B Design Philosophy

The interfaces follow the principle: **capabilities are stable; providers are transient.**

- A capability (CAP-REASONING, CAP-RETRIEVAL, CAP-VERIFICATION) represents a class of computation that is stable across time.
- A provider (OpenAI, Anthropic, Ollama, FAISS, Z3) is a concrete implementation of one or more capabilities.
- The interface abstracts away provider identity, leaving only capability as the relevant dimension.

This design ensures DNC remains architecturally stable as providers come and go.

---

## Section 2 — Execution Capability

### 2.A Definition

An **ExecutionCapability** (CAP-*) is an abstract identifier for a class of computation that an execution provider may implement.

### 2.B Capability Registry

The following capabilities are defined. Additional capabilities may be added via the extension mechanism in `conformance-model.md`.

| Identifier | Name | Description |
|---|---|---|
| CAP-REASONING | Reasoning | The provider generates reasoning outputs (text, decisions, plans) based on structured input. Encompasses chain-of-thought, tree-of-thought, and future reasoning paradigms. |
| CAP-RETRIEVAL | Retrieval | The provider retrieves relevant information from a knowledge base or external source. |
| CAP-PLANNING | Planning | The provider synthesizes plans or decomposes tasks into sub-goals. |
| CAP-VERIFICATION | Verification | The provider checks whether an output satisfies specified constraints or correctness criteria. |
| CAP-SIMULATION | Simulation | The provider executes a simulation or model-based computation. |
| CAP-OPTIMIZATION | Optimization | The provider finds optimal solutions within defined constraints. |
| CAP-EXECUTION | Execution | The provider executes code, commands, or procedural operations. |
| CAP-EMBEDDING | Embedding | The provider produces vector embeddings from inputs. |
| CAP-TRANSCRIPTION | Transcription | The provider converts audio to text or text to audio. |
| CAP-TRANSLATION | Translation | The provider translates between representations or modalities. |

### 2.C Capability Declaration

An execution provider MUST declare which capabilities it implements via `supports(capability: ExecutionCapability) → bool`.

A provider MAY implement multiple capabilities. The capabilities a provider implements are fixed for the lifetime of the provider instance.

---

## Section 3 — Execution Provider Interface

### 3.A Abstract Interface

All execution providers implement the following interface:

```python
class ExecutionProvider:
    """Abstract execution provider interface."""

    @property
    def provider_id(self) -> str:
        """Unique identifier for this provider instance."""

    @property
    def provider_version(self) -> str:
        """Version string of the provider implementation."""

    @property
    def provider_metadata(self) -> ProviderMetadata:
        """Metadata describing provider capabilities and limits."""

    def supports(self, capability: ExecutionCapability) -> bool:
        """Return True if this provider implements the given capability."""

    def execute(
        self,
        capability: ExecutionCapability,
        input: Any,
        config: Optional[Dict[str, Any]] = None,
    ) -> ProviderResult:
        """Execute the given capability with the provided input."""

    def estimate_cost(
        self,
        capability: ExecutionCapability,
        input: Any,
    ) -> CostEstimate:
        """Estimate the cost (tokens, time, money) of executing the given input."""

    def get_capabilities(self) -> Set[ExecutionCapability]:
        """Return the set of all capabilities this provider supports."""
```

### 3.B ProviderMetadata

```python
@dataclass(frozen=True)
class ProviderMetadata:
    """Metadata about an execution provider."""

    provider_name: str              # e.g., "OpenAI", "Anthropic", "Ollama"
    provider_type: str             # e.g., "openai", "anthropic", "ollama", "vllm"
    api_endpoint: Optional[str]    # API endpoint URL, if applicable
    supports_streaming: bool       # Whether streaming responses are supported
    supports_structured_output: bool # Whether structured output is supported
    max_concurrent_requests: int   # Maximum concurrent requests
    rate_limit_rpm: int             # Requests per minute limit (0 = unlimited)
    context_window: int            # Maximum context size in tokens (0 = unknown)
    supports_custom_models: bool   # Whether custom model selection is available
```

### 3.C ProviderResult

```python
@dataclass(frozen=True)
class ProviderResult:
    """Result returned by an execution provider."""

    output: Any                    # The primary output
    provider_id: str               # Which provider produced this
    latency_ms: float              # Wall-clock execution time
    token_usage: Optional[TokenUsage]  # Token consumption, if applicable
    cost_estimate: CostEstimate    # Actual cost of this execution
    metadata: Dict[str, Any]        # Provider-specific metadata
    error: Optional[str]            # Error message if execution failed
```

### 3.D CostEstimate

```python
@dataclass(frozen=True)
class CostEstimate:
    """Estimated or actual cost of an execution."""

    tokens_in: int                 # Input tokens consumed
    tokens_out: int               # Output tokens produced
    compute_ms: float              # Compute time in milliseconds
    estimated_cost_usd: float      # Cost in USD (0.0 if not applicable)
```

### 3.E TokenUsage

```python
@dataclass(frozen=True)
class TokenUsage:
    """Token consumption for a single execution."""

    input_tokens: int
    output_tokens: int
    reasoning_tokens: Optional[int] = None  # Provider-specific reasoning token count
    total_tokens: int = 0

    def __post_init__(self):
        if self.total_tokens == 0:
            object.__setattr__(self, 'total_tokens', self.input_tokens + self.output_tokens)
```

---

## Section 4 — LLM-Specific Provider Interface

### 4.A LLMProvider Extension

For execution providers that implement CAP-REASONING, the following additional interface applies:

```python
class LLMProvider(ExecutionProvider):
    """Extension of ExecutionProvider for LLM-specific operations."""

    def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> LLMResponse:
        """Send a chat completion request."""

    def structured_output(
        self,
        prompt: str,
        schema: Dict[str, Any],
        model: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """Generate output conforming to a specified schema."""

    def with_reasoning(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate output with explicit reasoning steps visible in the trace."""
```

### 4.B ChatMessage

```python
@dataclass(frozen=True)
class ChatMessage:
    """A single message in a chat conversation."""

    role: str          # "system", "user", "assistant", "tool"
    content: str      # Text content
    name: Optional[str] = None  # Name of sender (for multi-agent)
```

### 4.C LLMResponse

```python
@dataclass(frozen=True)
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    model: str
    finish_reason: str  # "stop", "length", "content_filter", "error"
    llm_metadata: Dict[str, Any]  # Provider-specific (reasoning_effort, etc.)
```

---

## Section 5 — Execution Capability Flags

Rather than identifying providers by name (OpenAI, Anthropic), DNC identifies providers by capability. The scheduler uses capability flags to match module requirements to provider capabilities.

### 5.A Standard Capability Flags

| Flag | Meaning |
|---|---|
| `SUPPORTS_CHAT` | Provider can process conversational input |
| `SUPPORTS_REASONING` | Provider can perform structured reasoning |
| `SUPPORTS_TOOLS` | Provider supports tool use / function calling |
| `SUPPORTS_IMAGES` | Provider can process image inputs |
| `SUPPORTS_JSON` | Provider supports structured JSON output |
| `SUPPORTS_STREAMING` | Provider supports streaming responses |
| `SUPPORTS_EMBEDDINGS` | Provider can produce vector embeddings |
| `SUPPORTS_FUNCTION_CALLING` | Provider supports function/tool calling |
| `SUPPORTS_VISION` | Provider can interpret visual inputs |
| `SUPPORTS_AUDIO` | Provider can process audio inputs |

### 5.B Capability Resolution

When a module requests a capability, the scheduler resolves the request as follows:

```
1. Collect all providers that declare supports(capability) = True
2. Filter by required flags (e.g., SUPPORTS_JSON if structured output required)
3. Select provider based on policy (cost, latency, reliability)
4. Bind module to selected provider at dispatch time
```

The selection policy is configurable and may be rule-based (cheapest, fastest, most reliable) or model-based (learned selection based on task characteristics).

---

## Section 6 — Module-to-Provider Binding

### 6.A Binding Model

A module instance in an execution graph does not directly reference a provider. Instead:

```
ModuleInstance
    declares capability requirement: CAP-REASONING
    references module contract: ModuleContract(capabilities=[CAP-REASONING])
            ↓
    Scheduler at dispatch time:
        queries ExecutionProviderRegistry for providers supporting CAP-REASONING
        selects provider based on selection policy
        dispatches module to selected provider
```

This binding model ensures provider independence: the execution graph is provider-agnostic.

### 6.B ExecutionProviderRegistry

```python
class ExecutionProviderRegistry:
    """Registry of available execution providers."""

    def register(self, provider: ExecutionProvider) -> None:
        """Register a provider."""

    def unregister(self, provider_id: str) -> None:
        """Remove a provider from the registry."""

    def providers_for_capability(
        self,
        capability: ExecutionCapability,
        required_flags: Set[str] = None,
    ) -> List[ExecutionProvider]:
        """Return all providers supporting the given capability."""

    def select_provider(
        self,
        capability: ExecutionCapability,
        required_flags: Set[str] = None,
        selection_policy: str = "cost",
    ) -> Optional[ExecutionProvider]:
        """Select a provider based on the given policy."""
```

---

## Section 7 — Conformance Clause

An implementation conforms to this specification if:

- Every execution provider implements the ExecutionProvider interface in Section 3.A
- Every provider's `supports()` returns True only for capabilities it genuinely implements
- Every provider's `execute()` produces a ProviderResult with all required fields
- The ExecutionProviderRegistry is implemented as specified
- Capability resolution in Section 5.B is implemented as specified
- Module-to-provider binding in Section 6 is provider-independent

Extensions are permitted only under `conformance-model.md` Section 3. Vendor-specific extensions use the EXT-* namespace.

---

## Section 8 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| IFACE-AMEND-001 | interfaces.md | 2026-07-11 | Architecture v1.0 Draft: Initial specification of ExecutionCapability, ExecutionProvider interface, capability flags, provider metadata, module-to-provider binding. | No |