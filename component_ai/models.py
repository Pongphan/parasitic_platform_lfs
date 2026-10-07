"""2026 ROI → resize → float32 → predict → ensemble, with explicit contracts."""
import hashlib
import threading
from pathlib import Path
import numpy as np
import streamlit as st
from PIL import Image
from component_ai.settings import canonical_labels

# Preserve the original public imports while keeping discovery separate.
from component_ai.registry import MODEL_DIR, discover_models, model_inventory, file_version, model_contract

@st.cache_resource(show_spinner=False, max_entries=8)
def load_model(path, version):
    """File version invalidates replaced weights; lock protects shared inference."""
    try:
        import tensorflow as tf
    except ImportError as exc:
        raise RuntimeError("Install requirements-ai.txt to enable Keras inference.") from exc
    model = tf.keras.models.load_model(path, compile=False, safe_mode=True)
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return model, threading.RLock(), digest

def prepare_input_tensor(crop_image, model, normalize_to_01=False):
    shape = model.input_shape
    if isinstance(shape, list) or len(shape) != 4 or shape[0] not in (None, 1) or shape[3] not in (1, 3):
        raise ValueError("Expected a single channels-last RGB or grayscale image input.")
    height, width = shape[1:3]
    if not isinstance(height, int) or not isinstance(width, int) or min(height, width) < 1 or height * width > 4_000_000:
        raise ValueError("Model requires fixed image dimensions of at most 4 megapixels.")
    image = crop_image.convert("RGB" if shape[3] == 3 else "L")
    array = np.asarray(image.resize((width, height), Image.Resampling.BICUBIC), dtype=np.float32)
    if shape[3] == 1:
        array = array[..., None]
    if normalize_to_01:
        array = array / 255.0
    return array[None, ...]

def postprocess_prediction(raw, labels, output="probabilities"):
    labels = canonical_labels(labels)
    if output not in ("probabilities", "logits", "sigmoid_scores"):
        raise ValueError("Unsupported output contract")
    if isinstance(raw, (dict, list, tuple)):
        raise ValueError("Multiple model outputs are unsupported.")
    values = np.asarray(raw, dtype=np.float64)
    if values.ndim == 2 and values.shape[0] == 1:
        values = values[0]
    if values.ndim != 1 or not values.size or not np.all(np.isfinite(values)):
        raise ValueError("Model returned invalid or non-finite classification scores.")
    if values.size == 1 and len(labels) == 2:
        score = float(values[0])
        if output == "logits":
            score = float(1 / (1 + np.exp(-np.clip(score, -700, 700))))
        values = np.array([1 - score, score])
    elif values.size != len(labels):
        raise ValueError("Output dimensions do not match the declared class labels.")
    elif output == "logits":
        values = np.exp(values - values.max())
        values /= values.sum()
    raw_scores = values.tolist()
    if output == "sigmoid_scores":
        if np.any(values < 0) or np.any(values > 1) or values.sum() <= 0:
            raise ValueError("Invalid sigmoid scores")
        values /= values.sum()
    if np.any(values < 0) or np.any(values > 1) or not np.isclose(values.sum(), 1, atol=0.001):
        raise ValueError("Expected probabilities; verify the model output contract.")
    values /= values.sum()
    index = int(values.argmax())
    return {"label": labels[index], "index": index, "scores": values.tolist(), "raw_scores": raw_scores, "labels": labels}

def build_ensemble_summary(results):
    if not results:
        return None
    labels = results[0]["prediction"]["labels"]
    if any(r["prediction"]["labels"] != labels for r in results):
        raise ValueError("Ensemble requires identical class labels and order.")
    scores = np.mean([r["prediction"]["scores"] for r in results], axis=0)
    votes = [r["prediction"]["index"] for r in results]
    counts = [votes.count(i) for i in range(len(labels))]
    winners = [labels[i] for i, count in enumerate(counts) if count == max(counts)]
    return {"label": labels[int(scores.argmax())], "scores": scores.tolist(), "labels": labels, "vote_counts": dict(zip(labels, counts)), "majority": winners}

def classify(image, paths):
    results, errors = [], []
    for path in paths:
        try:
            contract = model_contract(path)
            model, lock, digest = load_model(str(path.resolve()), file_version(path))
            tensor = prepare_input_tensor(image, model, contract["preprocessing"] == "scale_0_1")
            with lock:
                raw = model.predict(tensor, verbose=0)
            prediction = postprocess_prediction(raw, contract["labels"], contract["output"])
            results.append({"model": path.name, "model_sha256": digest, "contract": contract, "input_shape": list(tensor.shape), "prediction": prediction})
        except Exception as exc:
            errors.append({"model": path.name, "error": str(exc)})
    try:
        ensemble = build_ensemble_summary(results)
    except ValueError as exc:
        errors.append({"model": "ensemble", "error": str(exc)})
        ensemble = None
    return {"predictions": results, "ensemble": ensemble, "errors": errors}
