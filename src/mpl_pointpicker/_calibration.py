from __future__ import annotations

import math

from ._forms import Form


class Calibration:
    """Collect reference clicks without blocking the figure's event loop."""

    names = ("X1", "X2", "Y1", "Y2")

    def __init__(self, picker):
        self.picker = picker
        self.references = []
        self.markers = []
        self.form = None

    def update_title(self):
        name = self.names[len(self.references)]
        self.picker.ax.set_title(f"Calibration: click {name} reference (Esc cancels)", fontsize=10)
        self.picker.ax.figure.canvas.draw_idle()

    def on_press(self, event):
        if (
            event.inaxes is not self.picker.ax
            or event.button != 1
            or self.picker._toolbar_active()
            or self.form is not None
            or event.xdata is None
            or event.ydata is None
        ):
            return
        self.references.append((float(event.xdata), float(event.ydata)))
        (marker,) = self.picker.ax.plot([event.xdata], [event.ydata], "b+", markersize=10)
        self.markers.append(marker)
        if len(self.references) == 4:
            self.picker.ax.set_title("Calibration: enter the four known axis values", fontsize=10)
            self.form = Form(
                self.picker,
                "Known axis values (linear axes)",
                dict.fromkeys(self.names, ""),
                self.apply,
                self.cancel,
            )
        else:
            self.update_title()

    def apply(self, values):
        numbers = [float(values[name]) for name in self.names]
        if not all(math.isfinite(value) for value in numbers):
            raise ValueError("Reference values must be finite")
        x1, x2, y1, y2 = numbers
        px1, px2 = self.references[0][0], self.references[1][0]
        py1, py2 = self.references[2][1], self.references[3][1]
        if px1 == px2 or py1 == py2 or x1 == x2 or y1 == y2:
            raise ValueError("Each axis needs distinct reference positions and values")
        sx, sy = (x2 - x1) / (px2 - px1), (y2 - y1) / (py2 - py1)
        old = self.picker._image.get_extent()
        extent = [
            x1 + (old[0] - px1) * sx,
            x1 + (old[1] - px1) * sx,
            y1 + (old[2] - py1) * sy,
            y1 + (old[3] - py1) * sy,
        ]
        if not all(math.isfinite(value) for value in extent):
            raise ValueError("Calibration produced nonfinite bounds; use wider references")
        self.picker._image.set_extent(extent)
        self.picker.ax.set_xlim(extent[:2])
        self.picker.ax.set_ylim(extent[2:])
        self.picker.ax.set_aspect("auto")
        self.picker._calibration_metadata = {"kind": "linear", "extent": extent}
        self.cancel()

    def cancel(self):
        if self.form is not None:
            self.form.close()
        for marker in self.markers:
            marker.remove()
        self.markers.clear()
        self.picker._calibration = None
        self.picker._update_title()
