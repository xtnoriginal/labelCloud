import logging
from typing import List, Optional

import numpy as np
import numpy.typing as npt

import OpenGL.GL as GL

from ..control.config_manager import config
from ..definitions import (
    BBOX_EDGES,
    BBOX_SIDES,
    Color3f,
    Dimensions3D,
    Point3D,
    Rotations3D,
)
from ..io.labels.config import LabelConfig
from ..utils import math3d, oglhelper

# Added point class which stored the point id and point coordinates. Once confused my self with Point3D type alias
# Point3D = npt.NDArray[np.float32]  # (x,y,z)
class Point(object):
    MIN_DIMENSION: float = config.getfloat("LABEL", "MIN_BOUNDINGBOX_DIMENSION")
    HIGHLIGHTED_COLOR: Color3f = Color3f(0, 1, 0)

    def __init__(
        self,
        point: Point3D, 
        point_id : int
    ) -> None:
        self.point: Point3D = point 
        self.classname: str = LabelConfig().get_default_class_name()
        self.point_id = point_id

    # GETTERS

    def get_point(self) -> Point3D:
        return self.center
    
    def get_classname(self) -> str:
        return self.classname
    
    def get_coords(self):
        return (self.point[0], self.point[1], self.point[2])

   
    # SETTERS
    def set_classname(self, classname: str) -> None:
        if classname:
            self.classname = classname
    

    def set_x_rotation(self, angle: float) -> None:
        pass

    def set_y_rotation(self, angle: float) -> None:
        pass

    def set_z_rotation(self, angle: float) -> None:
        pass


    
    def set_x_translation(self, x_translation: float) -> None:
        self.point = (x_translation, *self.point[1:])

    def set_y_translation(self, y_translation: float) -> None:
        self.point = (self.point[0], y_translation, self.point[2])

    def set_z_translation(self, z_translation: float) -> None:
        self.point = (*self.point[:2], z_translation)

    # Draw the BBox using verticies
    def draw(self, highlighted: bool = False) -> None:

        GL.glPushMatrix()
        point_color = LabelConfig().get_class_color(self.classname)
        if highlighted:
            point_color = self.HIGHLIGHTED_COLOR
        # Import for adjustemnt of point size.
        oglhelper.draw_points([self.point], color=Color3f.to_rgba(point_color), point_size=min(config.getfloat("POINTCLOUD", "POINT_SIZE")*2.5, 20))
        GL.glPopMatrix()
        

    