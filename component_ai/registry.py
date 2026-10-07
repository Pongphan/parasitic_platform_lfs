"""Model discovery and JSON contracts, independent of cached inference modules."""
import json
from pathlib import Path
from component_ai.settings import canonical_labels

MODEL_DIR = Path(__file__).resolve().parent / "keras"

def discover_models(root=None):
    """Resolve beside this module, independent of the launch working directory."""
    folder = Path(root).resolve() if root is not None else Path(__file__).resolve().parent / "keras"
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".keras")

def model_inventory(root=None):
    """Check each contract without loading TensorFlow or hiding invalid entries."""
    rows = []
    for path in discover_models(root):
        try:
            contract = model_contract(path)
            error = None
        except (ValueError, OSError) as exc:
            contract, error = None, str(exc)
        rows.append({"path": path, "contract": contract, "error": error})
    return rows

def file_version(path):
    stat = Path(path).stat()
    return (stat.st_mtime_ns, stat.st_size)

def model_contract(path):
    metadata = Path(path).with_suffix(".json")
    if not metadata.is_file():
        raise ValueError(f"Missing model contract: {metadata.name}")
    try:
        contract = json.loads(metadata.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError(f"Invalid JSON in {metadata.name}: {exc}") from exc
    if not isinstance(contract, dict) or type(contract.get("schema_version")) is not int or contract["schema_version"] != 1:
        raise ValueError(f"{metadata.name}: expected a JSON object with schema_version 1")
    labels = contract.get("labels", [])
    if not isinstance(labels, list) or len(labels) < 2 or any(not isinstance(x, str) or not x for x in labels) or len(set(labels)) != len(labels):
        raise ValueError("Model labels must be unique nonempty strings in training order")
    if contract.get("preprocessing") not in ("raw_0_255", "scale_0_1") or contract.get("output") not in ("probabilities", "logits", "sigmoid_scores"):
        raise ValueError("Unsupported preprocessing or output contract")
    contract["labels"] = canonical_labels(labels)
    return contract

