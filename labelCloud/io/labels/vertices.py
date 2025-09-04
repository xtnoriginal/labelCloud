import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Union 

import numpy as np

from . import BaseLabelFormat
from ...definitions import Point3D
from ...model import BBox, Point
from ...utils import math3d

from .config import LabelConfig


class VerticesFormat(BaseLabelFormat):
    FILE_ENDING = ".json"
    
    from ...model.point import Point

    def import_labels(self, pcd_path: Path) -> List[Union[BBox, Point]]:
        labels = []

        label_path = self.label_folder.joinpath(pcd_path.stem + self.FILE_ENDING)
        if label_path.is_file():
            with label_path.open("r") as read_file:
                data = json.load(read_file)

            for label in data["objects"]:
                if "vertices" in label:  # BBox
                    vertices = label["vertices"]

                    centroid: Point3D = tuple(
                        np.add(np.subtract(vertices[4], vertices[2]) / 2, vertices[2])
                    )

                    length = math3d.vector_length(np.subtract(vertices[0], vertices[3]))
                    width  = math3d.vector_length(np.subtract(vertices[0], vertices[1]))
                    height = math3d.vector_length(np.subtract(vertices[0], vertices[4]))

                    rotations = math3d.vertices2rotations(vertices, centroid)

                    bbox = BBox(*centroid, length, width, height)
                    bbox.set_rotations(*rotations)
                    bbox.set_classname(label["name"])
                    labels.append(bbox)

                elif "point" in label:  # Point
                    x, y, z = label["point"]
                    point_idx = label["point_idx"]
                    point = Point((x, y, z), point_idx)
                    point.set_classname(label["name"])
                    labels.append(point)

            logging.info(
                "Imported %s labels from %s." % (len(data["objects"]), label_path)
            )
        return labels

    def export_labels(self, labels: List[Union[BBox, Point]], pcd_path: Path) -> None:
        data: Dict[str, Any] = dict()
        data["folder"] = pcd_path.parent.name
        data["filename"] = pcd_path.name
        data["path"] = str(pcd_path)
        data["annotator"] = LabelConfig().get_user_name()

        data["objects"] = []
        for label in labels:
            obj: Dict[str, Any] = dict()
            obj["name"] = label.get_classname()

            if isinstance(label, BBox):
                obj["vertices"] = self.round_dec(label.get_vertices().tolist())
            elif isinstance(label, Point):
                obj["point"] = self.round_dec(label.get_coords())
                obj["point_idx"] =  label.point_id

            data["objects"].append(obj)
        

        self.export_labels_horse_extension(labels, pcd_path)

        label_path = self.save_label_to_file(pcd_path, data)
        logging.info(
            f"Exported {len(labels)} labels to {label_path} "
            f"in {self.__class__.__name__} formatting!"
        )


    def export_labels_horse_extension(self, labels: List[Union[BBox, Point]], pcd_path: Path):
        data: Dict[str, Any] = dict()
        meta : Dict[str, Any] = dict()
        meta["folder"] = pcd_path.parent.name
        meta["filename"] = pcd_path.name
        meta["path"] = str(pcd_path)
        meta["annotator"] = LabelConfig().get_user_name()

        data["metadata"] = meta
        data["keypoints"] = []

        for label in labels:
            obj: Dict[str, Any] = dict()
            label.get_classname()

            if isinstance(label, BBox):
                continue
            elif isinstance(label, Point):
                obj[label.get_classname()] = self.round_dec(label.get_coords())
                obj["PCD_point_index"] = label.point_id

            data["keypoints"].append(obj)

        label_path = self.save_label_to_file(pcd_path, data, file_name_ext="mpi_horse_ext")
        logging.info(
            f"Exported {len(labels)} labels to {label_path} "
            f"in {self.__class__.__name__} formatting!"
        )
