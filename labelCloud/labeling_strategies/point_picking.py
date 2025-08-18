import logging
from typing import TYPE_CHECKING, List, Optional, cast

import numpy as np

from . import BaseLabelingStrategy
from ..control.config_manager import config
from ..definitions import Mode, Point3D
from ..model import Point
from ..utils import math3d as math3d
from ..utils import oglhelper as ogl
import open3d as o3d


class PickingPointStrategy(BaseLabelingStrategy):
    POINTS_NEEDED = 1
    PREVIEW = True

    def __init__(self, view: "GUI") -> None:
        super().__init__(view)
        logging.info("Enabled drawing mode.")
        self.view.status_manager.update_status(
            "Please pick the location for the bounding box front center.",
            mode=Mode.DRAWING,
        )
        self.point_1: Optional[Point3D] = None 
        self.tmp_p1: Optional[Point3D] = None
        self.bbox_z_rotation: float = 0
        self.preview_color = (1, 1, 0, 1)
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(view.controller.pcd_manager.pointcloud.points)

        # Make sure the point cloud is not empty
        assert len(pcd.points) > 0, "Point cloud is empty"

        # Initialize KDTree
        self.pcd_tree  = o3d.geometry.KDTreeFlann()
        self.pcd_tree.set_geometry(pcd)

    def register_point(self, new_point: Point3D) -> None:
        print("register_point called with:", new_point)
        if not self.tmp_p1 == None :
            k, idx, dist= self.pcd_tree.search_knn_vector_3d(new_point,1);
            if idx:
                self.point_1 = self.view.controller.pcd_manager.pointcloud.points[idx[0]]
                self.points_registered += 1
                                                                         
    def register_tmp_point(self, new_tmp_point: Point3D) -> None:
        self.tmp_p1 = new_tmp_point

    def register_scrolling(self, distance: float) -> None:
        self.bbox_z_rotation += distance // 30

    def draw_preview(self) -> None:  
        if not self.tmp_p1 == None :
            k, idx, dist= self.pcd_tree.search_knn_vector_3d(self.tmp_p1,1);
            if idx:
                ogl.draw_points([self.view.controller.pcd_manager.pointcloud.points[idx[0]]], color=self.preview_color)
                                                
    def get_point(self) -> Point3D: 
        assert self.point_1 is not None
        return Point(self.point_1)
    
    def get_selected_point(self):
        return self.point_1

    def reset(self) -> None:
        super().reset()
        self.tmp_p1 = None
        self.view.button_pick_point.setChecked(False)
    