"""
Capability Registry for R.I.A.T.A v0.2.0
Author: Ali Kamrani (MRThugh)

Central discovery and dispatch coordinator for modular desktop capabilities.
"""

from typing import Optional

from app.capabilities.applications import ApplicationsCapability
from app.capabilities.base import BaseCapability
from app.capabilities.clipboard import ClipboardCapability
from app.capabilities.filesystem import FilesystemCapability
from app.capabilities.media import MediaCapability
from app.capabilities.notifications import NotificationsCapability
from app.capabilities.processes import ProcessesCapability
from app.capabilities.system import SystemCapability
from app.capabilities.windows import WindowsCapability
from app.core.logger import get_logger

logger = get_logger("riata.capabilities")


class CapabilityRegistry:
    """Manages discovery and dispatching for desktop capabilities."""

    def __init__(self) -> None:
        self._capabilities: dict[str, BaseCapability] = {}
        self._intent_to_capability: dict[str, BaseCapability] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register built-in capability providers."""
        defaults = [
            ApplicationsCapability(),
            FilesystemCapability(),
            MediaCapability(),
            SystemCapability(),
            ProcessesCapability(),
            WindowsCapability(),
            NotificationsCapability(),
            ClipboardCapability(),
        ]
        for cap in defaults:
            self.register(cap)

    def register(self, capability: BaseCapability) -> None:
        """Register a capability provider."""
        self._capabilities[capability.id] = capability
        for intent_name in capability.supported_intents:
            self._intent_to_capability[intent_name] = capability
        logger.debug("Registered capability '%s' handling %s", capability.id, capability.supported_intents)

    def unregister(self, capability_id: str) -> bool:
        """Unregister a capability provider and its mapped intents."""
        if capability_id not in self._capabilities:
            return False
        cap = self._capabilities.pop(capability_id)
        for intent_name in cap.supported_intents:
            if self._intent_to_capability.get(intent_name) == cap:
                del self._intent_to_capability[intent_name]
        logger.debug("Unregistered capability '%s'", capability_id)
        return True

    def find_for_intent(self, intent_name: str) -> Optional[BaseCapability]:
        """Find the capability capable of handling the specified intent."""
        return self._intent_to_capability.get(intent_name)

    def supports_intent(self, intent_name: str) -> bool:
        """Check if any registered capability handles the specified intent."""
        return intent_name in self._intent_to_capability

    def get_capability(self, capability_id: str) -> Optional[BaseCapability]:
        """Retrieve capability by id."""
        return self._capabilities.get(capability_id)

    def list_capabilities(self) -> list[BaseCapability]:
        """List all registered capabilities."""
        return list(self._capabilities.values())


_GLOBAL_CAP_REGISTRY: Optional[CapabilityRegistry] = None


def get_capability_registry() -> CapabilityRegistry:
    """Retrieve global CapabilityRegistry singleton."""
    global _GLOBAL_CAP_REGISTRY
    if _GLOBAL_CAP_REGISTRY is None:
        _GLOBAL_CAP_REGISTRY = CapabilityRegistry()
    return _GLOBAL_CAP_REGISTRY
