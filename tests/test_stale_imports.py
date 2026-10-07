"""A running server can still have the pre-inventory models module imported."""
import subprocess
import sys
from pathlib import Path

def test_ui_imports_with_pre_update_models_module():
    root = Path(__file__).resolve().parents[1]
    # Isolate module-cache simulation from the other UI tests.
    script = """
import component_ai.models as models
del models.model_inventory
from component_layout import dashboard, detector
from component_ai.registry import model_inventory
assert len(model_inventory()) == 6
assert all(item['error'] is None for item in model_inventory())
assert dashboard.model_inventory is model_inventory
assert detector.model_inventory is model_inventory
assert detector.classify is models.classify
print('Cached pre-update models module: UI imports and six contracts OK')
"""
    result = subprocess.run([sys.executable, "-c", script], cwd=root, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
