
"""
A class to handle all user manipulations of a points and collect all labeling
settings in one place.
Point Management: adding, selecting updating, deleting points;
"""

import logging
from functools import wraps
from typing import TYPE_CHECKING, List, Optional

import numpy as np

from ..definitions import Mode,Point3D
from ..utils import oglhelper
from .config_manager import config
from .pcd_manager import PointCloudManger
from ..model.point import Point


if TYPE_CHECKING:
    from ..view.gui import GUI


def has_active_bbox_decorator(func):
    """
    Only execute point manipulation if there is an active point.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if args[0].has_active_ppointpoint_1selPoint3D():
            return func(*args, **kwargs)
        else:
            logging.warning("There is currently no active point to manipulate.")

    return wrapper


class PickedPointController(object):
    """
    Controller for managing picked points in the 3D point cloud.
    It handles the registration of points and their visualization.
    """

    def __init__(self) -> None:
        self.view = 'GUI'
        self.pcd_manager : PointCloudManger
        self.points :  List[Point] = []
        self.active_point_id = -1
    
    def has_active_point(self) -> bool:
        return 0 <= self.active_point_id < len(self.points)
    def set_view(self, view: "GUI") -> None:
        self.view = view

    def add_point(self, point: Point) -> None:
        """
        Set the picked point and update the drawing strategy.
        """
        if isinstance(point, Point):
            self.points.append(point)
            self.set_active_point(self.points.index(point))
            self.view.current_class_dropdown.setCurrentText(
                self.get_active_point().classname  # type: ignore
            )
            self.view.status_manager.update_status(
                "Point added, it can now be corrected.", Mode.CORRECTION
            )

    def get_point(self) -> Optional[Point]:
        """
        Get the currently picked point.
        """

        return self.point

    @has_active_bbox_decorator
    def get_classname(self) -> str:
        return self.get_active_bbox().get_classname()
    
    def get_active_bbox(self) -> Optional[Point]:
        if self.has_active_bbox():
            return self.points[self.active_point_id]
        else:
            return None



    def set_active_point(self, point_id: int) -> None:
        if 0 <= point_id < len(self.points):
            self.active_point_id = point_id
            self.update_all()
            self.view.tatus_manager.update_status(
                "Point sselected, it can now be corrected.", mode=Mode.CORRECTION
            )
        else:
            self.deselect_bbox()

    
    def update_all(self) -> None:
    
        self.update_curr_class()
        self.update_label_list()
        self.view.update_point_stats(self.get_active_bbox())
    
    @has_active_bbox_decorator
    def update_z_dial(self) -> None:
        self.view.dial_bbox_z_rotation.blockSignals(True)  # To brake signal loop
        self.view.dial_bbox_z_rotation.setValue(int(self.get_active_bbox().get_z_rotation()))  # type: ignore
        self.view.dial_bbox_z_rotation.blockSignals(False)

    def update_label_list(self) -> None:
        """Updates the list of drawn labels and highlights the active label.

        Should be always called if the bounding boxes changed.
        :return: None
        """
        self.view.label_list.blockSignals(True)  # To brake signal loop
        self.view.label_list.clear()
        for point in self.points:
            self.view.label_list.addItem(point.get_classname())
        if self.has_active_point():
            self.view.label_list.setCurrentRow(self.active_point_id)
            current_item = self.view.label_list.currentItem()
            if current_item:
                current_item.setSelected(True)
        self.view.label_list.blockSignals(False)
    