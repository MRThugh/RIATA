"""
Desktop capabilities package for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)
"""

from app.capabilities.base import BaseCapability
from app.capabilities.registry import CapabilityRegistry, get_capability_registry

__all__ = ["BaseCapability", "CapabilityRegistry", "get_capability_registry"]
