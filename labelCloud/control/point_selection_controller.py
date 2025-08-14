import logging
from typing import TYPE_CHECKING, List, Optional, Tuple

import numpy as np

from ..definitions import Mode
from .config_manager import config
from .pcd_manager import PointCloudManger

if TYPE_CHECKING:
    from ..view.gui import GUI


class PointSelectionController:
    """
    Handles selecting and labeling individual points in a point cloud.
    Supports single-point selection (ray picking), multi-selection (rectangle/lasso),
    and assigning/removing labels.
    """

    def __init__(self) -> None:
        self.view: GUI
        self.pcd_manager: PointCloudManger
        self.selected_points: List[int] = []  # store point indices

    # ----------------
    # INITIALIZATION
    # ----------------
    def set_view(self, view: "GUI") -> None:
        self.view = view

    def set_pcd_manager(self, pcd_manager: PointCloudManger) -> None:
        self.pcd_manager = pcd_manager

    def reset(self) -> None:
        """Clears all selected points."""
        self.selected_points.clear()
        self.update_all()
        self.view.status_manager.set_mode(Mode.NAVIGATION)

    # ----------------
    # SELECTION
    # ----------------
    def select_point_by_ray(self, x: int, y: int) -> None:
        """
        Ray-picks the closest point to the cursor location (x, y) in screen coordinates.
        """
        point_id = self.pcd_manager.get_intersected_point(
            x,
            y,
            self.view.gl_widget.modelview,
            self.view.gl_widget.projection,
        )
        if point_id is not None:
            self.selected_points = [point_id]
            self.update_all()
            logging.info(f"Selected point {point_id}")

    def select_points_by_area(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """
        Selects all points within a screen-space rectangle.
        """
        point_ids = self.pcd_manager.get_points_in_rectangle(x1, y1, x2, y2)
        self.selected_points = point_ids
        self.update_all()
        logging.info(f"Selected {len(point_ids)} points in area.")

    def add_point_to_selection(self, point_id: int) -> None:
        """Adds a point to the current selection without clearing."""
        if point_id not in self.selected_points:
            self.selected_points.append(point_id)
            self.update_all()

    def remove_point_from_selection(self, point_id: int) -> None:
        """Removes a point from the selection."""
        if point_id in self.selected_points:
            self.selected_points.remove(point_id)
            self.update_all()

    def deselect_all(self) -> None:
        self.selected_points.clear()
        self.update_all()

    # ----------------
    # LABELING
    # ----------------
    def label_selected_points(self, class_name: str) -> None:
        """Assigns a class label to all selected points."""
        if not self.selected_points:
            logging.warning("No points selected to label.")
            return
        self.pcd_manager.assign_point_labels(self.selected_points, class_name)
        logging.info(f"Labeled {len(self.selected_points)} points as '{class_name}'")
        if config.getboolean("USER_INTERFACE", "clear_selection_after_label"):
            self.deselect_all()

    # ----------------
    # GUI UPDATES
    # ----------------
    def update_all(self) -> None:
        """Updates the GUI to reflect the current selection."""
        self.update_label_list()
        self.view.update_point_stats(self.selected_points)

    def update_label_list(self) -> None:
        """Updates the label list widget to show selected points and their classes."""
        self.view.label_list.blockSignals(True)
        self.view.label_list.clear()

        for pid in self.selected_points:
            classname = self.pcd_manager.get_point_class(pid)
            self.view.label_list.addItem(f"Point {pid}: {classname}")

        self.view.label_list.blockSignals(False)
