"""Minimal stub of the :mod:`reportlab` package for tests.

Only the tiny subset of the real library required by the unit tests is
implemented.  The real project uses :mod:`reportlab` to render a very simple PDF
export of notebook content, but shipping the full dependency would add a large
binary footprint.  This stub provides a compatible API for the tests without
requiring any external packages.
"""

# The actual functionality is provided in :mod:`reportlab.pdfgen`.

