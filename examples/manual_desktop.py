"""Three lightweight curves for trying PointPicker in a desktop window."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from mpl_pointpicker import PointPicker


def main():
    x = np.linspace(0, 1, 200)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(x, 1 + x, label="Curva 1")
    ax.plot(x, 2 + 0.3 * np.sin(2 * np.pi * x), label="Curva 2")
    ax.plot(x, 3 - 0.5 * x, label="Curva 3")
    ax.set(xlabel="x", ylabel="y")
    ax.legend()
    ax.grid(alpha=0.2)
    fig.canvas.manager.set_window_title("PointPicker - tres curvas")

    picker = PointPicker(ax, axis_lock=True, use_widgets=False)
    output = Path(__file__).resolve().parent / "simple-points.yaml"
    print("a: anadir; m: mover; d: borrar; t: etiquetar; i: inspeccionar; n: nueva columna.")
    print(f"Al cerrar la ventana, los puntos se guardaran en: {output}", flush=True)
    plt.show(block=True)
    picker.save_yaml(output)
    print(picker.to_dict())


if __name__ == "__main__":
    main()
