"""Stub of :mod:`reportlab.pdfgen` providing a tiny ``canvas`` module."""

from types import SimpleNamespace


class Canvas:
    """Very small stand-in for :class:`reportlab.pdfgen.canvas.Canvas`.

    The methods simply write nothing but keep the API used in the tests.  The
    generated PDF bytes are meaningless but the tests only check that a response
    is returned, not the contents of the PDF.
    """

    def __init__(self, _buffer):  # pragma: no cover - trivial
        self._buffer = _buffer

    def setFont(self, *args, **kwargs):  # pragma: no cover - no-op
        pass

    def drawString(self, *args, **kwargs):  # pragma: no cover - no-op
        pass

    def showPage(self):  # pragma: no cover - no-op
        pass

    def save(self):  # pragma: no cover - no-op
        pass


# Expose a ``canvas`` attribute mimicking the real package structure where the
# ``canvas`` module provides the ``Canvas`` class.
canvas = SimpleNamespace(Canvas=Canvas)

__all__ = ["canvas", "Canvas"]

