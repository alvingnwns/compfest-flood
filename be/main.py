"""Compatibility entry point: run `uvicorn main:app --reload` from `be/`."""

from app.main import app

__all__ = ["app"]
