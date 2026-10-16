"""Small nonblocking forms shared by tagging and calibration."""

from __future__ import annotations

from matplotlib.widgets import Button, RadioButtons, TextBox


def _notebook_widgets():
    try:
        from IPython import get_ipython
        from IPython.display import display
        import ipywidgets as widgets

        shell = get_ipython()
        if shell is not None and hasattr(shell, "kernel"):
            return widgets, display
    except ImportError:
        pass
    return None


class Form:
    """Show a form in notebook widgets or below the Matplotlib axes."""

    def __init__(self, picker, title, fields, submit, cancel, *, choices=None):
        self.picker = picker
        self.submit = submit
        self.cancel = cancel
        self._fields = {}
        self._axes = []
        self._controls = []
        self._box = None
        self._feedback = None
        self._positions = []
        self._layout_engine = None
        self._closed = False
        self._notebook = False
        choices = choices or {}
        notebook = _notebook_widgets() if picker._prefer_widgets else None
        if notebook:
            self._notebook = True
            widgets, display = notebook
            for name, value in fields.items():
                if name in choices:
                    control = widgets.Dropdown(options=choices[name], value=value, description=name)
                else:
                    control = widgets.Text(value=value, description=name)
                    control.continuous_update = True
                self._fields[name] = control
            ok = widgets.Button(description="Apply")
            cancel_button = widgets.Button(description="Cancel")
            self._feedback = widgets.Label()
            ok.on_click(self._submit)
            cancel_button.on_click(lambda event: self.cancel())
            self._box = widgets.VBox(
                [
                    widgets.Label(title),
                    *self._fields.values(),
                    widgets.HBox([ok, cancel_button]),
                    self._feedback,
                ]
            )
            display(self._box)
        else:
            fig = picker.ax.figure
            self._positions = [(ax, ax.get_position().frozen()) for ax in fig.axes]
            self._layout_engine = fig.get_layout_engine()
            if self._layout_engine is not None:
                fig.set_layout_engine(None)
            for ax, position in self._positions:
                ax.set_position(
                    [position.x0, 0.28 + 0.72 * position.y0, position.width, position.height * 0.72]
                )
            self._heading = fig.text(0.08, 0.245, title, fontsize=9)
            self._feedback = fig.text(0.08, 0.015, "", fontsize=8, color="crimson")
            width = 0.82 / len(fields)
            for index, (name, value) in enumerate(fields.items()):
                x = 0.08 + width * index
                if name in choices:
                    field_ax = fig.add_axes([x, 0.11, width - 0.035, 0.115])
                    control = RadioButtons(
                        field_ax, choices[name], active=choices[name].index(value)
                    )
                    field_ax.set_title(name, fontsize=8)
                else:
                    field_ax = fig.add_axes([x, 0.13, width - 0.045, 0.06])
                    control = TextBox(field_ax, "", initial=value)
                    field_ax.set_title(name, fontsize=8)
                self._axes.append(field_ax)
                self._fields[name] = control
                self._controls.append(control)
            ok_ax = fig.add_axes([0.30, 0.045, 0.16, 0.055])
            cancel_ax = fig.add_axes([0.53, 0.045, 0.16, 0.055])
            ok, cancel_button = Button(ok_ax, "Apply"), Button(cancel_ax, "Cancel")
            ok.on_clicked(self._submit)
            cancel_button.on_clicked(lambda event: self.cancel())
            self._axes.extend([ok_ax, cancel_ax])
            self._controls.extend([ok, cancel_button])
            fig.canvas.draw_idle()

    @property
    def is_editing(self):
        if self._closed:
            return False
        return self._notebook or any(
            isinstance(control, TextBox) and control.capturekeystrokes
            for control in self._fields.values()
        )

    def _submit(self, event=None):
        if self._closed:
            return
        values = {}
        for name, control in self._fields.items():
            if self._notebook:
                values[name] = control.value
            elif isinstance(control, RadioButtons):
                values[name] = control.value_selected
            else:
                values[name] = control.text
        try:
            self.submit(values)
        except (ValueError, TypeError) as exc:
            if self._notebook:
                self._feedback.value = str(exc)
            else:
                self._feedback.set_text(str(exc))
                self.picker.ax.figure.canvas.draw_idle()
            return
        self.close()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._box is not None:
            # Closing the parent alone does not release child comms.
            for child in self._fields.values():
                child.close()
            for row in self._box.children:
                if hasattr(row, "children"):
                    for child in row.children:
                        child.close()
                row.close()
            self._box.close()
        else:
            fig = self.picker.ax.figure
            for control in self._controls:
                if isinstance(control, TextBox):
                    control.stop_typing()
                control.disconnect_events()
            for ax in self._axes:
                if ax in fig.axes:
                    ax.remove()
            self._heading.remove()
            self._feedback.remove()
            for ax, position in self._positions:
                ax.set_position(position)
            if self._layout_engine is not None:
                fig.set_layout_engine(self._layout_engine)
            fig.canvas.draw_idle()
