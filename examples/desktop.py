"""Run ``python examples/desktop.py [image.png]`` with a GUI backend."""

from pathlib import Path
import sys

import matplotlib.pyplot as plt

from mpl_pointpicker import PointPicker


def main():
    image = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("demo.png")
    picker = PointPicker.from_image(image, use_widgets=False)
    picker.ax.figure.set_size_inches(10, 7)
    picker.calibrate()
    print("Click two x references, then two y references, and enter their values.")
    print("After calibration: a add, t tag, m move, d delete, i inspect; close when finished.")
    plt.show()
    picker.view_points()
    picker.save_yaml("picked-points.yaml")
    print("Transition data:", picker.to_transition_data(include_sigma=True))


if __name__ == "__main__":
    main()
