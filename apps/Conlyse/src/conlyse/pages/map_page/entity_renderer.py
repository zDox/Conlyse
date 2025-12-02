"""
Base Entity Renderer
====================
Abstract base class for rendering specific entity types using OpenGL.

Author: Copilot
Date: 2025-12-02
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from conlyse.pages.map_page.camera import Camera


class EntityRenderer(ABC):
    """
    Abstract base class for entity-specific renderers.
    
    Each renderer is responsible for rendering a specific type of entity
    (e.g., provinces, borders, units, etc.) using OpenGL.
    """

    def __init__(self):
        """Initialize the renderer."""
        self._initialized = False

    @abstractmethod
    def initialize(self):
        """
        Initialize OpenGL resources for this renderer.
        Called once when the GL context is ready.
        """
        pass

    @abstractmethod
    def render(self, camera: Camera, entities: Any):
        """
        Render entities using OpenGL.

        Args:
            camera: Camera for coordinate transformations
            entities: The entities to render (type depends on renderer)
        """
        pass

    @abstractmethod
    def cleanup(self):
        """
        Clean up OpenGL resources.
        Called when the renderer is no longer needed.
        """
        pass

    def is_initialized(self) -> bool:
        """
        Check if the renderer has been initialized.

        Returns:
            True if initialized, False otherwise
        """
        return self._initialized
