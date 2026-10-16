# Simple desktop test

From the repository root:

```bash
.venv/bin/python examples/manual_desktop.py
```

The script draws three ordinary Matplotlib curves with 200 samples each and
attaches `PointPicker(ax, axis_lock=True)`. It opens the usual `plt.show()` event
loop. There is no heatmap, input file or autosave timer.

Use `a` to add, `m` to move, `d` to delete, `t` to tag, `i` to inspect and `n`
for a new x column. Turn off the toolbar's zoom/pan tool before selecting points.

Close the window to save all points, including unlabeled ones, in
`examples/simple-points.yaml` and print the grouped dictionary in the terminal.
Running and closing the example again replaces that output file.
