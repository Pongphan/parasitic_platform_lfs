# Keras classifier assets

The six existing `.keras` files and their six sibling `.json` contracts were
moved here without changing their bytes. `component_ai.models.MODEL_DIR` resolves
this folder. The public `component_ai.keras` interface exports discovery, loading,
contract parsing and classification; existing `component_ai.models` imports remain
compatible. Adding another `.keras` plus its JSON contract requires no UI edits.

See `../README.md` for class order, preprocessing, output normalization and provenance.
