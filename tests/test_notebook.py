import matplotlib.pyplot as plt
import numpy as np
import pytest

from mpl_pointpicker import PointPicker
from mpl_pointpicker import _forms
from test_picker import click, key


@pytest.fixture
def notebook(monkeypatch):
    widgets = pytest.importorskip("ipywidgets")
    displayed = []
    monkeypatch.setattr(_forms, "_notebook_widgets", lambda: (widgets, displayed.append))
    return displayed


def test_notebook_tag_submit_validation_and_shortcuts(notebook):
    _, ax = plt.subplots()
    picker = PointPicker(ax)
    picker._add_point(1, 2)
    picker.mode = "tag"
    picker._tag_ui.show(0)
    form = picker._tag_ui._form
    assert len(notebook) == 1
    assert notebook[0] is picker._form_host
    assert picker._form_host.children == (form._box,)
    form._fields["Type"].value = "Series"
    form._fields["Label"].value = "measurement A"
    form._fields["Sigma (y units)"].value = "nan"
    key(picker, "d")
    assert picker.mode == "tag"
    form._submit()
    assert not form._closed
    assert "positive" in form._feedback.value
    form._fields["Sigma (y units)"].value = "0.2"
    form._submit()
    assert picker.to_dict() == {"measurement A": [(1.0, 2.0, 0.2)]}
    assert form._closed
    assert picker._form_host.children == ()
    key(picker, "m")
    assert picker.mode == "move"


def test_notebook_calibration_and_cancel(notebook):
    picker = PointPicker.from_image(np.zeros((101, 101)))
    picker.calibrate()
    for point in ((10, 50), (90, 50), (50, 80), (50, 20)):
        click(picker, *point)
    form = picker._calibration.form
    for name, value in zip(("X1", "X2", "Y1", "Y2"), ("0", "2", "10", "40")):
        form._fields[name].value = value
    form._submit()
    assert picker._calibration is None
    assert form._closed
    np.testing.assert_allclose(picker._image.get_extent(), [-0.2625, 2.2625, -0.25, 50.25])
    picker.calibrate()
    key(picker, "escape")
    assert picker._calibration is None
