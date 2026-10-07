"""Shared inference defaults and display vocabulary, without changing class IDs."""
DEFAULT_CONFIDENCE = 0.7
LABEL_ALIASES = {
    "class_1": "Opisthorchis viverrini egg",
    "class_2": "Minute intestinal fluke egg",
    "opisthorchis viverrini egg": "Opisthorchis viverrini egg",
    "minute intestinal fluke egg": "Minute intestinal fluke egg",
}


def canonical_label(label):
    # Match explicit names only: class ID 1 in a COCO model is NOT a parasite.
    return LABEL_ALIASES.get(str(label).strip().casefold(), str(label))


def canonical_labels(labels):
    names = [canonical_label(label) for label in labels]
    if len(set(names)) != len(names):
        raise ValueError("Class labels collide after alias normalization")
    return names
