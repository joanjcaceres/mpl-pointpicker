from types import SimpleNamespace
from contextlib import nullcontext

import matplotlib.pyplot as plt
from matplotlib.backend_bases import KeyEvent, MouseEvent
import numpy as np
import pytest
import yaml

from mpl_pointpicker import PointPicker


def click(picker, x, y, name="button_press_event"):
    picker.ax.figure.canvas.draw()
    px, py = picker.ax.transData.transform((x, y))
    event = MouseEvent(name, picker.ax.figure.canvas, px, py, button=1)
    picker.ax.figure.canvas.callbacks.process(name, event)


def key(picker, value):
    event = KeyEvent("key_press_event", picker.ax.figure.canvas, key=value)
    picker.ax.figure.canvas.callbacks.process("key_press_event", event)


def test_editing_modes_and_toolbar(capsys):
    fig, ax = plt.subplots()
    ax.set(xlim=(0, 10), ylim=(0, 10))
    picker = PointPicker(ax, use_widgets=False)
    click(picker, 2, 3)
    np.testing.assert_allclose(picker.xy, [[2, 3]])
    picker.tag_point(0, "measurement", 0.1)
    key(picker, "i")
    click(picker, 2, 3)
    assert "measurement" in capsys.readouterr().out
    key(picker, "m")
    click(picker, 2, 3)
    click(picker, 4, 5, "motion_notify_event")
    click(picker, 4, 5, "button_release_event")
    np.testing.assert_allclose(picker.xy, [[4, 5]])
    assert picker._selected_idx is None
    fig.canvas.toolbar = SimpleNamespace(mode="zoom", _wait_cursor_for_draw_cm=nullcontext)
    key(picker, "d")
    click(picker, 4, 5)
    assert len(picker.points) == 1
    fig.canvas.toolbar = None
    click(picker, 4, 5)
    assert picker.xy.shape == (0, 2)
    assert picker.labels == picker.sigmas == []
    picker.disconnect()
    picker.disconnect()
    key(picker, "a")
    click(picker, 1, 1)
    assert len(picker.points) == 0


def test_axis_lock_and_next_column():
    _, ax = plt.subplots()
    ax.set(xlim=(0, 10), ylim=(0, 10))
    picker = PointPicker(ax, axis_lock=True, use_widgets=False)
    click(picker, 2, 2)
    click(picker, 3, 4)
    np.testing.assert_allclose(picker.x_coords, [2, 2])
    key(picker, "n")
    click(picker, 6, 6)
    key(picker, "m")
    click(picker, 6, 6)
    click(picker, 8, 7, "motion_notify_event")
    np.testing.assert_allclose(picker.xy[-1], [6, 7])
    picker.disconnect()
    picker.disconnect()


def test_series_transitions_unlabeled_and_legacy_defaults(tmp_path):
    _, ax = plt.subplots()
    picker = PointPicker(ax, use_widgets=False)
    for xy in [(1, 2), (3, 4), (5, 6), (7, 8)]:
        picker._add_point(*xy)
    picker.tag_point(0, (0, 1), 0.2)
    # A series name that looks like a transition must remain a string.
    picker.tag_point(1, "0,1")
    picker.tag_point(2, "série A", 0.4)
    assert picker.to_transition_data() == {(0, 1): [(1.0, 2.0)]}
    assert picker.to_dict()["0,1"] == [(3.0, 4.0, None)]
    output = tmp_path / "points.yaml"
    picker.save_yaml(output, x_scale=2)
    payload = yaml.safe_load(output.read_text())
    assert payload["data"] == {"0,1": [[2.0, 2.0, 0.2]]}
    assert payload["series"]["0,1"] == [[6.0, 4.0, None]]
    assert payload["unlabeled"] == [[14.0, 8.0, None]]
    _, ax2 = plt.subplots()
    loaded = PointPicker.load_yaml(ax2, output)
    np.testing.assert_allclose(loaded.x_coords, [2, 6, 10, 14])
    assert loaded.labels == [(0, 1), "0,1", "série A", None]
    assert loaded.sigmas == [0.2, None, 0.4, None]
    assert loaded.to_transition_data(include_sigma=True) == {(0, 1): [(2.0, 2.0, 0.2)]}


def test_empty_session_remains_editable(tmp_path):
    _, ax = plt.subplots()
    picker = PointPicker(ax, use_widgets=False)
    output = tmp_path / "empty.yaml"
    picker.save_yaml(output)
    _, other_ax = plt.subplots()
    loaded = PointPicker.load_yaml(other_ax, output)
    assert loaded.points.shape == (0, 2)
    loaded._add_point(1, 2)
    assert loaded.xy.tolist() == [[1, 2]]


@pytest.mark.parametrize("sigma", [0, -1, float("inf"), float("nan")])
def test_invalid_sigma_is_rejected(sigma):
    _, ax = plt.subplots()
    picker = PointPicker(ax, use_widgets=False)
    picker._add_point(1, 2)
    with pytest.raises(ValueError):
        picker.tag_point(0, (0, 1), sigma)
    with pytest.raises(ValueError):
        picker.set_current_sigma(sigma)


@pytest.mark.parametrize("scale", [0, -1, float("inf"), float("nan")])
def test_invalid_export_scale(scale):
    _, ax = plt.subplots()
    with pytest.raises(ValueError):
        PointPicker(ax, use_widgets=False).to_dict(x_scale=scale)


def test_defaults_are_suggestions_and_remove_tag():
    _, ax = plt.subplots()
    picker = PointPicker(ax, use_widgets=False)
    picker.set_current_label("series A")
    picker.set_current_sigma(0.1)
    picker._add_point(1, 2)
    assert picker.labels == [None]
    assert picker._tag_defaults_for(0) == ("series A", 0.1)
    picker.tag_point(0, "series A", 0.1)
    picker._remove_tag(0)
    assert picker.labels == picker.sigmas == [None]


def test_text_entry_does_not_activate_shortcuts_and_restores_layout():
    fig, ax = plt.subplots()
    picker = PointPicker(ax, use_widgets=False)
    picker._add_point(0.5, 0.5)
    position = ax.get_position().frozen()
    key(picker, "t")
    click(picker, 0.5, 0.5)
    form = picker._tag_ui._form
    form._fields["Type"].set_active(1)
    field = form._fields["Label"]
    field.begin_typing()
    field.set_val("")
    for letter in "mad scientist":
        key(picker, letter)
    assert picker.mode == "tag"
    assert field.text == "mad scientist"
    form._submit()
    assert picker.labels == ["mad scientist"]
    np.testing.assert_allclose(ax.get_position().bounds, position.bounds)
    assert len(fig.axes) == 1
    key(picker, "m")
    assert picker.mode == "move"


def test_form_rejects_invalid_and_can_remove_a_tag():
    _, ax = plt.subplots()
    picker = PointPicker(ax, use_widgets=False)
    picker._add_point(1, 2)
    picker._tag_ui.show(0)
    form = picker._tag_ui._form
    form._fields["Label"].set_val("bad")
    form._submit()
    assert not form._closed
    assert "two integers" in form._feedback.get_text()
    form._fields["Label"].set_val("1,2")
    form._submit()
    assert picker.labels == [(1, 2)]
    picker._tag_ui.show(0)
    form = picker._tag_ui._form
    form._fields["Action"].set_active(1)
    form._submit()
    assert picker.labels == [None]


def test_import_does_not_change_global_keymaps():
    import importlib
    import matplotlib
    import mpl_pointpicker.pointpicker as module

    before = dict(matplotlib.rcParams)
    importlib.reload(module)
    assert dict(matplotlib.rcParams) == before
