from __future__ import annotations

import math
from pathlib import Path

import yaml
from typing import Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np

from ._tagui import BaseTagUI, create_tag_ui

Label = str | tuple[int, int]
PointDict = dict[Label, list[tuple[float, float] | tuple[float, float, float | None]]]


class PointPicker:
    """Interactive point picker for matplotlib axes (cross‑platform friendly).

    Works with any content in the axes: images, plots, scatter plots, etc.

    Modes (switch with keyboard)
    ---------------------------
    | Key | Mode    | Click action                                |
    |-----|---------|---------------------------------------------|
    | **a** or **Esc** | **Add**    | Left‑click on axes → add point        |
    | **m** | **Move**   | Left‑click–drag a point → move          |
    | **d** | **Delete** | Left‑click on a point → delete          |
    | **t** | **Tag**    | Left‑click on point → assign label via prompt   |
    | **i** | **Inspect** | Left‑click on point → show label info (non-blocking) |

    In Jupyter, enable ``%matplotlib widget`` before creating the figure.

    Other behavior
    --------------
    • In axis-lock mode, the vertical guide follows the cursor until the first point.
    • While the Matplotlib toolbar is in *zoom* or *pan* mode, clicks are **ignored**.
    • Pick radius can be tuned via *pick_radius* (in display pixels).
    • Works with multiple images/plots in the same axes.
    • Use save_yaml("file.yaml") and load_yaml(ax, "file.yaml") to save/load data.

    Example
    -------
    >>> fig, ax = plt.subplots()
    >>> ax.imshow(img1, alpha=0.7)
    >>> ax.contour(img2)
    >>> picker = PointPicker(ax)
    >>> plt.show()          # interact with a/m/d/t keys + left clicks
    >>> picker.save_yaml('my_points.yaml')
    >>> x_coords, y_coords = picker.get_coordinates()
    """

    def __init__(
        self,
        ax: plt.Axes,
        use_widgets: bool = True,
        *,
        pick_radius: int = 6,
        axis_lock: bool = False,
    ):
        if not math.isfinite(pick_radius) or pick_radius <= 0:
            raise ValueError("pick_radius must be positive and finite")
        self.ax = ax
        self.pick_radius = pick_radius
        self._image = None
        self._image_extent = None
        self._calibration_metadata = None
        self._calibration = None
        self._disconnected = False

        # Tagging UI (ipywidgets when available, fallback to matplotlib controls)
        self._prefer_widgets = bool(use_widgets)
        self._form_host = None
        if self._prefer_widgets:
            # Widget callbacks have no cell output area in JupyterLab. Display
            # a persistent host now, while constructing the picker in a cell.
            from ._forms import _notebook_widgets

            notebook = _notebook_widgets()
            if notebook:
                widgets, display = notebook
                self._form_host = widgets.VBox()
                display(self._form_host)
        self._tag_ui: BaseTagUI = create_tag_ui(self, prefer_widgets=self._prefer_widgets)

        # Axis‑lock configuration
        self.axis_lock = axis_lock
        self._fixed_x: Optional[float] = None  # Locked x for current column
        self._vline: Optional[plt.Line2D] = None  # Vertical guide line artist
        self.labels: list[Label | None] = []  # label metadata
        self._current_label: Label | None = None
        self.sigmas: list[Optional[float]] = []  # per-point uncertainty (None = unset)
        self._current_sigma: Optional[float] = None  # last used sigma value

        # Data containers: store points as an N×2 NumPy array
        self.points: np.ndarray = np.empty((0, 2))
        self._markers: list[plt.Line2D] = []

        # Interaction state
        self.mode: str = "add"  # 'add' | 'move' | 'delete' | 'tag' | 'inspect'
        self._selected_idx: Optional[int] = None  # index of point currently dragged

        # Connect canvas events
        canvas = ax.figure.canvas
        self._cids: list[int] = [
            canvas.mpl_connect("button_press_event", self._on_press),
            canvas.mpl_connect("button_release_event", self._on_release),
            canvas.mpl_connect("motion_notify_event", self._on_motion),
            canvas.mpl_connect("key_press_event", self._on_key),
            canvas.mpl_connect("close_event", lambda event: self.disconnect()),
        ]

        self._update_title()

    # ------------------------------------------------------------------
    def _set_marker_color(self, idx: int):
        """Apply marker color according to label/sigma availability."""
        if idx < 0 or idx >= len(self._markers):
            return
        lab = self.labels[idx] if idx < len(self.labels) else None
        sigma = self.sigmas[idx] if idx < len(self.sigmas) else None
        if lab is None:
            color = "r"
        else:
            color = "g" if sigma is not None else "orange"
        marker = self._markers[idx]
        marker.set_markerfacecolor(color)
        marker.set_markeredgecolor(color)

    # ------------------------------------------------------------------
    # Tagging helpers
    # ------------------------------------------------------------------
    def _tag_defaults_for(self, idx: int) -> Tuple[Label | None, Optional[float]]:
        current_label = self.labels[idx] if idx < len(self.labels) else None
        sigma = self.sigmas[idx] if idx < len(self.sigmas) else None
        if current_label is None:
            current_label = self._current_label
        if sigma is None:
            sigma = self._current_sigma
        return current_label, sigma

    def _apply_tag(self, idx: int, i: int, j: int, sigma: Optional[float]) -> None:
        """Compatibility helper for transition tags."""
        self.tag_point(idx, (i, j), sigma)

    @staticmethod
    def _validate_label(label: Label | None) -> Label | None:
        if label is None:
            return None
        if isinstance(label, str) and label.strip():
            return label
        if isinstance(label, (tuple, list, np.ndarray)) and len(label) == 2:
            if all(isinstance(i, (int, np.integer)) and not isinstance(i, bool) for i in label):
                return (int(label[0]), int(label[1]))
        raise ValueError("Use a nonempty text label or a pair of integers")

    def tag_point(self, idx: int, label: Label | None, sigma: float | None = None) -> None:
        """Assign a series name or transition; sigma is uncertainty in y units."""
        if idx < 0 or idx >= len(self.points):
            raise ValueError(f"Invalid point index {idx}")
        if sigma is not None and (not math.isfinite(sigma) or sigma <= 0):
            raise ValueError("sigma must be positive when provided")
        label = self._validate_label(label)
        self.labels[idx] = label
        self._current_label = label
        self.sigmas[idx] = sigma
        self._current_sigma = sigma
        self._set_marker_color(idx)
        self.ax.figure.canvas.draw_idle()

    def _remove_tag(self, idx: int) -> None:
        if idx < 0 or idx >= len(self.points):
            return
        self.labels[idx] = None
        self.sigmas[idx] = None
        self._set_marker_color(idx)
        self.ax.figure.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Terminal input helper for tagging
    # ------------------------------------------------------------------
    def _inspect_point(self, idx: int):
        """
        Non-blocking inspection of point labels - just prints info to console.
        """
        current_label = self.labels[idx]
        x, y = self.points[idx]

        if current_label is not None:
            print(
                f"Point #{idx} at ({x:.2f}, {y:.2f}) -> labeled as {ascii(current_label)}, sigma={self.sigmas[idx]}"
            )
        else:
            print(f"Point #{idx} at ({x:.2f}, {y:.2f}) -> unlabeled")

    # Note: _terminal_tag_input removed to avoid blocking matplotlib interaction
    # Tag mode now delegates to an environment-specific UI (ipywidgets or matplotlib)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _toolbar_active(self) -> bool:
        """Return *True* if toolbar's *pan/zoom* tool is active."""
        tb = getattr(self.ax.figure.canvas, "toolbar", None)
        return bool(getattr(tb, "mode", ""))

    # -- Mouse press ----------------------------------------------------
    def _on_press(self, event):
        if self._calibration is not None:
            self._calibration.on_press(event)
            return
        if event.inaxes is not self.ax or event.button != 1 or self._toolbar_active():
            return  # ignore right‑clicks and toolbar interactions

        idx = self._index_near(event)

        if self.mode == "add":
            if idx is None:
                # Regular add
                self._add_point(float(event.xdata), float(event.ydata))
            else:
                # Clicked an existing point → (re)activate its column when axis_lock is on
                if self.axis_lock:
                    self._fixed_x = self.points[idx, 0]
                    self._update_vline(self._fixed_x)
                    print(f"Column at x={self._fixed_x:.2f} re-selected; add more points.")

        elif self.mode == "delete":
            if idx is not None:
                self._remove_point(idx)

        elif self.mode == "move":
            if idx is not None:
                self._selected_idx = idx  # start dragging

        elif self.mode == "tag":
            if idx is not None:
                self._tag_point(idx)

        elif self.mode == "inspect":
            if idx is not None:
                self._inspect_point(idx)

    # -- Mouse motion ---------------------------------------------------
    def _on_motion(self, event):
        if self._calibration is not None:
            return
        # Show guide line only *before* first click in a column
        if (
            self.axis_lock
            and self.mode == "add"
            and self._fixed_x is None
            and event.inaxes is self.ax
            and event.xdata is not None
        ):
            self._update_vline(float(event.xdata))

        # Drag‑to‑move logic
        if self.mode != "move" or self._selected_idx is None:
            return
        if event.inaxes is not self.ax or event.ydata is None:
            return

        idx = self._selected_idx
        # In axis‑lock: allow vertical motion only (keep x constant)
        if self.axis_lock:
            x = self.points[idx, 0]
            y = float(event.ydata)
        else:
            if event.xdata is None:
                return
            x, y = float(event.xdata), float(event.ydata)

        # Update data + marker
        self.points[idx, :] = [x, y]
        m = self._markers[idx]
        m.set_data([x], [y])
        self.ax.figure.canvas.draw_idle()

    # -- Mouse release --------------------------------------------------
    def _on_release(self, _event):
        self._selected_idx = None  # stop dragging

    # -- Key presses ----------------------------------------------------
    def _on_key(self, event):
        if self._calibration is not None:
            if event.key == "escape":
                self._calibration.cancel()
            return
        if self._tag_ui.is_editing and event.key != "escape":
            return
        # Track previous mode to close tagging UI when switching away from tag mode
        old_mode = self.mode

        if event.key in {"a", "escape"}:
            self.mode = "add"
        elif event.key == "m":
            self.mode = "move"
        elif event.key == "d":
            self.mode = "delete"
        elif event.key == "t":
            self.mode = "tag"
        elif event.key == "i":
            self.mode = "inspect"
        elif event.key == "n" and self.axis_lock:
            # Finish current column
            self._fixed_x = None
            if self._vline is not None:
                self._vline.remove()
                self._vline = None

        # Close tagging UI when leaving tag mode
        if old_mode == "tag" and self.mode != "tag":
            if self._tag_ui is not None:
                self._tag_ui.close()

        self._update_title()

    # ------------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------------
    def _update_title(self):
        self.ax.set_title(
            f"Mode: {self.mode} | a:Add  m:Move  d:Delete  t:Tag  i:Inspect\n"
            + ("Esc:Add | n:New column" if self.axis_lock else "Esc:Add"),
            fontsize=8,
        )
        self.ax.figure.canvas.draw_idle()

    # -- Guide line helper ------------------------------------------------
    def _update_vline(self, x: float):
        """Draw or update the vertical guide line (axis‑lock mode)."""
        if self._vline is None:
            self._vline = self.ax.axvline(x, linestyle=":", color="k", alpha=0.5)
        else:
            self._vline.set_xdata([x, x])
        self.ax.figure.canvas.draw_idle()

    def _add_point(self, x: float, y: float):
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError("Point coordinates must be finite")
        # Axis‑lock: lock x at first click in a column
        if self.axis_lock:
            if self._fixed_x is None:
                self._fixed_x = x
                self._update_vline(self._fixed_x)
            x = self._fixed_x

        # Append point
        self.points = np.vstack([self.points, [x, y]])
        # Newly added points start without label or sigma; tagging is explicit
        self.labels.append(None)
        self.sigmas.append(None)

        (marker,) = self.ax.plot(x, y, "ro", markersize=6)
        self._markers.append(marker)
        self._set_marker_color(len(self._markers) - 1)
        self.ax.figure.canvas.draw_idle()
        print(f"Added -> ({x:.2f}, {y:.2f})")

    def _remove_point(self, idx: int):
        # Remove point from array and marker
        self.points = np.delete(self.points, idx, axis=0)
        self._markers[idx].remove()
        self._markers.pop(idx)
        self.labels.pop(idx)
        self.sigmas.pop(idx)
        self.ax.figure.canvas.draw_idle()
        print(f"Deleted point #{idx}")

    def _tag_point(self, idx: int):
        if idx < 0 or idx >= len(self.points):
            return
        self._tag_ui.show(idx)

    def _index_near(self, event) -> Optional[int]:
        # Return None if no points are stored
        if self.points.shape[0] == 0:
            return None
        # Transform all points to display coordinates
        display = self.ax.transData.transform(self.points)
        # Compute distances to mouse event
        d = np.hypot(display[:, 0] - event.x, display[:, 1] - event.y)
        idx = int(np.argmin(d))
        # Only return an index if within pick radius
        return idx if d[idx] <= self.pick_radius else None

    # ------------------------------------------------------------------
    # Public utilities
    # ------------------------------------------------------------------
    def disconnect(self):
        if self._disconnected:
            return
        self._disconnected = True
        if self._calibration is not None:
            self._calibration.cancel()
        # Close any active tagging UI
        if self._tag_ui is not None:
            self._tag_ui.close()

        if self._vline is not None:
            self._vline.remove()
            self._vline = None
        canvas = self.ax.figure.canvas
        for cid in self._cids:
            canvas.mpl_disconnect(cid)
        if self._form_host is not None:
            self._form_host.close()

    @property
    def xy(self) -> np.ndarray:
        return self.points

    @property
    def x_coords(self) -> np.ndarray:
        return self.points[:, 0] if self.points.size else np.array([])

    @property
    def y_coords(self) -> np.ndarray:
        return self.points[:, 1] if self.points.size else np.array([])

    def get_coordinates(self) -> tuple[np.ndarray, np.ndarray]:
        """Returns a tuple with (x_coords, y_coords)."""
        return self.x_coords, self.y_coords

    # ------------------------------------------------------------------
    # Tagging ---------------------------------------------------------
    # ------------------------------------------------------------------
    def set_current_label(self, label: Label | None):
        """
        Set the default series or transition suggested by the tagging form.
        New points remain unlabeled until explicitly tagged.
        """
        self._current_label = self._validate_label(label)

    def set_current_sigma(self, sigma: float | None):
        """Define the sigma pre-filled when tagging new points. Use None to clear."""
        if sigma is not None and (not math.isfinite(sigma) or sigma <= 0):
            raise ValueError(f"sigma must be positive when provided, got {sigma}")
        self._current_sigma = sigma

    def summary(self):
        """Prints a summary of the selected points."""
        n = self.points.shape[0]
        print(f"Selected points: {n}")
        if n:
            print(f"X coords: {self.x_coords}")
            print(f"Y coords: {self.y_coords}")
        else:
            print("No points selected.")

    def view_points(self):
        """Print all points, including unlabelled points."""
        print("Idx | Label | x | y | sigma")
        for idx, ((x, y), label, sigma) in enumerate(zip(self.points, self.labels, self.sigmas)):
            print(f"{idx} | {ascii(label)} | {x:g} | {y:g} | {sigma}")

    def to_transition_data(self, *, include_sigma: bool = False, x_scale: float = 1.0) -> PointDict:
        """Return only integer-pair transition groups, suitable for a fitter."""
        return {
            key: values
            for key, values in self.to_dict(include_sigma=include_sigma, x_scale=x_scale).items()
            if isinstance(key, tuple)
        }

    @staticmethod
    def _validate_scale(x_scale: float) -> None:
        if not math.isfinite(x_scale) or x_scale <= 0:
            raise ValueError("x_scale must be positive and finite")

    def to_dict(self, *, include_sigma: bool = True, x_scale: float = 1.0) -> PointDict:
        """Group tagged points by series name or (i, j); omit unlabelled points."""
        self._validate_scale(x_scale)
        data: PointDict = {}
        for (x, y), label, sigma in zip(self.points, self.labels, self.sigmas):
            if label is None:
                continue
            key = self._validate_label(label)
            entry = (float(x) * x_scale, float(y))
            if include_sigma:
                entry += (float(sigma) if sigma is not None else None,)
            data.setdefault(key, []).append(entry)
        return data

    def save_yaml(self, filename="pointpicker_data.yaml", *, include_sigma=True, x_scale=1.0):
        """Save final coordinates, labels and calibration; does not embed the image."""
        grouped = self.to_dict(include_sigma=include_sigma, x_scale=x_scale)
        metadata = {
            "format_version": "2.0",
            "axis_lock": self.axis_lock,
            "x_scale": float(x_scale),
            "include_sigma": include_sigma,
            "description": "mpl-pointpicker data export",
        }
        if self._calibration_metadata is not None:
            # Record the image placement in the same final units as the points.
            calibration = dict(self._calibration_metadata)
            calibration["extent"] = [
                float(v) * x_scale if i < 2 else float(v)
                for i, v in enumerate(calibration["extent"])
            ]
            metadata["calibration"] = calibration
        elif self._image is not None:
            metadata["image_extent"] = [
                float(v) * x_scale if i < 2 else float(v)
                for i, v in enumerate(self._image.get_extent())
            ]
        unlabeled = []
        for (x, y), label, sigma in zip(self.points, self.labels, self.sigmas):
            if label is None:
                entry = [float(x) * x_scale, float(y)]
                if include_sigma:
                    entry.append(float(sigma) if sigma is not None else None)
                unlabeled.append(entry)
        payload = {
            "metadata": metadata,
            "data": {
                f"{k[0]},{k[1]}": [list(p) for p in v]
                for k, v in grouped.items()
                if isinstance(k, tuple)
            },
            "series": {k: [list(p) for p in v] for k, v in grouped.items() if isinstance(k, str)},
            "unlabeled": unlabeled,
        }
        with open(filename, "w", encoding="utf-8") as stream:
            yaml.safe_dump(payload, stream, sort_keys=False, allow_unicode=True)

    @classmethod
    def load_yaml(cls, ax, filename="pointpicker_data.yaml"):
        """Read legacy/v2 YAML onto supplied axes; the image is supplied separately."""
        with open(filename, encoding="utf-8") as stream:
            payload = yaml.safe_load(stream)
        if not isinstance(payload, dict):
            raise ValueError("Expected a pointpicker YAML mapping")
        metadata = payload.get("metadata", {})
        if str(metadata.get("format_version", "1.0")) not in {"1.0", "2.0"}:
            raise ValueError("Unsupported pointpicker format_version")
        # Validate everything before adding artists or callbacks.
        records = []
        for section in ("data", "series", "unlabeled"):
            groups = payload.get(section, [] if section == "unlabeled" else {})
            entries = [(None, groups)] if section == "unlabeled" else groups.items()
            for key, points in entries:
                if section == "data":
                    try:
                        parts = str(key).split(",")
                        if len(parts) != 2:
                            raise ValueError()
                        label = tuple(int(i) for i in parts)
                    except (TypeError, ValueError) as exc:
                        raise ValueError(f"Invalid transition key: {key!r}") from exc
                else:
                    label = cls._validate_label(key)
                for point in points:
                    if len(point) not in (2, 3):
                        raise ValueError(f"Invalid point format: {point!r}")
                    x, y = map(float, point[:2])
                    sigma = float(point[2]) if len(point) == 3 and point[2] is not None else None
                    if not (math.isfinite(x) and math.isfinite(y)):
                        raise ValueError("Point coordinates must be finite")
                    if sigma is not None and (not math.isfinite(sigma) or sigma <= 0):
                        raise ValueError("sigma must be positive and finite")
                    records.append((x, y, label, sigma))
        picker = cls(ax, axis_lock=bool(metadata.get("axis_lock", False)))
        # Do not apply axis locking while restoring independent saved points.
        picker.points = np.array([[x, y] for x, y, _, _ in records], dtype=float).reshape(-1, 2)
        picker.labels = [label for _, _, label, _ in records]
        picker.sigmas = [sigma for _, _, _, sigma in records]
        for idx, (x, y) in enumerate(picker.points):
            (marker,) = ax.plot([x], [y], "o", markersize=6)
            picker._markers.append(marker)
            picker._set_marker_color(idx)
        calibration = metadata.get("calibration")
        extent = calibration["extent"] if calibration else metadata.get("image_extent")
        if ax.images:
            picker._image = ax.images[-1]
            if extent is not None:
                picker._image.set_extent(extent)
                ax.set_xlim(extent[:2])
                ax.set_ylim(extent[2:])
                if calibration:
                    ax.set_aspect("auto")
            picker._image_extent = list(picker._image.get_extent())
        picker._calibration_metadata = calibration
        ax.figure.canvas.draw_idle()
        return picker

    @classmethod
    def from_image(cls, image, *, ax=None, **kwargs):
        """Open a PNG/JPG path or grayscale/RGB(A) array in pixel coordinates.

        Call ``calibrate()`` before adding points to recover graph units.
        In a desktop script call ``plt.show()`` to enter the event loop.
        """
        pixels = plt.imread(Path(image)) if isinstance(image, (str, Path)) else np.asarray(image)
        if pixels.ndim not in (2, 3) or (pixels.ndim == 3 and pixels.shape[2] not in (3, 4)):
            raise ValueError("Expected a grayscale, RGB or RGBA image")
        if not pixels.size:
            raise ValueError("The image must not be empty")
        if ax is None:
            _, ax = plt.subplots()
        artist = ax.imshow(pixels, origin="upper", cmap="gray")
        picker = cls(ax, **kwargs)
        picker._image = artist
        picker._image_extent = list(artist.get_extent())
        return picker

    def calibrate(self):
        """Start four-reference linear calibration. Escape cancels it.

        Select two x references followed by two y references, then enter their
        values in the form. Calibration is allowed only before adding points.
        """
        if self._disconnected:
            raise ValueError("This picker has been disconnected")
        if self._image is None:
            raise ValueError("Calibration requires an image; use PointPicker.from_image")
        if self.points.size:
            raise ValueError("Calibrate before adding points; start a new picker to recalibrate")
        if self._calibration is not None:
            self._calibration.cancel()
        self._tag_ui.close()
        from ._calibration import Calibration

        self._calibration = Calibration(self)
        self._calibration.update_title()
