import logging
from contextlib import contextmanager
from typing import Optional, Tuple, Union

import numpy as np
import numpy.typing as npt
import OpenGL.GL as GL
from OpenGL import GLU
from PyQt5 import QtGui, QtOpenGL, QtCore

from ..control.alignmode import AlignMode
from ..control.unified_annotation_controller import UnifiedAnnotationController
from ..control.config_manager import config
from ..control.drawing_manager import DrawingManager
from ..control.pcd_manager import PointCloudManger
from ..definitions.types import Color4f, Point2D
from ..utils import oglhelper

from ..model.bbox import BBox
from ..model.point import Point

@contextmanager
def ignore_depth_mask():
    GL.glDepthMask(GL.GL_FALSE)
    try:
        yield
    finally:
        GL.glDepthMask(GL.GL_TRUE)


# Main widget for presenting the point cloud
class GLWidget(QtOpenGL.QGLWidget):
    NEAR_PLANE = config.getfloat("USER_INTERFACE", "near_plane")
    FAR_PLANE = config.getfloat("USER_INTERFACE", "far_plane")

    def __init__(self, parent=None) -> None:
        QtOpenGL.QGLWidget.__init__(self, parent)
        self.setMouseTracking(
            True
        )  # mouseMoveEvent is called also without button pressed

        self.modelview: Optional[npt.NDArray] = None
        self.projection: Optional[npt.NDArray] = None
        self.DEVICE_PIXEL_RATIO: float = (
            self.devicePixelRatioF()
        )  # 1 = normal; 2 = retina display
        oglhelper.DEVICE_PIXEL_RATIO = (
            self.DEVICE_PIXEL_RATIO
        )  # set for helper functions

        self.pcd_manager: PointCloudManger = None  # type: ignore
        self.bbox_controller: BoundingBoxController = None  # type: ignore
        self.unified_annotation_controller: UnifiedAnnotationController = None
 

        # Objects to be drawn
        self.crosshair_pos: Point2D = (0, 0)
        self.crosshair_col: Color4f = (0, 1, 0, 1)
        self.selected_side_vertices: npt.NDArray = np.array([])
        self.drawing_mode: DrawingManager = None  # type: ignore
        self.align_mode: Union[AlignMode, None] = None

        self.current_label_text: Optional[str] = None

    def set_pointcloud_controller(self, pcd_manager: PointCloudManger) -> None:
        self.pcd_manager = pcd_manager


    def set_unified_annotation_controller(self, unified_annotation_controller: UnifiedAnnotationController ):
        self.unified_annotation_controller = unified_annotation_controller


    # QGLWIDGET METHODS

    def initializeGL(self) -> None:
        bg_color = [
            int(fl_color)
            for fl_color in config.getlist("USER_INTERFACE", "BACKGROUND_COLOR")
        ]  # floats to ints
        self.qglClearColor(QtGui.QColor(*bg_color))  # screen background color
        GL.glEnable(GL.GL_DEPTH_TEST)  # for visualization of depth
        GL.glEnable(GL.GL_BLEND)  # enable transparency
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        logging.info("Intialized widget.")

        # Must be written again, due to buffer clearing
        self.pcd_manager.pointcloud.create_buffers()  # type: ignore

    def resizeGL(self, width, height) -> None:
        logging.info("Resized widget.")
        GL.glViewport(0, 0, width, height)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        aspect = width / float(height)

        GLU.gluPerspective(45.0, aspect, GLWidget.NEAR_PLANE, GLWidget.FAR_PLANE)
        GL.glMatrixMode(GL.GL_MODELVIEW)

    def paintGL(self) -> None:
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glPushMatrix()  # push the current matrix to the current stack

        # Draw point cloud
        self.pcd_manager.pointcloud.draw_pointcloud()  # type: ignore

        # Get actual matrices for click unprojection
        self.modelview = GL.glGetDoublev(GL.GL_MODELVIEW_MATRIX)
        self.projection = GL.glGetDoublev(GL.GL_PROJECTION_MATRIX)

        with ignore_depth_mask():  # Do not write decoration and preview elements in depth buffer
            if config.getboolean("USER_INTERFACE", "show_floor"):
                oglhelper.draw_xy_plane(self.pcd_manager.pointcloud)  # type: ignore

            # Draw crosshair/ cursor in 3D world
            if self.crosshair_pos:
                cx, cy, cz = self.get_world_coords(*self.crosshair_pos, correction=True)
                oglhelper.draw_crosshair(cx, cy, cz, color=self.crosshair_col)

            if self.drawing_mode.has_preview():
                self.drawing_mode.draw_preview()

            if self.align_mode is not None:
                if self.align_mode.is_active:
                    self.align_mode.draw_preview()

            # Highlight selected side with filled rectangle
            if len(self.selected_side_vertices) == 4:
                oglhelper.draw_rectangles(
                    self.selected_side_vertices, color=(0, 1, 0, 0.3)
                )
        
        if self.unified_annotation_controller.has_active_item():
            self.unified_annotation_controller.get_active_item().draw(highlighted=True) 

            if config.getboolean("USER_INTERFACE", "show_orientation") and isinstance(self.unified_annotation_controller.get_active_item(), BBox):
                self.unified_annotation_controller.get_active_item().draw_orientation()


        for label in  self.unified_annotation_controller.items:
            label.draw()

        GL.glPopMatrix()  # restore the previous modelview matrix


    # Translates the 2D cursor position from screen plane into 3D world space coordinates
    def get_world_coords(
        self, x: float, y: float, z: Optional[float] = None, correction: bool = False
    ) -> Tuple[float, float, float]:
        x *= self.DEVICE_PIXEL_RATIO  # For fixing mac retina bug
        y *= self.DEVICE_PIXEL_RATIO

        # Stored projection matrices are taken from loop
        viewport = GL.glGetIntegerv(GL.GL_VIEWPORT)
        real_y = viewport[3] - y  # adjust for down-facing y positions

        if z is None:
            buffer_size = 21
            center = buffer_size // 2 + 1
            depths = GL.glReadPixels(
                x - center + 1,
                real_y - center + 1,
                buffer_size,
                buffer_size,
                GL.GL_DEPTH_COMPONENT,
                GL.GL_FLOAT,
            )
            z = depths[center][center]  # Read selected pixel from depth buffer

            if z == 1:
                z = depth_smoothing(depths, center)
            elif correction:
                z = depth_min(depths, center)

        mod_x, mod_y, mod_z = GLU.gluUnProject(
            x, real_y, z, self.modelview, self.projection, viewport
        )
        return mod_x, mod_y, mod_z
    

    def set_current_label(self, text: Optional[str]) -> None:
        """Set the label text to display at the bottom of the widget."""
        self.current_label_text = text
        self.update()  # force repaint


# Creates a circular mask with radius around center
def circular_mask(arr_length, center, radius) -> np.ndarray:
    dx = np.arange(arr_length)
    return (dx[np.newaxis, :] - center) ** 2 + (
        dx[:, np.newaxis] - center
    ) ** 2 < radius**2


# Returns the minimum (closest) depth for a specified radius around the center
def depth_min(depths, center, r=4) -> float:
    selected_depths = depths[circular_mask(len(depths), center, r)]
    filtered_depths = selected_depths[(0 < selected_depths) & (selected_depths < 1)]
    if 0 in depths:  # Check if cursor is at widget border
        return 1
    elif len(filtered_depths) > 0:
        return np.min(filtered_depths)
    else:
        return 0.5


# Returns the mean depth for a specified radius around the center
def depth_smoothing(depths, center, r=15) -> float:
    selected_depths = depths[circular_mask(len(depths), center, r)]
    if 0 in depths:  # Check if cursor is at widget border
        return 1
    elif np.isnan(
        selected_depths[selected_depths < 1]
    ).all():  # prevent mean of empty slice
        return 1
    return np.nanmedian(selected_depths[selected_depths < 1])

