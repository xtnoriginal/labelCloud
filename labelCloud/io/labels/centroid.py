import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Union

from ...model import BBox, Point
from . import BaseLabelFormat, abs2rel_rotation, rel2abs_rotation

from .config import LabelConfig

class CentroidFormat(BaseLabelFormat):
    FILE_ENDING = ".json"

    def export_labels(self, labels: List[Union[BBox, Point]], pcd_path: Path) -> None:
        data: Dict[str, Any] = {}
        # Header
        data["folder"] = pcd_path.parent.name
        data["filename"] = pcd_path.name
        data["path"] = str(pcd_path)
        data["annotator"] = LabelConfig().get_user_name()

        # Labels
        data["objects"] = []
        for label in labels:
            obj: Dict[str, Any] = {}
            obj["name"] = label.get_classname()

            if isinstance(label, BBox):  # <-- save as bbox
                obj["centroid"] = {
                    str(axis): self.round_dec(val)
                    for axis, val in zip(["x", "y", "z"], label.get_center())
                }
                obj["dimensions"] = {
                    str(dim): self.round_dec(val)
                    for dim, val in zip(
                        ["length", "width", "height"], label.get_dimensions()
                    )
                }
                conv_rotations = label.get_rotations()
                if self.relative_rotation:
                    conv_rotations = map(abs2rel_rotation, conv_rotations)

                obj["rotations"] = {
                    str(axis): self.round_dec(angle)
                    for axis, angle in zip(["x", "y", "z"], conv_rotations)
                }

            elif isinstance(label, Point):  # <-- save as single point
                obj["centroid"] = {
                    str(axis): self.round_dec(val)
                    for axis, val in zip(["x", "y", "z"], label.get_coords())
                }
                # no dimensions or rotations for points

            data["objects"].append(obj)

        # Save to JSON
        label_path = self.save_label_to_file(pcd_path, data)
        logging.info(
            f"Exported {len(labels)} labels to {label_path} "
            f"in {self.__class__.__name__} formatting!"
        )




    def import_labels(self, pcd_path: Path) -> List[Union[BBox, Point]]:
        labels = []

        label_path = self.label_folder.joinpath(pcd_path.stem + self.FILE_ENDING)
        if label_path.is_file():
            with label_path.open("r") as read_file:
                data = json.load(read_file)

            for label in data["objects"]:
                if "dimensions" in label:  # <-- BBox case
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

                else:  # <-- Point case
                    x = label["centroid"]["x"]
                    y = label["centroid"]["y"]
                    z = label["centroid"]["z"]
                    point = Point((x, y, z))
                    point.set_classname(label["name"])
                    labels.append(point)

            logging.info(
                "Imported %s labels from %s." % (len(data["objects"]), label_path)
            )
        return labels
