import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from ...model import BBox
from . import BaseLabelFormat, abs2rel_rotation, rel2abs_rotation

from ...model.point import Point


class CentroidFormat(BaseLabelFormat):
    FILE_ENDING = ".json"

    def import_labels(self, pcd_path: Path) -> List[BBox]:
        labels = []
        points = []

        picked_points = []

        label_path = self.label_folder.joinpath(pcd_path.stem + self.FILE_ENDING)
        if label_path.is_file():
            with label_path.open("r") as read_file:
                data = json.load(read_file)

            for label in data["objects"]:
                x = label["centroid"]["x"]
                y = label["centroid"]["y"]
                z = label["centroid"]["z"]
                length = label["dimensions"]["length"]
                width = label["dimensions"]["width"]
                height = label["dimensions"]["height"]
                bbox = BBox(x, y, z, length, width, height)
                rotations = label["rotations"].values()
                if self.relative_rotation:
                    rotations = map(rel2abs_rotation, rotations)
                bbox.set_rotations(*rotations)
                bbox.set_classname(label["name"])
                labels.append(bbox)

            for point in data.get("points", []):
                x = point["x"]
                y = point["y"]
                z = point["z"]
                points.append(Point((x, y, z)))

            logging.info(
                "Imported Boxes %s Points %s labels from %s." % (len(data["objects"]),len(data["points"]), label_path)
            )
        return labels, picked_points

    def export_labels(self, bboxes: List[BBox], points: List[Point],pcd_path: Path) -> None:
        data: Dict[str, Any] = {}
        # Header
        data["folder"] = pcd_path.parent.name
        data["filename"] = pcd_path.name
        data["path"] = str(pcd_path)

        # Labels
        data["objects"] = []
        for bbox in bboxes:
            label: Dict[str, Any] = {}
            label["name"] = bbox.get_classname()
            label["centroid"] = {
                str(axis): self.round_dec(val)
                for axis, val in zip(["x", "y", "z"], bbox.get_center())
            }
            label["dimensions"] = {
                str(dim): self.round_dec(val)
                for dim, val in zip(
                    ["length", "width", "height"], bbox.get_dimensions()
                )
            }
            conv_rotations = bbox.get_rotations()
            if self.relative_rotation:
                conv_rotations = map(abs2rel_rotation, conv_rotations)  # type: ignore

            label["rotations"] = {
                str(axis): self.round_dec(angle)
                for axis, angle in zip(["x", "y", "z"], conv_rotations)
            }
            data["objects"].append(label)


        # Points
        data["points"] = [
            {"x": self.round_dec(p.point[0]), "y": self.round_dec(p.point[1]), "z": self.round_dec(p.point[2]), 'class': p.get_classname()} 
            for p in points
        ]

        # Save to JSON
        label_path = self.save_label_to_file(pcd_path, data)
        logging.info(
            f"Exported {len(bboxes)} labels to {label_path} "
            f"in {self.__class__.__name__} formatting!"
        )

