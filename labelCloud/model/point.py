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


class Point(object):
    MIN_DIMENSION: float = config.getfloat("LABEL", "MIN_BOUNDINGBOX_DIMENSION")
    HIGHLIGHTED_COLOR: Color3f = Color3f(0, 1, 0)

    def __init__(
        self,
        point: Point3D
    ) -> None:
        self.point: Point3D = point
    
        self.classname: str = LabelConfig().get_default_class_name()

    # GETTERS

    def get_point(self) -> Point3D:
        return self.center
    
    def get_classname(self) -> str:
        return self.classname

   
    # SETTERS

    def set_classname(self, classname: str) -> None:
        if classname:
            self.classname = classname


    # Draw the BBox using verticies
    def draw(self, highlighted: bool = False) -> None:

        GL.glPushMatrix()
        point_color = LabelConfig().get_class_color(self.classname)
        if highlighted:
            point_color = self.HIGHLIGHTED_COLOR
        oglhelper.draw_points([self.point], color=Color3f.to_rgba(point_color))
        GL.glPopMatrix()
        

    