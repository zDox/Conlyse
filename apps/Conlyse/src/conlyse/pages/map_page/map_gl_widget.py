"""
Map OpenGL Widget
=================
OpenGL widget for rendering the map using PyQt6.

Author: Copilot
Date: 2025-12-02
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Any, Optional

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import QWidget
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import (
    glClearColor, glClear, glViewport, glMatrixMode, glLoadIdentity,
    glOrtho, GL_COLOR_BUFFER_BIT, GL_PROJECTION, GL_MODELVIEW
)

from conlyse.logger import get_logger
from conlyse.pages.map_page.camera import Camera
from conlyse.pages.map_page.entity_renderer import EntityRenderer

if TYPE_CHECKING:
    from PyQt6.QtGui import QMouseEvent, QWheelEvent

logger = get_logger()


class MapGLWidget(QOpenGLWidget):
    """
    OpenGL widget for rendering the map.
    
    Handles OpenGL context initialization, rendering loop, and user input.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the OpenGL widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Camera for view transformation
        self.camera: Optional[Camera] = None
        
        # Renderers for different entity types
        self.renderers: Dict[str, EntityRenderer] = {}
        
        # Data to render
        self.provinces: Dict[int, Any] = {}
        
        # Mouse interaction state
        self._last_mouse_pos: Optional[QPoint] = None
        self._is_panning = False
        
        # Widget settings
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    def add_renderer(self, name: str, renderer: EntityRenderer):
        """
        Add a renderer for a specific entity type.

        Args:
            name: Name/identifier for the renderer
            renderer: EntityRenderer instance
        """
        self.renderers[name] = renderer

    def set_provinces(self, provinces: Dict[int, Any]):
        """
        Set the provinces to render.

        Args:
            provinces: Dictionary of province_id -> province object
        """
        self.provinces = provinces
        self.update()

    def initializeGL(self):
        """Initialize OpenGL context and resources."""
        try:
            # Set clear color (background)
            glClearColor(0.2, 0.3, 0.4, 1.0)
            
            # Initialize camera
            self.camera = Camera(self.width(), self.height())
            
            # Initialize all renderers
            for name, renderer in self.renderers.items():
                logger.debug(f"Initializing renderer: {name}")
                renderer.initialize()
            
            logger.info("OpenGL initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing OpenGL: {e}", exc_info=True)

    def resizeGL(self, w: int, h: int):
        """
        Handle widget resize.

        Args:
            w: New width
            h: New height
        """
        glViewport(0, 0, w, h)
        
        if self.camera:
            self.camera.screen_width = w
            self.camera.screen_height = h
        
        # Set up orthographic projection
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, w, h, 0, -1, 1)  # Screen coordinates
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def paintGL(self):
        """Render the map."""
        try:
            # Clear the screen
            glClear(GL_COLOR_BUFFER_BIT)
            
            if not self.camera:
                return
            
            # Render all entities using their respective renderers
            for name, renderer in self.renderers.items():
                if not renderer.is_initialized():
                    continue
                
                # For now, we only pass provinces to all renderers
                # In the future, this can be extended to pass different data
                if name == "province":
                    renderer.render(self.camera, self.provinces)
        except Exception as e:
            logger.error(f"Error rendering map: {e}", exc_info=True)

    def mousePressEvent(self, event: QMouseEvent):
        """
        Handle mouse press events.

        Args:
            event: Mouse event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_panning = True
            self._last_mouse_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """
        Handle mouse release events.

        Args:
            event: Mouse event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_panning = False
            self._last_mouse_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseMoveEvent(self, event: QMouseEvent):
        """
        Handle mouse move events.

        Args:
            event: Mouse event
        """
        if self._is_panning and self._last_mouse_pos and self.camera:
            current_pos = event.pos()
            dx = current_pos.x() - self._last_mouse_pos.x()
            dy = current_pos.y() - self._last_mouse_pos.y()
            
            # Pan camera (negative because we move opposite to mouse)
            self.camera.pan(-dx, -dy)
            self._last_mouse_pos = current_pos
            
            # Trigger repaint
            self.update()

    def wheelEvent(self, event: QWheelEvent):
        """
        Handle mouse wheel events for zooming.

        Args:
            event: Wheel event
        """
        if not self.camera:
            return
        
        # Get scroll direction
        delta = event.angleDelta().y()
        
        # Zoom towards mouse position
        # Use pos() for better compatibility across PyQt6 versions
        mouse_pos = (event.position().x(), event.position().y())
        
        if delta > 0:
            self.camera.zoom_in(mouse_pos)
        else:
            self.camera.zoom_out(mouse_pos)
        
        # Trigger repaint
        self.update()

    def cleanup(self):
        """Clean up OpenGL resources."""
        for renderer in self.renderers.values():
            renderer.cleanup()
        self.renderers.clear()
        self.provinces.clear()
