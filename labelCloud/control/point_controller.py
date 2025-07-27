import logging
from functools import wraps
from typing import TYPE_CHECKING, List, Optional

import numpy as np

from ..definitions import Mode, Point3D

from ..utils import oglhelper
from .config_manager import config
from .pcd_manager import PointCloudManger

if TYPE_CHECKING:
    from ..view.gui import GUI



class PointController:
    '''
    Controller for managing point interactions in the GUI.
    This class handles the state and behavior of points in the point cloud,
    '''
    
    def __init__(self):
        self.view: GUI
        self.pcd_manager: PointCloudManger
        self.points : List[Point3D] = [] 
        self.active_point_id = -1  # -1 means zero bboxes
    
    def set_view(self, view: "GUI") -> None:
        self.view = view
    
    def has_active_point(self) -> bool:
        """
        Check if there is an active point.
        This method checks if the `point` attribute is set to a valid Point3D object.   
        
        Returns:
            bool: True if there is an active point, False otherwise.
        """
        return 0 <= self.active_point_id < len(self.points)
    
    def reset(self) -> None:
        '''
        Reset the point controller to its initial state.
        This method clears the active point and resets the points list.
        '''
        
        self.deselect_point()
        self.set_points([])
    
    def deselect_point(self) -> None:
        '''
        Deselect the currently active point.
        This method sets the active point ID to -1, indicating no active point.
        It also updates the view and resets the mode to navigation.
        '''
        
        self.active_point_id = -1
        self.update_all()
        self.view.status_manager.set_mode(Mode.NAVIGATION)
        
        
    def set_points(self, points: List[Point3D]) -> None:
        '''
        Set the points in the point controller.     
        
        Args:
            points (List[Point3D]): A list of Point3D objects to set as the points.
        ''' 
        self.points = points
        self.deselect_point()
        self.update_label_list()
        
        
    
    def update_all(self) -> None:
        #self.update_z_dial()
        #self.update_curr_class()
        #self.update_label_list()
        #self.view.update_bbox_stats(self.get_active_bbox())
        pass

    # @has_active_bbox_decorator
    # def update_z_dial(self) -> None:
    #     self.view.dial_bbox_z_rotation.blockSignals(True)  # To brake signal loop
    #     self.view.dial_bbox_z_rotation.setValue(int(self.get_active_bbox().get_z_rotation()))  # type: ignore
    #     self.view.dial_bbox_z_rotation.blockSignals(False)

    # def update_curr_class(self) -> None:
    #     if self.has_active_bbox():
    #         self.view.current_class_dropdown.setCurrentText(
    #             self.get_active_bbox().classname  # type: ignore
    #         )
    #     else:
    #         self.view.controller.pcd_manager.populate_class_dropdown()

    # def update_label_list(self) -> None:
    #     """Updates the list of drawn labels and highlights the active label.

    #     Should be always called if the bounding boxes changed.
    #     :return: None
    #     """
    #     self.view.label_list.blockSignals(True)  # To brake signal loop
    #     self.view.label_list.clear()
    #     for bbox in self.bboxes:
    #         self.view.label_list.addItem(bbox.get_classname())
    #     if self.has_active_bbox():
    #         self.view.label_list.setCurrentRow(self.active_bbox_id)
    #         current_item = self.view.label_list.currentItem()
    #         if current_item:
    #             current_item.setSelected(True)
    #     self.view.label_list.blockSignals(False)

    def assign_point_label_in_active_box(self) -> None:
        box = self.get_active_bbox()
        if box is not None:
            self.pcd_manager.assign_point_label_in_box(box)
            if config.getboolean("USER_INTERFACE", "delete_box_after_assign"):
                self.delete_current_bbox()

    
    def update_label_list(self) -> None:
        """
        Updates the list of drawn labels and highlights the active label.

        Should be always called if the bounding boxes changed.
        :return: None
        """
        
        pass
        
        # self.view.label_list.blockSignals(True)  # To brake signal loop
        # self.view.label_list.clear()
        # for point in self.points:
        #     self.view.label_list.addItem(point.get_classname())
        
        # if self.has_active_bbox():
        #     self.view.label_list.setCurrentRow(self.active_bbox_id)
        #     current_item = self.view.label_list.currentItem()
        #     if current_item:
        #         current_item.setSelected(True)
        # self.view.label_list.blockSignals(False)
    
    