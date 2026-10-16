"""Run from outside the checkout, against an installed wheel or sdist."""

import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

import mpl_pointpicker


def main():
    assert mpl_pointpicker.__version__ == "0.1.0"
    picker = mpl_pointpicker.PointPicker.from_image(np.zeros((20, 20)), use_widgets=False)
    picker._add_point(4, 5)
    picker.tag_point(0, (0, 1), 0.1)
    assert picker.to_transition_data() == {(0, 1): [(4.0, 5.0)]}
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "points.yaml"
        picker.save_yaml(output)
        _, ax = plt.subplots()
        restored = mpl_pointpicker.PointPicker.load_yaml(ax, output)
        assert restored.to_dict() == {(0, 1): [(4.0, 5.0, 0.1)]}
        restored.disconnect()
    picker.disconnect()
    plt.close("all")


if __name__ == "__main__":
    main()
