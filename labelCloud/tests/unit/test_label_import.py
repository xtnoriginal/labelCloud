import os
from pathlib import Path
import pytest

from labelCloud.control.label_manager import LabelManager
from labelCloud.model.point import Point
from labelCloud.model.bbox import BBox


# ------------------------------
# Fixtures for test label files
# ------------------------------

@pytest.fixture
def label_centroid():
    return """{"folder": "pointclouds", "filename": "test.ply", "path": "pointclouds/test.ply",
                "objects": [{"name": "cart", "centroid": { "x": -0.186338, "y": -0.241696, "z": 0.054818},
                "dimensions": {"length": 0.80014, "width": 0.512493, "height": 0.186055},
                "rotations": {"x": 0, "y": 0, "z": 1.616616} } ] }"""


@pytest.fixture
def label_vertices():
    return """{"folder": "pointclouds", "filename": "test.ply", "path": "pointclouds/test.ply", "objects": [
                {"name": "cart", "vertices": [[-0.245235,-0.465784,0.548944], [-0.597706,-0.630144,0.160035],
                [-0.117064,-0.406017,-0.370295], [0.235407,-0.241657,0.018614], [-0.308628,-0.329838,0.548944],
                [-0.661099,-0.494198,0.160035], [-0.180457,-0.270071,-0.370295], [0.172014,-0.105711,0.018614]]}]}"""


@pytest.fixture
def label_kitti():
    return "cart 0 0 0 0 0 0 0 0.75 0.55 0.15 -0.409794 -0.012696 0.076757 0.436332"


@pytest.fixture
def label_points():
    return """{"folder": "pointclouds", "filename": "test.ply", "path": "pointclouds/test.ply",
                "objects": [{"name": "tree", "point": { "x": 1.23, "y": -0.45, "z": 2.34 } }]}"""


# ------------------------------
# Import tests
# ------------------------------

@pytest.mark.parametrize(
    "label_format, rotation",
    [("centroid_abs", (0, 0, 1.616616)), ("centroid_rel", (0, 0, 92.6252738933211))],
)
def test_centroid_import(label_centroid, tmppath, label_format, rotation):
    with tmppath.joinpath("test.json").open("w") as f:
        f.write(label_centroid)

    label_manager = LabelManager(strategy=label_format, path_to_label_folder=tmppath)
    bounding_boxes = label_manager.import_labels(Path("test.ply"))
    bbox = bounding_boxes[0]

    assert isinstance(bbox, BBox)
    assert bbox.get_classname() == "cart"
    assert bbox.get_center() == (-0.186338, -0.241696, 0.054818)
    assert bbox.get_dimensions() == (0.80014, 0.512493, 0.186055)
    assert bbox.get_rotations() == rotation


def test_vertices_import(label_vertices, tmppath):
    with tmppath.joinpath("test.json").open("w") as f:
        f.write(label_vertices)

    label_manager = LabelManager(strategy="vertices", path_to_label_folder=tmppath)
    bounding_boxes = label_manager.import_labels(Path("test.ply"))
    bbox = bounding_boxes[0]

    assert isinstance(bbox, BBox)
    assert bbox.get_classname() == "cart"
    assert bbox.get_center() == pytest.approx((-0.212846, -0.3679275, 0.0893245))
    assert bbox.get_dimensions() == pytest.approx((0.75, 0.55, 0.15))
    assert bbox.get_rotations() == pytest.approx((270, 45, 25))


def test_kitti_import(label_kitti, tmppath):
    with open(os.path.join(tmppath, "test.txt"), "w") as f:
        f.write(label_kitti)

    label_manager = LabelManager(strategy="kitti_untransformed", path_to_label_folder=tmppath)
    bounding_boxes = label_manager.import_labels(Path("test.txt"))
    bbox = bounding_boxes[0]

    assert isinstance(bbox, BBox)
    assert bbox.get_classname() == "cart"
    assert bbox.get_center() == (-0.409794, -0.012696, 0.076757)
    assert bbox.get_dimensions() == (0.15, 0.55, 0.75)
    assert bbox.get_rotations() == pytest.approx((0, 0, 25))


def test_points_import(label_points, tmppath):
    with tmppath.joinpath("test.json").open("w") as f:
        f.write(label_points)

    label_manager = LabelManager(strategy="points", path_to_label_folder=tmppath)
    points = label_manager.import_labels(Path("test.ply"))
    point = points[0]

    assert isinstance(point, Point)
    assert point.get_classname() == "tree"
    assert point.get_coords() == (1.23, -0.45, 2.34)


# ------------------------------
# Export + round-trip tests
# ------------------------------

@pytest.mark.parametrize("strategy", ["centroid_abs", "vertices", "kitti_untransformed", "points"])
def test_roundtrip_export_import(strategy, tmppath):
    """Ensure export → import yields equivalent objects."""

    # Create dummy objects for each strategy
    if strategy == "points":
        obj = Point("tree", (1.23, -0.45, 2.34))
    else:
        obj = BBox("cart", center=(0, 0, 0), dimensions=(1, 2, 3), rotations=(0, 0, 0))

    label_manager = LabelManager(strategy=strategy, path_to_label_folder=tmppath)

    # Export
    label_manager.export_labels(Path("test.ply"), [obj])
    exported_files = list(tmppath.iterdir())
    assert exported_files, "No file exported"

    # Import back
    imported = label_manager.import_labels(Path("test.ply"))
    assert len(imported) == 1

    new_obj = imported[0]
    assert new_obj.get_classname() == obj.get_classname()

    if strategy == "points":
        assert new_obj.get_coords() == obj.get_coords()
    else:
        assert new_obj.get_center() == obj.get_center()
        assert new_obj.get_dimensions() == obj.get_dimensions()
