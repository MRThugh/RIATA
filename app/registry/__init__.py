"""Registry package for R.I.A.T.A."""

from app.registry.applications import (
    AppEntry,
    ApplicationRegistry,
    get_application_registry,
)

__all__ = ["AppEntry", "ApplicationRegistry", "get_application_registry"]
