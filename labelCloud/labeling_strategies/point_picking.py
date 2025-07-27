import logging
from typing import TYPE_CHECKING, List, Optional, cast

import numpy as np

from . import BaseLabelingStrategy
from ..control.config_manager import config
from ..definitions import Mode, Point3D
from ..model import BBox
from ..utils import math3d as math3d
from ..utils import oglhelper as ogl

if TYPE_CHECKING:
    from ..view.gui import GUI


class PointPickingStrategy(BaseLabelingStrategy):
    POINTS_NEEDED = 4
    PREVIEW = True
    CORRECTION = False  # Increases dimensions after drawing

    def __init__(self, view: "GUI") -> None:
        super().__init__(view)
        logging.info("Enabled point picking mode.")
        self.view.status_manager.update_status(
            "Begin by selecting a vertex.", mode=Mode.DRAWING
        )
        self.preview_color = (1, 1, 0, 1)
        self.point: Optional[Point3D] = None  # second edge
        self.tmp_p: Optional[Point3D] = None  # tmp points for preview

    def reset(self) -> None:
        super().reset()
        self.point = None
        self.tmp_p = None
        
        self.view.button_pick_point.setChecked(False)

    def register_point(self, new_point: Point3D) -> None:
        
        if self.point is None:
            self.point = new_point
        else:
            logging.warning("Cannot register point.")
    

    def register_tmp_point(self, new_tmp_point: Point3D) -> None:
        if self.point:
            self.tmp_p = new_tmp_point
            

    def get_bbox(self) -> BBox:
        
        return []

    def draw_preview(self) -> None:
        print(f"DEBUG: Drawing preview with point {self.point} and tmp_p {self.tmp_p}")
        if self.point:
            ogl.draw_points([self.point], color=self.preview_color)
                
        elif self.tmp_p:
            ogl.draw_points([self.tmp_p], color=self.preview_color)
           