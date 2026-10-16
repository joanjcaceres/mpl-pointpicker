from __future__ import annotations

from ._forms import Form


class BaseTagUI:
    """Adaptive tagging form; the public picker owns validation and data."""

    def __init__(self, picker):
        self.picker = picker
        self._form = None

    @property
    def is_editing(self):
        return self._form is not None and self._form.is_editing

    def is_available(self):
        return True

    def show(self, idx):
        self.close()
        label, sigma = self.picker._tag_defaults_for(idx)
        kind = "Series" if isinstance(label, str) else "Transition"
        text = label if isinstance(label, str) else f"{label[0]},{label[1]}" if label else "0,1"

        def submit(values):
            if values["Action"] == "Remove tag":
                self.picker._remove_tag(idx)
                return
            if values["Type"] == "Transition":
                try:
                    parts = values["Label"].split(",")
                    if len(parts) != 2:
                        raise ValueError()
                    parsed = tuple(int(part.strip()) for part in parts)
                except ValueError as exc:
                    raise ValueError("Enter two integers separated by a comma, e.g. 0,1") from exc
            else:
                parsed = values["Label"]
            raw_sigma = values["Sigma (y units)"].strip()
            sigma_value = float(raw_sigma) if raw_sigma else None
            self.picker.tag_point(idx, parsed, sigma_value)

        self._form = Form(
            self.picker,
            f"Tag point #{idx}: choose a series or transition",
            {
                "Type": kind,
                "Label": text,
                "Sigma (y units)": "" if sigma is None else f"{sigma:g}",
                "Action": "Set tag",
            },
            submit,
            self.close,
            choices={"Type": ["Transition", "Series"], "Action": ["Set tag", "Remove tag"]},
        )

    def close(self):
        if self._form is not None:
            self._form.close()
            self._form = None


def create_tag_ui(picker, prefer_widgets=True):
    return BaseTagUI(picker)
