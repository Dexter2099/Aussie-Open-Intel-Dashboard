"""Test configuration ensuring real service modules are available.

Some of the ingest tests install light-weight stubs into ``sys.modules`` for
``services`` and ``services.etl``.  Those stubs are useful when testing the
ingest layer in isolation but they interfere with the ETL service tests which
require the real implementations.  To avoid the stubs replacing the actual
packages we preload the real modules here.  Because ``conftest.py`` is imported
before any tests are collected this happens early enough that the subsequent
``sys.modules.setdefault`` calls in the ingest tests become no-ops.
"""

import importlib
import sys
from pathlib import Path

# Ensure the repository root is on ``sys.path`` so the ``services`` package can
# be imported when this configuration file is executed from any working
# directory.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import the real service packages so they are present in ``sys.modules``.
importlib.import_module("services")
# Pre-import ETL submodules so that ingest tests do not stub them out with
# ``sys.modules.setdefault``.
importlib.import_module("services.etl.fusion")
importlib.import_module("services.etl.enrich")
importlib.import_module("services.etl.nlp")

