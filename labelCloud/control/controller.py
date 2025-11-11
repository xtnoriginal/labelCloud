import logging
from typing import Optional

import numpy as np
from PyQt5 import QtGui,QtCore
from PyQt5.QtCore import QPoint
from PyQt5.QtCore import Qt as Keys

from ..definitions import BBOX_SIDES, Colors, Context, LabelingMode
from ..io.labels.config import LabelConfig
from ..utils import oglhelper
from ..view.gui import GUI
from .alignmode import AlignMode
from .bbox_controller import BoundingBoxController
from .pick_point_controller import PickPointController
from .pick_flow_controller import PickFlowController
from .config_manager import config
from .drawing_manager import DrawingManager
from .pcd_manager import PointCloudManger
from .unified_annotation_controller import UnifiedAnnotationController


from ..model.bbox import BBox
from ..model.point import Point

from ..definitions import Mode

class Controller:
    MOVEMENT_THRESHOLD = 0.1

    def __init__(self) -> None:
        """Initializes all controllers and managers."""
        self.view: "GUI"
        self.pcd_manager = PointCloudManger()
        self.unified_annotation_controller = UnifiedAnnotationController() # Added unified controller to manage both bbox and points
        self.bbox_controller = BoundingBoxController()
        self.pick_point_controller = PickPointController()
        self.pick_flow_controller = PickFlowController()

        # Drawing states
        self.drawing_mode = DrawingManager(self.bbox_controller,self.pick_point_controller, self.pick_flow_controller)
        self.align_mode = AlignMode(self.pcd_manager)

        # Control states
        self.curr_cursor_pos: Optional[QPoint] = None  # updated by mouse movement
        self.last_cursor_pos: Optional[QPoint] = None  # updated by mouse click
        self.ctrl_pressed = False
        self.scroll_mode = False  # to enable the side-pulling

        # Correction states
        self.side_mode = False
        self.selected_side: Optional[str] = None

    def startup(self, view: "GUI") -> None:
        """Sets the view in all controllers and dependent modules; Loads labels from file."""
        self.view = view
        self.bbox_controller.set_view(self.view)
        self.pick_point_controller.set_view(self.view)
        self.pick_flow_controller.set_view(self.view)
        self.pcd_manager.set_view(self.view)
        self.drawing_mode.set_view(self.view)
        self.align_mode.set_view(self.view)
        self.view.gl_widget.set_unified_annotation_controller(self.unified_annotation_controller)
        self.bbox_controller.pcd_manager = self.pcd_manager
        self.bbox_controller.unified_annotation_controller = self.unified_annotation_controller
        self.pick_point_controller.unified_annotation_controller = self.unified_annotation_controller
        self.pick_point_controller.pcd_manager = self.pcd_manager
        self.unified_annotation_controller.set_view(self.view)
        self.pick_flow_controller.unified_annotation_controller = self.unified_annotation_controller
        self.pick_flow_controller.pcd_manager = self.pcd_manager
    

        # Read labels from folders
        self.pcd_manager.read_pointcloud_folder()
        self.next_pcd(save=False)

    def loop_gui(self) -> None:
        """Function collection called during each event loop iteration."""
        self.set_crosshair()
        self.set_selected_side()
        self.view.gl_widget.updateGL()

    # POINT CLOUD METHODS
    def next_pcd(self, save: bool = True) -> None:
        if save:
            self.save()
        if self.pcd_manager.pcds_left():
            previous_unified_bbox_point = self.unified_annotation_controller.items
            self.pcd_manager.get_next_pcd()
            self.reset()

            self.unified_annotation_controller.set_items(self.pcd_manager.get_labels_from_file())
            self.update_curr_class()

            if not self.unified_annotation_controller.items and config.getboolean(
                "LABEL", "propagate_labels"
            ):
                self.bbox_controller.set_bboxes(previous_unified_bbox_point)
            self.unified_annotation_controller.set_active_item(0)
           
        else:
            self.view.update_progress(len(self.pcd_manager.pcds))
            self.view.button_next_pcd.setEnabled(False)

    def prev_pcd(self) -> None:
        self.save()
        if self.pcd_manager.current_id > 0:
            self.pcd_manager.get_prev_pcd()
            self.reset()
            # self.bbox_controller.set_bboxes(self.pcd_manager.get_labels_from_file())
            # self.bbox_controller.set_active_bbox(0)
            self.unified_annotation_controller.set_items(self.pcd_manager.get_labels_from_file())
            self.unified_annotation_controller.set_active_item(0)
            self.update_curr_class()

    def custom_pcd(self, custom: int) -> None:
        self.save()
        self.pcd_manager.get_custom_pcd(custom)
        self.reset()
        self.unified_annotation_controller.set_items(self.pcd_manager.get_labels_from_file())
        self.update_curr_class()

    # CONTROL METHODS
    def save(self) -> None:
        """Saves all bounding boxes and optionally segmentation labels in the label file."""
        self.pcd_manager.save_labels_into_file(self.unified_annotation_controller.items)

        if LabelConfig().type == LabelingMode.SEMANTIC_SEGMENTATION:
            assert self.pcd_manager.pointcloud is not None
            self.pcd_manager.pointcloud.save_segmentation_labels()

    def reset(self) -> None:
        """Resets the controllers and bounding boxes from the current screen."""
        self.unified_annotation_controller.reset()
        self.drawing_mode.reset()
        self.align_mode.reset()
    

    def set_active(self, index: int) -> None:
        """Sets the active bounding box or point based on the index from the label list."""
        if self.unified_annotation_controller.has_active_item():
            self.unified_annotation_controller.set_active_item(index)

            self.update_all()
            

            item = self.unified_annotation_controller.get_active_item()

            if isinstance(item, Point):
                self.pcd_manager.pointcloud.focus_on_point(item.point)  # type: ignoreq
        
            self.view.status_manager.update_status(
                f"Selected: {self.unified_annotation_controller.get_active_item().get_classname()}",
                mode=Mode.CORRECTION
            )
        else:
            logging.warning("No active item to set.")

    # CORRECTION METHODS
    def set_crosshair(self) -> None:
        """Sets the crosshair position in the glWidget to the current cursor position."""
        if self.curr_cursor_pos:
            self.view.gl_widget.crosshair_col = Colors.GREEN.value
            self.view.gl_widget.crosshair_pos = (
                self.curr_cursor_pos.x(),
                self.curr_cursor_pos.y(),
            )

    def set_selected_side(self) -> None:
        """Sets the currently hovered bounding box side in the glWidget."""
        if (
            (not self.side_mode)
            and self.curr_cursor_pos
            and self.unified_annotation_controller.has_active_item()
            and (not self.scroll_mode
            )
            and isinstance( self.unified_annotation_controller.get_active_item(), BBox)
        ):
            _, self.selected_side = oglhelper.get_intersected_sides(
                self.curr_cursor_pos.x(),
                self.curr_cursor_pos.y(),
                self.unified_annotation_controller.get_active_item(),  # type: ignore
                self.view.gl_widget.modelview,
                self.view.gl_widget.projection,
            )
        if (
            self.selected_side
            and (not self.ctrl_pressed)
            and self.unified_annotation_controller.has_active_item()
            and isinstance( self.unified_annotation_controller.get_active_item(), BBox)
        ):
            self.view.gl_widget.crosshair_col = Colors.RED.value
            side_vertices = self.unified_annotation_controller.get_active_item().get_vertices()  # type: ignore
            self.view.gl_widget.selected_side_vertices = side_vertices[
                BBOX_SIDES[self.selected_side]
            ]
            self.view.status_manager.set_message(
                "Scroll to change the bounding box dimension.",
                context=Context.SIDE_HOVERED,
            )
        else:
            self.view.gl_widget.selected_side_vertices = np.array([])
            self.view.status_manager.clear_message(Context.SIDE_HOVERED)

    # EVENT PROCESSING
    def mouse_clicked(self, a0: QtGui.QMouseEvent) -> None:
        """Triggers actions when the user clicks the mouse."""
        self.last_cursor_pos = a0.pos()

        if self.drawing_mode.drawing_strategy.__class__.__name__== "PickingPointStrategy" :
            if self.drawing_mode.is_active()and self.ctrl_pressed:
                self.drawing_mode.register_point(a0.x(), a0.y(), correction=True)
        
        elif (
            self.drawing_mode.is_active()
            and (a0.buttons() & Keys.LeftButton)
            and (not self.ctrl_pressed)
        ):
            self.drawing_mode.register_point(a0.x(), a0.y(), correction=True)

        elif self.align_mode.is_active and (not self.ctrl_pressed):
            self.align_mode.register_point(
                self.view.gl_widget.get_world_coords(a0.x(), a0.y(), correction=False)
            )

        elif self.selected_side:
            self.side_mode = True
    
    def select_item_by_ray(self, x: int, y: int) -> None:
        intersected_bbox_id = oglhelper.get_intersected_bboxes(
            x,
            y,
            self.unified_annotation_controller.items,
            self.view.gl_widget.modelview,
            self.view.gl_widget.projection,
        )
        if intersected_bbox_id is not None:
            self.unified_annotation_controller.set_active_item(intersected_bbox_id)
            logging.info("Selected bounding box or point %s." % intersected_bbox_id)

    def mouse_double_clicked(self, a0: QtGui.QMouseEvent) -> None:
        """Triggers actions when the user double clicks the mouse."""
        self.select_item_by_ray(a0.x(), a0.y())

    def mouse_move_event(self, a0: QtGui.QMouseEvent) -> None:
        """Triggers actions when the user moves the mouse."""
        self.curr_cursor_pos = a0.pos()  # Updates the current mouse cursor position

        # Methods that use absolute cursor position
        if self.drawing_mode.is_active() and (not self.ctrl_pressed):
            self.drawing_mode.register_point(
                a0.x(), a0.y(), correction=True, is_temporary=True
            )

        elif self.align_mode.is_active and (not self.ctrl_pressed):
            self.align_mode.register_tmp_point(
                self.view.gl_widget.get_world_coords(a0.x(), a0.y(), correction=False)
            )

        if self.last_cursor_pos:
            dx = (
                self.last_cursor_pos.x() - a0.x()
            ) / 5  # Calculate relative movement from last click position
            dy = (self.last_cursor_pos.y() - a0.y()) / 5

            if (
                self.ctrl_pressed
                and (not self.drawing_mode.is_active())
                and (not self.align_mode.is_active)
            ):
                if a0.buttons() & Keys.LeftButton:  # bbox rotation
                    item = self.unified_annotation_controller.get_active_item()
                    if isinstance(item, BBox): # The code might crush because item can be a BBox or Point some logic is needed: solution just add this line
                        self.bbox_controller.rotate_with_mouse(-dx, -dy)
                elif a0.buttons() & Keys.RightButton:  # bbox translation
                    new_center = self.view.gl_widget.get_world_coords(
                        a0.x(), a0.y(), correction=True
                    )
                    self.bbox_controller.set_center(*new_center)  # absolute positioning
            else:
                if a0.buttons() & Keys.LeftButton:  # pcd rotation
                    self.pcd_manager.rotate_around_x(dy)
                    self.pcd_manager.rotate_around_z(dx)
                elif a0.buttons() & Keys.RightButton:  # pcd translation
                    self.pcd_manager.translate_along_x(dx)
                    self.pcd_manager.translate_along_y(dy)

            # Reset scroll locks of "side scrolling" for significant cursor movements
            if dx > Controller.MOVEMENT_THRESHOLD or dy > Controller.MOVEMENT_THRESHOLD:
                if self.side_mode:
                    self.side_mode = False
                else:
                    self.scroll_mode = False
        self.last_cursor_pos = a0.pos()

    def mouse_scroll_event(self, a0: QtGui.QWheelEvent) -> None:
        """Triggers actions when the user scrolls the mouse wheel."""
        if self.selected_side:
            self.side_mode = True

        
        if self.drawing_mode.is_active() and self.drawing_mode.drawing_strategy.__class__.__name__== "PickingPointStrategy":
            self.pcd_manager.zoom_into(a0.angleDelta().y())
            self.scroll_mode = True
        elif (
            self.drawing_mode.is_active()
            and (not self.ctrl_pressed)
            and self.drawing_mode.drawing_strategy is not None
        ):
            self.drawing_mode.drawing_strategy.register_scrolling(a0.angleDelta().y())
        elif self.side_mode and self.unified_annotation_controller.has_active_item():
            item = self.unified_annotation_controller.get_active_item()
            if isinstance(item, BBox):
                self.unified_annotation_controller.get_active_item().change_side(  # type: ignore
                    self.selected_side, -a0.angleDelta().y() / 4000  # type: ignore
                )  # ToDo implement method
            else:
                pass
        else:
            self.pcd_manager.zoom_into(a0.angleDelta().y())
            self.scroll_mode = True
 
    def key_press_event(self, a0: QtGui.QKeyEvent) -> None:
        """Triggers actions when the user presses a key."""
        controller = self.active_controller()
        
        
        # ----- UNDO / REDO -----
        if (a0.key() == QtCore.Qt.Key_Z) and (a0.modifiers() & QtCore.Qt.ControlModifier): #
            # Ctrl+Z => Undo
            print("Undo last action")
            self.unified_annotation_controller.delete_last_item()
            if self.drawing_mode.drawing_strategy.__class__.__name__== "PickingPointStrategy" and self.drawing_mode.drawing_strategy.pick_flow:
                self.drawing_mode.undo()
            return
        
        # Reset position to intial value
        if a0.key() == Keys.Key_Control:
            self.ctrl_pressed = True
            self.view.status_manager.set_message(
                "Hold right mouse button to translate or left mouse button to rotate "
                "the bounding box.",
                context=Context.CONTROL_PRESSED,
            )
        # Reset point cloud pose to intial rotation and translation
        elif a0.key() in [Keys.Key_P, Keys.Key_Home]:
            self.pcd_manager.reset_transformations()
            logging.info("Reseted position to default.")

        elif a0.key() == Keys.Key_Delete:  # Delete active bbox
            self.unified_annotation_controller.delete_bbox()

        # Save labels to file
        elif a0.key() == Keys.Key_S and self.ctrl_pressed:
            self.save()

        elif a0.key() == Keys.Key_Escape:
            if self.drawing_mode.is_active():
                self.drawing_mode.reset()
                logging.info("Resetted drawn points!")
            elif self.align_mode.is_active:
                self.align_mode.reset()
                logging.info("Resetted selected points!")

        # BBOX MANIPULATION
        # elif a0.key() == Keys.Key_Z:
        #     # z rotate counterclockwise
        #     if isinstance(controller, BoundingBoxController):
        #         self.bbox_controller.rotate_around_z()
        elif a0.key() == Keys.Key_X:
            if isinstance(controller, BoundingBoxController):
                # z rotate clockwise
                self.bbox_controller.rotate_around_z(clockwise=True)
        elif a0.key() == Keys.Key_C:
            if isinstance(controller, BoundingBoxController):
                # y rotate counterclockwise
                self.bbox_controller.rotate_around_y()
        elif a0.key() == Keys.Key_V:
            if isinstance(controller, BoundingBoxController):
                # y rotate clockwise
                controller.rotate_around_y(clockwise=True)
        elif a0.key() == Keys.Key_B:
            if isinstance(controller, BoundingBoxController):
                # x rotate counterclockwise
                self.bbox_controller.rotate_around_x()
        elif a0.key() == Keys.Key_N:
            # x rotate clockwise
            controller.rotate_around_x(clockwise=True)
        elif a0.key() == Keys.Key_W:
            # move backward
            controller.translate_along_y()
        elif a0.key() == Keys.Key_S:
            # move forward
            controller.translate_along_y(forward=True)
        elif a0.key() == Keys.Key_A:
            # move left
            controller.translate_along_x(left=True)
        elif a0.key() == Keys.Key_D:
            # move right
            controller.translate_along_x()
        elif a0.key() == Keys.Key_Q:
            # move up

            controller.translate_along_z()
        elif a0.key() == Keys.Key_E:
            # move down
            controller.translate_along_z(down=True)

        # BBOX Scaling
        elif a0.key() == Keys.Key_I:
            if isinstance(controller, BoundingBoxController):
                # increase length
                self.bbox_controller.scale_along_length()
        elif a0.key() == Keys.Key_O:
            if isinstance(controller, BoundingBoxController):
                self.bbox_controller.scale_along_length(decrease=True)
        elif a0.key() == Keys.Key_K:
            if isinstance(controller, BoundingBoxController):
                # increase width
                self.bbox_controller.scale_along_width()
        elif a0.key() == Keys.Key_L:
            if isinstance(controller, BoundingBoxController):
                # decrease width
                self.bbox_controller.scale_along_width(decrease=True)
        elif a0.key() == Keys.Key_Comma:
            if isinstance(controller,BoundingBoxController):
                # increase height
                self.bbox_controller.scale_along_height()
        elif a0.key() == Keys.Key_Period:

            if isinstance(controller,BoundingBoxController):
                # decrease height
                self.bbox_controller.scale_along_height(decrease=True)

        elif a0.key() in [Keys.Key_R, Keys.Key_Left]:
            # load previous sample
            self.prev_pcd()
        elif a0.key() in [Keys.Key_F, Keys.Key_Right]:
            # load next sample
            self.next_pcd()
        elif a0.key() in [Keys.Key_T, Keys.Key_Up]:
            # select previous bbox
            self.select_relative_bbox(-1)
        elif a0.key() in [Keys.Key_G, Keys.Key_Down]:
            # select previous bbox
            self.select_relative_bbox(1)
        elif a0.key() == Keys.Key_Y:
            # change bbox class to previous available class
            self.select_relative_class(-1)
        elif a0.key() == Keys.Key_H:
            # change bbox class to next available class
            self.select_relative_class(1)
        elif a0.key() in list(range(49, 58)):
            # select bboxes with 1-9 digit keys
            self.unified_annotation_controller.set_active_item(int(a0.key()) - 49)
            self.update_all()

    def select_relative_class(self, step: int):
        if step == 0:
            return
        curr_class = self.unified_annotation_controller.get_active_item().get_classname()  # type: ignore
        new_class = LabelConfig().get_relative_class(curr_class, step)
        self.unified_annotation_controller.get_active_item().set_classname(new_class)  # type: ignore
        self.update_all()  # updates UI in SelectBox

    def select_relative_bbox(self, step: int):
        if step == 0:
            return
        max_id = len(self.unified_annotation_controller.items) - 1
        curr_id = self.unified_annotation_controller.active_index
        new_id = curr_id + step
        corner_case_id = 0 if step > 0 else max_id
        new_id = new_id if new_id in range(max_id + 1) else corner_case_id
        self.unified_annotation_controller.set_active_item(new_id)

    def key_release_event(self, a0: QtGui.QKeyEvent) -> None:
        """Triggers actions when the user releases a key."""
        if a0.key() == Keys.Key_Control:
            self.ctrl_pressed = False
            self.view.status_manager.clear_message(Context.CONTROL_PRESSED)

    def crop_pointcloud_inside_active_bbox(self) -> None:
        item = self.unified_annotation_controller.get_active_item()

        if not isinstance(item, BBox): # Logic not necessary for points
            
            return 
        
        bbox = item


        assert bbox is not None
        assert self.pcd_manager.pointcloud is not None
        points_inside = bbox.is_inside(self.pcd_manager.pointcloud.points)
        pointcloud = self.pcd_manager.pointcloud.get_filtered_pointcloud(points_inside)
        if pointcloud is None:
            logging.warning("No points found inside the box. Ignored.")
            return
        self.view.save_point_cloud_as(pointcloud)


    def set_classname(self, classname: str) -> None:
        """Sets the classname of the active bounding box."""
        if self.unified_annotation_controller.has_active_item():
            self.unified_annotation_controller.get_active_item().set_classname(classname)
        
        self.update_label_list()

    def update_label_list(self) -> None:
        """Updates the list of drawn labels and highlights the active label.

        Should be always called if the bounding boxes changed.
        :return: None
        """
        self.unified_annotation_controller.update_label_list()
    
    def delete_current(self) -> None:
        """Deletes the currently selected bounding box or point."""
        self.unified_annotation_controller.delete_bbox()
        self.update_all() 

    def deselect_label(self) -> None:
        """Deselects the currently selected bounding box or point."""
        self.unified_annotation_controller.deselect_label()
        self.update_all()
        self.view.status_manager.set_mode(Mode.NAVIGATION)

    
    def update_all(self) -> None:
        #self.update_z_dial()
        self.update_curr_class()
        self.update_label_list()
        self.view.update_bbox_stats(self.unified_annotation_controller.get_active_item())


    def update_curr_class(self) -> None:
        if self.unified_annotation_controller.has_active_item():
            self.view.current_class_dropdown.setCurrentText(
                self.unified_annotation_controller.get_active_item().classname  # type: ignore
            )
        else:
            self.view.controller.pcd_manager.populate_class_dropdown()



    def active_controller(self):

        if self.unified_annotation_controller.has_active_item():
            if isinstance(self.unified_annotation_controller.get_active_item(), BBox):
                return self.bbox_controller
            return self.pick_point_controller
        else:
            print("No controller")
            return None

    def translate_along_x(self, left=False):
        controller = self.active_controller() 
        if controller:
            controller.translate_along_x(left=left)

    def translate_along_y(self, forward=False):
        controller = self.active_controller() 
        if controller:
            controller.translate_along_y(forward=forward)

    def translate_along_z(self, down=False):
        controller = self.active_controller() 
        if controller:
            controller.translate_along_z(down=down)

    def skip_label(self): # Used when in pick flow mode to move to next class after picking a point
        #Check if in pick flow mode
        if self.drawing_mode.drawing_strategy.__class__.__name__== "PickingPointStrategy" and self.drawing_mode.drawing_strategy.pick_flow:
            self.drawing_mode.move_to_next_class(skip=True)
