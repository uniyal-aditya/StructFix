# Future Work & Roadmap

The following enhancements are planned for future releases of StructFix:

## 1. Streaming JSON Repair
- Support for chunk-by-chunk repair of streaming LLM outputs in flight.
- Partial bracket auto-completion for progressive UI rendering.

## 2. Pydantic & TypeSpec Schema Adapters
- Direct integration with Pydantic v2 models without requiring explicit JSON Schema export.
- Support for TypeSpec and TypeScript interface definitions.

## 3. Additional Local Inference Engines
- Native bindings for `llama.cpp` (via `llama-cpp-python`) and `vLLM` alongside Ollama.
- ONNX Runtime support for tiny quantized repair models running directly on CPU.

## 4. Enhanced Semantic Healing
- Differential field-level repair (re-prompting only for the specific invalid JSON paths rather than the whole document).
- Vector-indexed few-shot repair prompts for domain-specific schemas.
