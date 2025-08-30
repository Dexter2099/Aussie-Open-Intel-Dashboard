"""Ingest package.

This package contains standalone command line adapters as well as shared
utilities located in the nested ``ingest`` subpackage.  The latter is added to
the package search path for convenience so ``ingest.common`` and similar modules
are available when importing :mod:`ingest`.

Historically the shared utilities lived under ``ingest.ingest`` while thin
wrappers were exposed at the package root.  To remain backwards compatible we
explicitly alias ``ingest.common`` to ``ingest.ingest.common`` so that
monkeypatching in tests affects both import paths.
"""

from importlib import import_module
from pkgutil import extend_path
import sys

# Allow namespace-style extension to include the legacy ``ingest/ingest``
# directory which contains shared modules.
__path__ = extend_path(__path__, __name__)

# Ensure ``ingest.common`` and ``ingest.ingest.common`` refer to the same module
# object so patches are reflected consistently.
_common = import_module("ingest.ingest.common")
sys.modules.setdefault(__name__ + ".common", _common)

__all__: list[str] = []
