
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
import open3d as o3d
from PyQt5 import QtWidgets, QtCore
from .unified_annotation_controller import UnifiedAnnotationController


if TYPE_CHECKING:
    from ..view.gui import GUI


def has_active_point_decorator(func):
    """
    Only execute point manipulation if there is an active point.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if args[0].unified_annotation_controller.has_active_item():
            return func(*args, **kwargs)
        else:
            logging.warning("There is currently no active point to manipulate.")

    return wrapper


class PickPointController(object):
    """
    Controller for managing picked points in the 3D point cloud.
    It handles the registration of points and their visualization.
    """

    def __init__(self) -> None:
        self.view : GUI
        self.pcd_manager : PointCloudManger
        self.points :  List[Point] = []
        self.active_point_id = -1
        self.unified_annotation_controller: UnifiedAnnotationController
    
    def has_active_point(self) -> bool:
        return 0 <= self.active_point_id < len(self.points)
    def set_view(self, view: "GUI") -> None:
        self.view = view

    def add_point(self, point: Point) -> None:
        """
        Set the picked point and update the drawing strategy.
        """
        if isinstance(point, Point):
            self.points.append(point) #TODO  : Remove this line if not needed
            self.unified_annotation_controller.add_item(point)
            self.unified_annotation_controller.update_label_list()
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

    
    def get_active_point(self) -> Optional[Point]:
        if self.has_active_point():
            return self.points[self.active_point_id]
        else:
            return None


    def set_points(self, points: List[Point]) -> None:
        self.points = points
        self.deselect_point()
        self.update_label_list()


    def set_active_point(self, point_id: int) -> None:
        if 0 <= point_id < len(self.points):
            self.active_point_id = point_id
            self.update_all()
            self.view.status_manager.update_status(
                "Point sselected, it can now be corrected.", mode=Mode.CORRECTION
            )
        else:
            self.deselect_point()

    
    def update_all(self) -> None:
    
        self.update_curr_class()
        self.update_label_list()
        #self.view.update_point_stats(self.get_active_point()) #TODO : research
    

    def delete_bbox(self, point_id: int) -> None:
        if 0 <= point_id < len(self.points):
            del self.points[point_id]
            if point_id == self.active_point_id:
                self.set_active_point(len(self.points) - 1)
            else:
                self.update_label_list()



    def delete_current_point(self) -> None:
        selected_item_id = self.view.label_list.currentRow()
        self.delete_bbox(selected_item_id)


    def deselect_point(self) -> None:
        self.active_point_id = -1
        self.update_all()
        self.view.status_manager.set_mode(Mode.NAVIGATION)
    
    @has_active_point_decorator
    def get_classname(self) -> str:
        return self.get_active_point().get_classname()
    
    @has_active_point_decorator
    def set_classname(self, new_class: str) -> None:
        self.get_active_point().set_classname(new_class)  # type: ignore
        self.update_label_list()
    
    @has_active_point_decorator
    def update_z_dial(self) -> None:
        self.view.dial_bbox_z_rotation.blockSignals(True)  # To brake signal loop
        self.view.dial_bbox_z_rotation.setValue(int(self.get_active_point().get_z_rotation()))  # type: ignore
        self.view.dial_bbox_z_rotation.blockSignals(False)
    

    @has_active_point_decorator
    def translate_along_x(
        self, distance: Optional[float] = None, left: bool = False
    ) -> None:
        distance = distance or config.getfloat("LABEL", "std_translation")
        if left:
            distance *= -1

        cosz, sinz, bu = self.pcd_manager.get_perspective()

        active_point: Point = self.unified_annotation_controller.get_active_item()  # type: ignore
        active_point.set_x_translation(active_point.point[0] + distance * cosz)
        active_point.set_y_translation(active_point.point[1] + distance * sinz)

    @has_active_point_decorator
    def translate_along_y(
        self, distance: Optional[float] = None, forward: bool = False
    ) -> None:
        distance = distance or config.getfloat("LABEL", "std_translation")
        if forward:
            distance *= -1

       
        cosz, sinz, bu = self.pcd_manager.get_perspective()

        active_point: Point = self.unified_annotation_controller.get_active_item()  # type: ignore
        active_point.set_x_translation(active_point.point[0] + distance * bu * -sinz)
        active_point.set_y_translation(active_point.point[1] + distance * bu * cosz)

    @has_active_point_decorator
    def translate_along_z(
        self, distance: Optional[float] = None, down: bool = False
    ) -> None:
        
        
        distance = distance or config.getfloat("LABEL", "std_translation")
        if down:
            distance *= -1

        active_point: Point = self.unified_annotation_controller.get_active_item()  # type: ignore
        active_point.set_z_translation(active_point.point[2] + distance)




    def update_label_list(self) -> None:
        """Updates the list of drawn labels and highlights the active label.

        Should be always called if the bounding boxes changed.
        :return: None
        """
        self.unified_annotation_controller.update_label_list()


    def update_curr_class(self) -> None:
        if self.view is None:
            logging.error("View is not set yet. Cannot set active point.")
            return
    
        if self.has_active_point():
            self.view.current_class_dropdown.setCurrentText(
                self.get_active_point().classname  # type: ignore
            )

            print(f"DEBUG ::: update_curr_class called{self.get_active_point().classname}")
        else:
            self.view.controller.pcd_manager.populate_class_dropdown()
        
    
    def reset(self) -> None:
        self.deselect_point()
        self.set_points([])


    @has_active_point_decorator
    def assign_label_to_active_point(self) -> None:
        point = self.get_active_point()
        if point is not None:
            self.pcd_manager.assign_label_to_point(point)