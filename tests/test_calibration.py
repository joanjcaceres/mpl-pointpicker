import matplotlib.pyplot as plt
import numpy as np
import pytest

from mpl_pointpicker import PointPicker
from test_picker import click, key


def references(picker, points=((10, 50), (90, 50), (50, 80), (50, 20))):
    picker.calibrate()
    for point in points:
        click(picker, *point)
    return picker._calibration


def test_linear_calibration_recovers_values_and_roundtrips(tmp_path):
    image = np.zeros((101, 101))
    picker = PointPicker.from_image(image, use_widgets=False)
    calibration = references(picker)
    calibration.apply({"X1": "0", "X2": "2", "Y1": "10", "Y2": "40"})
    assert picker._calibration is None
    np.testing.assert_allclose(picker._image.get_extent(), [-0.2625, 2.2625, -0.25, 50.25])
    # Pixel (50, 50) corresponds to (1, 25) after affine calibration.
    click(picker, 1, 25)
    np.testing.assert_allclose(picker.xy, [[1, 25]])
    picker.tag_point(0, (0, 1), 0.2)
    output = tmp_path / "calibrated.yaml"
    picker.save_yaml(output, x_scale=1000)
    _, ax = plt.subplots()
    ax.imshow(image, origin="upper")
    loaded = PointPicker.load_yaml(ax, output)
    np.testing.assert_allclose(loaded.xy, [[1000, 25]])
    extent = picker._image.get_extent()
    np.testing.assert_allclose(
        loaded._image.get_extent(), [extent[0] * 1000, extent[1] * 1000, *extent[2:]]
    )
    output2 = tmp_path / "again.yaml"
    loaded.save_yaml(output2)
    _, ax2 = plt.subplots()
    reloaded = PointPicker.load_yaml(ax2, output2)
    np.testing.assert_allclose(reloaded.xy, loaded.xy)


def test_inverted_axes_and_pixel_origin():
    picker = PointPicker.from_image(np.zeros((101, 101)), use_widgets=False)
    assert picker.ax.get_ylim()[0] > picker.ax.get_ylim()[1]
    calibration = references(picker)
    calibration.apply({"X1": "2", "X2": "0", "Y1": "40", "Y2": "10"})
    assert picker.ax.get_xlim()[0] > picker.ax.get_xlim()[1]
    assert picker.ax.get_ylim()[0] > picker.ax.get_ylim()[1]
    click(picker, 1, 25)
    np.testing.assert_allclose(picker.xy, [[1, 25]])


def test_cancel_and_preconditions():
    picker = PointPicker.from_image(np.zeros((100, 100)), use_widgets=False)
    extent = list(picker._image.get_extent())
    picker.calibrate()
    click(picker, 10, 10)
    key(picker, "escape")
    assert picker._calibration is None
    assert list(picker._image.get_extent()) == extent
    assert len(picker.ax.lines) == 0
    click(picker, 20, 30)
    with pytest.raises(ValueError, match="before adding"):
        picker.calibrate()
    _, ax = plt.subplots()
    with pytest.raises(ValueError, match="requires an image"):
        PointPicker(ax).calibrate()


@pytest.mark.parametrize(
    "values",
    [
        {"X1": "1", "X2": "1", "Y1": "0", "Y2": "1"},
        {"X1": "nan", "X2": "2", "Y1": "0", "Y2": "1"},
    ],
)
def test_invalid_values_do_not_change_image(values):
    picker = PointPicker.from_image(np.zeros((101, 101)), use_widgets=False)
    old = list(picker._image.get_extent())
    calibration = references(picker)
    with pytest.raises(ValueError):
        calibration.apply(values)
    assert list(picker._image.get_extent()) == old
    calibration.cancel()


def test_coincident_reference_positions_are_rejected():
    picker = PointPicker.from_image(np.zeros((101, 101)), use_widgets=False)
    calibration = references(picker, ((10, 20), (10, 60), (20, 20), (20, 80)))
    with pytest.raises(ValueError, match="distinct reference"):
        calibration.apply({"X1": "0", "X2": "1", "Y1": "0", "Y2": "1"})


def test_png_and_jpg_paths(tmp_path):
    image = np.zeros((20, 30, 3), dtype=np.uint8)
    for extension in ("png", "jpg"):
        path = tmp_path / f"image.{extension}"
        plt.imsave(path, image)
        picker = PointPicker.from_image(path, use_widgets=False)
        click(picker, 10, 10)
        np.testing.assert_allclose(picker.xy, [[10, 10]])


@pytest.mark.parametrize("image", [np.empty((0, 0)), np.zeros((2, 2, 2)), np.zeros(10)])
def test_invalid_images(image):
    with pytest.raises(ValueError):
        PointPicker.from_image(image)
