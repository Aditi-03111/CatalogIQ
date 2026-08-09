# CatalogIQ — LLM Providers

## Overview

CatalogIQ uses an LLM provider abstraction layer for AI product extraction and AI commerce enrichment. All providers implement `BaseLLMProvider` and return validated Pydantic structures (`ExtractionResult` for Phase 4 extraction and `CommerceEnrichment` for Phase 5 enrichment). No provider-specific logic exists outside `backend/app/services/llm/`.

## Provider Architecture

```
BaseLLMProvider
├── OllamaProvider      → Local development (Qwen3 8B)
├── GeminiProvider      → Production (Gemini 3.6 Flash)
└── MockProvider        → Automated tests ONLY
```

## Interface Capabilities
Every provider implements two core interface methods:
1. `extract(ir: Dict[str, Any]) -> ExtractionResult` — Phase 4 semantic product extraction from parsed Docling IR.
2. `enrich(product_context: Dict[str, Any]) -> CommerceEnrichment` — Phase 5 evidence-backed B2B commerce content generation.

## Configuration

| Variable | Description | Default |
|---|---|---|
| `LLM_PROVIDER` | `ollama` \| `gemini` \| `mock` | `ollama` |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model name | `qwen3:8b` |
| `GEMINI_API_KEY` | Google Gemini API key | *(required for gemini)* |
| `GEMINI_MODEL` | Gemini model name | `gemini-3.6-flash` |

## Environment Presets

### Local Development (Ollama)
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
```
Prerequisites: `ollama serve` running, `ollama pull qwen3:8b` complete.

### Production (Gemini)
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.6-flash
```

### Tests
```env
LLM_PROVIDER=mock
ENV=test
```
`MockProvider` is only valid when `ENV=test`. Any other environment raises `ConfigurationError`.


## Provider Details

### OllamaProvider
- Calls `POST /api/chat` with `format: "json"` for structured output.
- `temperature=0.1` for deterministic extraction.
- Retries 3× on connection/HTTP errors with exponential backoff.
- Raises `ConfigurationError` if Ollama unreachable.

### GeminiProvider
- Uses `google-genai` SDK (`from google import genai`).
- `response_mime_type="application/json"` for enforced JSON output.
- `temperature=0.1` for deterministic extraction.
- Retries 3× on rate limits (429), 5xx, and timeouts.
- Raises `ConfigurationError` on missing `GEMINI_API_KEY`.

### MockProvider
- Returns a deterministic pre-baked `ExtractionResult` matching `MockParser` output.
- Never makes network calls.
- `provider_name="mock"`, `model_name="mock-v1"`.

## Adding a New Provider

1. Create `backend/app/services/llm/my_provider.py` extending `BaseLLMProvider`.
2. Implement `provider_name`, `model_name`, `prompt_version`, and `extract()`.
3. Add a branch in `factory.py`.
4. Add a corresponding `ENV` variable.
