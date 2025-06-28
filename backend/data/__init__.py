
from importlib import import_module
import sys

# Alias for backward compatibility
try:
    models = import_module('.models_core', __name__)
    sys.modules[__name__ + '.models'] = models
except ModuleNotFoundError:
    # Allow basic functionality when models_core is absent
    models = None


__all__ = []  # package exports handled by submodules
