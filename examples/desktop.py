"""Explore original Matplotlib data, or optionally digitize an image file."""

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

from mpl_pointpicker import PointPicker


def main():
    if len(sys.argv) > 1:
        picker = PointPicker.from_image(Path(sys.argv[1]), use_widgets=False, axis_lock=True)
        picker.calibrate()
        print("Click two x references, then two y references, and enter their values.")
    else:
        x = np.linspace(0, 1, 2001)
        y = np.linspace(2, 8, 801)
        ridge = 4 + np.cos(2 * np.pi * x)
        signal = np.exp(-(((y[:, None] - ridge[None, :]) / 0.025) ** 2))
        fig, ax = plt.subplots()
        ax.pcolormesh(x, y, signal, shading="auto")
        ax.set(xlabel="Control parameter", ylabel="Frequency (GHz)")
        picker = PointPicker(ax, use_widgets=False, axis_lock=True)
        print("Original measurement arrays: zoom/pan freely; no image calibration needed.")
    picker.ax.figure.set_size_inches(10, 7)
    print("The first point locks x. Press n for a new column, or reuse an existing point's x.")
    print("a add, t tag, m move, d delete, i inspect; close when finished.")
    plt.show()
    picker.view_points()
    picker.save_yaml("picked-points.yaml")
    print("Transition data:", picker.to_transition_data(include_sigma=True))


if __name__ == "__main__":
    main()
