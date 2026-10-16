# mpl-pointpicker

Attach directly to your original Matplotlib axes: zoom into the underlying data,
select fine details, and keep x fixed while picking a column. No intermediate
screenshots or cropped image files are needed. PNG/JPG digitization is also
available as a separate workflow. Recover
coordinates as NumPy arrays or dictionaries grouped by a series name or a
transition `(i, j)`, with optional uncertainty in y.

Python 3.11 or newer. MIT licensed. This package was extracted from
[SCCircuits](https://github.com/joanjcaceres/sccircuits); it does not depend on
SCCircuits, SciPy or SymPy.

## Install

Install from PyPI (Python 3.11 or newer):

```bash
python -m pip install mpl-pointpicker
```

For an interactive figure embedded in Jupyter Notebook, JupyterLab or VS Code:

```bash
python -m pip install "mpl-pointpicker[notebook]"
```

For a local notebook with a separate desktop window, install `ipykernel` in the
same Python environment and use the native backend shown in the
[three-curve notebook](examples/window.ipynb). That workflow uses Matplotlib
forms and does not need the embedded-widget extra.

For a reproducible installation, pin `mpl-pointpicker==0.1.0`. The fixed GitHub
release remains available as an alternative:

```bash
python -m pip install "mpl-pointpicker @ git+https://github.com/joanjcaceres/mpl-pointpicker.git@v0.1.0"
```

The [GitHub release](https://github.com/joanjcaceres/mpl-pointpicker/releases/tag/v0.1.0)
also includes the published wheel and source archive.

## Start with your original Matplotlib data

Pass the same `ax` used to display your measurement data. Existing image arrays,
`pcolormesh` heatmaps, curves, contours and overlays stay in the figure. Their
coordinates are already defined, so **no calibration is needed**.

```python
import numpy as np
import matplotlib.pyplot as plt
from mpl_pointpicker import PointPicker

# Replace this synthetic dataset with your original x, y and measured signal.
x = np.linspace(0, 1, 2001)
y = np.linspace(2, 8, 801)
ridge = 4 + np.cos(2 * np.pi * x)
signal = np.exp(-((y[:, None] - ridge[None, :]) / 0.025) ** 2)

fig, ax = plt.subplots()
ax.pcolormesh(x, y, signal, shading="auto")
ax.set(xlabel="Control parameter", ylabel="Frequency (GHz)")
picker = PointPicker(ax, axis_lock=True)
plt.show()

data = picker.to_transition_data(include_sigma=True)
```

Use the **Matplotlib zoom/pan toolbar** to inspect a small region, then deactivate
the toolbar tool before selecting points. The picker continues to use the
original data coordinates at every zoom level. It does not turn your axes into
a screenshot. Resolution is determined by the original data, rather than a
previously saved image's screen resolution.

With `axis_lock=True`, the first point fixes the current column's x coordinate.
Later points use that exact x even after zooming or panning; dragging a point
changes only y. Press **n** for a new column, or click an existing point in Add
mode to reuse its x. The lock operates in data units and does not require
recalibration when the view changes.

Try the [axes and zoom notebook](examples/axes.ipynb) or run
`python examples/desktop.py` to explore the original synthetic data interactively.

## Manual desktop session

For a minimal desktop test with three ordinary curves, run:

```bash
.venv/bin/python examples/manual_desktop.py
```

The example uses 200 samples per curve and keeps x fixed. Closing the window
saves the points to `examples/simple-points.yaml`. See the
[short guide](examples/MANUAL_TEST.md) for shortcuts.

## Start with an image file

```python
import matplotlib.pyplot as plt
from mpl_pointpicker import PointPicker

picker = PointPicker.from_image("graph.png")
picker.calibrate()  # Omit this line to keep pixel coordinates.
plt.show()          # Desktop event loop; interact before closing the window.

data = picker.to_dict()
picker.save_yaml("picked-points.yaml")
```

Keep the picker variable alive for the duration of the interaction. In desktop
scripts, choose an interactive Matplotlib backend. macOS and standard Windows
Python installations usually provide one. On Linux, install your distribution's
Tk support or a Qt binding such as PySide6, then select `TkAgg` or `QtAgg` before
importing `matplotlib.pyplot`. The noninteractive `Agg` backend can export data
and run tests but cannot receive mouse clicks.

### Linear image calibration

Calibration must happen **before adding points**. The graph must have straight,
horizontal/vertical linear axes; logarithmic axes and rotated photographs are
outside this version's scope.

1. Call `picker.calibrate()`.
2. Click two positions with known **x** values, in order X1, X2. Their y positions do not matter.
3. Click two positions with known **y** values, in order Y1, Y2. Their x positions do not matter.
4. Enter those four axis values in the form and choose **Apply**.

Click precisely on tick marks or other known reference locations. Each pair
needs distinct positions and values. Descending values are supported. **Esc**
cancels calibration; the Cancel button is also available in the value form.
The image and future points now share the calibrated coordinates. Calibration
does not estimate uncertainty: sigma is entered separately in the final y units.

## Use in Jupyter

For a **separate desktop window on macOS**, open the minimal
[three-curve notebook](examples/window.ipynb) and select the repository's
`.venv/bin/python` kernel (install `ipykernel` in that environment if needed).
It uses `%matplotlib osx` and `use_widgets=False`; the notebook remains available
while you select points in the native window. Run the later cells to inspect
and save the points. This requires a local kernel with access to your desktop.
Restart the kernel before switching from another backend.

For an embedded interactive figure, use the widget workflow below.

Run this before creating figures:

```python
%matplotlib widget
from mpl_pointpicker import PointPicker

picker = PointPicker.from_image("graph.png")
picker.calibrate()
```

Complete calibration and point selection in the displayed figure. Then run a
**separate cell** to retrieve `picker.to_dict()` or save YAML. Notebook code does
not block while waiting for mouse input. `%matplotlib inline` produces a static
image and is unsuitable for picking. Use the notebook extra above, and restart
the kernel after installing it. `use_widgets=False` uses Matplotlib forms even
inside a notebook.

For the image-file workflow, try the guided
[image calibration notebook](examples/quickstart.ipynb), or run
`python examples/desktop.py graph.png`. Choose the axes workflow above whenever
you have the original measurement arrays or a prepared Matplotlib figure.

## Select and edit

Focus the figure before using shortcuts:

| Key | Action |
| --- | --- |
| `a` / `Esc` | Add mode: click to add a point |
| `m` | Move mode: drag a point |
| `d` | Delete mode: click a point |
| `t` | Tag mode: click a point, choose Transition or Series, enter a label and optional sigma |
| `i` | Inspect mode: click a point to print its label and coordinates |
| `n` | Start a new x column when `axis_lock=True` |

Pan and zoom toolbar operations do not add or edit points. In the tag form use
**Action → Remove tag → Apply** to remove a label. **Esc** closes the form.
Typing in a form does not trigger editing shortcuts. Markers are red when
unlabeled, orange when labeled, and green when labeled with sigma.

For an existing plot or an image array with coordinates already set:

```python
fig, ax = plt.subplots()
ax.plot([0, 1, 2], [1, 4, 2])
picker = PointPicker(ax, axis_lock=False, pick_radius=6)
plt.show()
```

`axis_lock=True` keeps each column's x value fixed, including during dragging.
Press `n` to choose another column, or click an existing point in Add mode to
reuse its column.

## Get results

```python
picker.xy                         # N × 2 NumPy array, including unlabeled points
x, y = picker.get_coordinates()   # Also available as x_coords and y_coords
picker.view_points()              # Table with labels and sigma
picker.tag_point(0, (0, 1), 0.02) # Programmatic transition tag
picker.tag_point(1, "series A")   # Programmatic text label
picker.to_dict()
# {(0, 1): [(0.25, 5.10, 0.02)], "series A": [(0.50, 3.20, None)]}
picker.to_transition_data()
# {(0, 1): [(0.25, 5.10)]}
```

`to_dict(include_sigma=True, x_scale=1.0)` includes text and transition groups.
`to_transition_data(include_sigma=False, x_scale=1.0)` returns only integer-pair
labels, compatible with SCCircuits `TransitionFitter`. Both omit unlabeled
points. `include_sigma=False` returns pairs `(x, y)`; otherwise entries are
`(x, y, sigma)`, where unset sigma is `None`.

`set_current_label(label)` and `set_current_sigma(sigma)` set suggestions for the
tag form; new points remain unlabeled until explicitly tagged. `sigma` must be
positive and finite when supplied. `x_scale` must be positive and finite and
multiplies exported x values only. Transition order is preserved; the fitter
can normalize `(i, j)` if needed.

## Save and resume

```python
picker.save_yaml("picked-points.yaml", include_sigma=True, x_scale=1.0)

fig, ax = plt.subplots()
ax.imshow(plt.imread("graph.png"), origin="upper", cmap="gray")
restored = PointPicker.load_yaml(ax, "picked-points.yaml")
plt.show()
```

Provide the original image separately; it is not embedded in YAML. When an
image is already on the supplied axes, loading restores its saved placement.
Without an image, the points still load onto the supplied axes. Coordinates are
stored in their final units, so calibration and `x_scale` are **not reapplied**.

The loader accepts the original SCCircuits YAML format. Format 2.0 preserves
`data` for transition groups and `unlabeled` for untagged points, adds `series`
for text labels, and records image calibration under `metadata`. A series named
`"0,1"` remains distinct from transition `(0, 1)`. SCCircuits'
`TransitionFitter.load_from_yaml()` can read the `data` section unchanged.
Groups retain point order internally; roundtripping YAML may regroup points by
label, so numeric point indices are session-local.

Call `picker.disconnect()` to release event handlers and forms without closing
the figure. Closing the window also disconnects automatically. Disconnecting
does not discard points or prevent export.

## Development and releases

```bash
python -m pip install -e ".[dev,notebook]"
python -m pytest
ruff check src tests examples
python -m build
python -m twine check dist/*
```

CI tests supported Python environments, builds both distributions and checks
installation outside the source tree on Linux, macOS and Windows. PyPI
publishing is manual and disabled until `PYPI_PUBLISH_ENABLED` is set to `true`
after configuring a Trusted Publisher; see [RELEASING.md](RELEASING.md).

## Attribution

The original PointPicker was developed by Joan Caceres in SCCircuits. Extraction
started from SCCircuits commit `c5e051a4dddc43b93a3cff5a8e3e80c698c00afd`.
The original MIT copyright notice is preserved in [LICENSE](LICENSE).
