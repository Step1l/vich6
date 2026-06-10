import matplotlib
matplotlib.use("TkAgg")
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backend_bases import MouseButton
import math
import sys

from rungeknut   import rungeknut
from modeulerum  import modeulerum
from miln        import miln
from runge       import rungstep, rungforecast



EQUATIONS = {
    "y' = y":       (lambda x, y: y,           lambda x, c: c * math.exp(x)),
    "y' = -y":      (lambda x, y: -y,          lambda x, c: c * math.exp(-x)),
    "y' = x":       (lambda x, y: x,           lambda x, c: x**2/2 + c),
    "y' = sin(x)":  (lambda x, y: math.sin(x), lambda x, c: -math.cos(x) + c),
    "y' = x^2 - y": (lambda x, y: x**2 - y,   None),
}

def get_exact(eq_name, x0, y0):
    _, exact_template = EQUATIONS[eq_name]
    if exact_template is None:
        return None
    name = eq_name
    if name == "y' = y":
        C = y0 / math.exp(x0)
    elif name == "y' = -y":
        C = y0 * math.exp(x0)
    elif name == "y' = x":
        C = y0 - x0**2/2
    elif name == "y' = sin(x)":
        C = y0 + math.cos(x0)
    else:
        return None

    def exact(x):
        return exact_template(x, C)
    return exact


ONE_STEP  = {"Эйлер модиф.": (modeulerum, 2), "Рунге-Кутта 4": (rungeknut, 4)}
MULTI_STEP = {"Милна": miln}

METHOD_COLORS = {
    "Эйлер модиф.":  "#89b4fa",
    "Рунге-Кутта 4": "#a6e3a1",
    "Милна":         "#fab387",
    "Точное":        "#ffffff",
}

ZOOM_MIN, ZOOM_MAX = 1e-6, 1e6




class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ОДУ — Задача Коши")
        self.geometry("1400x820")
        self.configure(bg="#1e1e2e")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._last_results = {}
        self._panning = False
        self._pan_start = None
        self._vis = {m: tk.BooleanVar(value=True) for m in list(ONE_STEP) + list(MULTI_STEP) + ["Точное"]}

        self._build_ui()

    def _on_close(self):
        plt.close("all"); self.destroy(); sys.exit(0)



    def _build_ui(self):
        left = tk.Frame(self, bg="#1e1e2e", width=400)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        left.pack_propagate(False)

        right = tk.Frame(self, bg="#1e1e2e")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,10), pady=10)

        self._build_inputs(left)
        self._build_visibility(left)
        self._build_results(left)
        self._build_plot(right)

    def _lbl(self, parent, text):
        tk.Label(parent, text=text, bg="#1e1e2e", fg="#cdd6f4",
                 font=("Courier", 9)).pack(anchor="w", pady=(4,0))

    def _entry(self, parent, default=""):
        e = tk.Entry(parent, bg="#313244", fg="#cdd6f4", font=("Courier", 10),
                     insertbackground="#cdd6f4", relief="flat")
        e.pack(fill=tk.X, pady=1)
        e.insert(0, default)
        return e

    def _build_inputs(self, parent):
        tk.Label(parent, text="Уравнение:", bg="#1e1e2e", fg="#cdd6f4",
                 font=("Courier", 10, "bold")).pack(anchor="w", pady=(0,2))
        self._eq_var = tk.StringVar(value=list(EQUATIONS.keys())[0])
        ttk.Combobox(parent, textvariable=self._eq_var, state="readonly",
                     values=list(EQUATIONS.keys()), font=("Courier", 9)
                     ).pack(fill=tk.X, pady=(0,6))

        self._lbl(parent, "x₀ (начало)")
        self._x0 = self._entry(parent, "0")
        self._lbl(parent, "y₀ = y(x₀)")
        self._y0 = self._entry(parent, "1")
        self._lbl(parent, "xₙ (конец)")
        self._xn = self._entry(parent, "2")
        self._lbl(parent, "h (шаг)")
        self._h  = self._entry(parent, "0.1")
        self._lbl(parent, "ε (точность)")
        self._eps = self._entry(parent, "0.001")

        tk.Button(parent, text="▶  Решить", command=self._compute,
                  bg="#89b4fa", fg="#1e1e2e", font=("Courier", 11, "bold"),
                  relief="flat", pady=8).pack(fill=tk.X, pady=(10,4))

    def _build_visibility(self, parent):
        tk.Label(parent, text="Показывать:", bg="#1e1e2e", fg="#cdd6f4",
                 font=("Courier", 9, "bold")).pack(anchor="w", pady=(4,0))
        g = tk.Frame(parent, bg="#1e1e2e")
        g.pack(fill=tk.X)
        all_methods = list(ONE_STEP) + list(MULTI_STEP) + ["Точное"]
        for i, name in enumerate(all_methods):
            color = METHOD_COLORS.get(name, "#cdd6f4")
            tk.Checkbutton(g, variable=self._vis[name],
                           command=self._redraw_cached,
                           bg="#1e1e2e", fg=color, selectcolor="#313244",
                           activebackground="#1e1e2e", activeforeground=color,
                           font=("Courier", 9), text=name, anchor="w"
                           ).grid(row=i//2, column=i%2, sticky="w", padx=4)

    def _build_results(self, parent):
        tk.Label(parent, text="Результаты:", bg="#1e1e2e", fg="#cdd6f4",
                 font=("Courier", 10, "bold")).pack(anchor="w", pady=(8,2))
        self.result_text = tk.Text(parent, bg="#181825", fg="#cdd6f4",
                                   font=("Courier", 8), relief="flat",
                                   height=22, wrap=tk.NONE)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        tk.Button(parent, text="Сохранить", command=self._save,
                  bg="#45475a", fg="#cdd6f4", font=("Courier", 9),
                  relief="flat").pack(fill=tk.X, pady=(4,0))

    def _build_plot(self, parent):
        self.fig, self.ax = plt.subplots(figsize=(8,6))
        self.fig.patch.set_facecolor("#1e1e2e")
        self.ax.set_facecolor("#181825")
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        tk.Label(parent, text="СКМ+drag — панорама   Колесо — зум",
                 bg="#1e1e2e", fg="#6c7086", font=("Courier", 8)).pack(anchor="w")
        self.fig.canvas.mpl_connect("button_press_event",   self._on_click)
        self.fig.canvas.mpl_connect("button_release_event", self._on_release)
        self.fig.canvas.mpl_connect("motion_notify_event",  self._on_motion)
        self.fig.canvas.mpl_connect("scroll_event",         self._on_scroll)



    def _on_click(self, event):
        if event.button == MouseButton.MIDDLE and event.inaxes == self.ax:
            self._panning = True
            self._pan_start = (event.xdata, event.ydata)

    def _on_release(self, event):
        if event.button == MouseButton.MIDDLE:
            self._panning = False; self._pan_start = None

    def _on_motion(self, event):
        if not self._panning or event.inaxes != self.ax or event.xdata is None:
            return
        dx = self._pan_start[0] - event.xdata
        dy = self._pan_start[1] - event.ydata
        xl = self.ax.get_xlim(); yl = self.ax.get_ylim()
        self.ax.set_xlim(xl[0]+dx, xl[1]+dx)
        self.ax.set_ylim(yl[0]+dy, yl[1]+dy)
        self.canvas.draw_idle()

    def _on_scroll(self, event):
        if event.inaxes != self.ax or event.xdata is None: return
        factor = 0.85 if event.button == "up" else 1/0.85
        xl = self.ax.get_xlim(); yl = self.ax.get_ylim()
        xw = (xl[1]-xl[0])*factor; yw = (yl[1]-yl[0])*factor
        if xw < ZOOM_MIN or xw > ZOOM_MAX or yw < ZOOM_MIN or yw > ZOOM_MAX: return
        cx, cy = event.xdata, event.ydata
        self.ax.set_xlim(cx+(xl[0]-cx)*factor, cx+(xl[1]-cx)*factor)
        self.ax.set_ylim(cy+(yl[0]-cy)*factor, cy+(yl[1]-cy)*factor)
        self.canvas.draw_idle()



    def _parse(self):
        MAX_VAL = 1e6
        MAX_N   = 10000

        def read(entry, name):
            s = entry.get().strip().replace(",", ".")
            if not s:
                raise ValueError(f"Поле «{name}» не заполнено")
            try:
                return float(s)
            except ValueError:
                raise ValueError(f"«{name}»: введите число, получено «{s}»")

        x0  = read(self._x0,  "x₀")
        y0  = read(self._y0,  "y₀")
        xn  = read(self._xn,  "xₙ")
        h   = read(self._h,   "h")
        eps = read(self._eps, "ε")

        for val, name in [(x0,"x₀"),(y0,"y₀"),(xn,"xₙ"),(h,"h"),(eps,"ε")]:
            if abs(val) > MAX_VAL:
                raise ValueError(f"«{name}» слишком большое: {val}. Допустимо не более {MAX_VAL}")

        if xn <= x0:
            raise ValueError(f"xₙ ({xn}) должно быть больше x₀ ({x0})")
        if xn - x0 > MAX_VAL:
            raise ValueError(f"Интервал [{x0}, {xn}] слишком большой. Максимум {MAX_VAL}")
        if h <= 0:
            raise ValueError(f"Шаг h должен быть > 0, получено {h}")
        if h >= (xn - x0):
            raise ValueError(f"Шаг h={h} больше или равен длине интервала {xn-x0:.6g}. Уменьшите h")
        if eps <= 0:
            raise ValueError(f"Точность ε должна быть > 0, получено {eps}")
        if eps < 1e-12:
            raise ValueError(f"Точность ε={eps} слишком маленькая (минимум 1e-12)")

        n_float = (xn - x0) / h
        n = round(n_float)
        if abs(n - n_float) > 1e-6 * n_float:
            h_suggest = (xn - x0) / round(n_float)
            raise ValueError(
                f"Интервал [{x0}, {xn}] не делится ровно на шаг h={h}.\n"
                f"Попробуйте h={h_suggest:.6g} (даёт ровно {round(n_float)} шагов)"
            )
        if n > MAX_N:
            raise ValueError(f"Слишком много точек: {n}. Максимум {MAX_N}. Увеличьте h")

        return x0, y0, xn, h, eps, n+1

    def _compute(self):
        try:
            x0, y0, xn, h, eps, n = self._parse()
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e)); return

        eq_name = self._eq_var.get()
        f, _ = EQUATIONS[eq_name]
        exact = get_exact(eq_name, x0, y0)

        results = {}
        used_h  = {}
        errors  = {}

        # одношаговые — правило Рунге
        for name, (method, p) in ONE_STEP.items():
            try:
                (xs, ys), hh = rungstep(method, f, x0, y0, xn, h, eps, p)
                results[name] = (xs, ys)
                used_h[name]  = hh
            except Exception as e:
                errors[name] = str(e)

        for name, method in MULTI_STEP.items():
            try:
                if exact is not None:
                    (xs, ys), hh = rungforecast(method, f, x0, y0, xn, h, eps, exact)
                else:
                    xs, ys = method(f, x0, y0, h, n)
                    hh = h
                results[name] = (xs, ys)
                used_h[name]  = hh
            except Exception as e:
                errors[name] = str(e)

        self._last_results = results
        self._last_exact    = exact
        self._last_x0       = x0
        self._last_xn       = xn

        self._show_results(results, used_h, errors, exact)
        self._draw_plot(results, exact, x0, xn, reset_view=True)

    def _show_results(self, results, used_h, errors, exact):
        self.result_text.delete("1.0", tk.END)
        out = []

        for name, (xs, ys) in results.items():
            out.append("="*48)
            out.append(f"{name}  (h={used_h[name]:.6g})")
            header = f"{'i':>4}  {'x':>10}  {'y':>14}"
            if exact:
                header += f"  {'y_exact':>14}  {'|error|':>12}"
            out.append(header)
            for i, (xi, yi) in enumerate(zip(xs, ys)):
                row = f"{i:>4}  {xi:>10.5f}  {yi:>14.8f}"
                if exact:
                    ye = exact(xi)
                    row += f"  {ye:>14.8f}  {abs(yi-ye):>12.2e}"
                out.append(row)
            if exact:
                max_err = max(abs(ys[i]-exact(xs[i])) for i in range(len(xs)))
                out.append(f"  max|error| = {max_err:.4e}")

        for name, err in errors.items():
            out.append("="*48)
            out.append(f"{name}  — ОШИБКА: {err}")

        self.result_text.insert("1.0", "\n".join(out))
        self._last_output = "\n".join(out)

    def _redraw_cached(self):
        if self._last_results:
            self._draw_plot(self._last_results, self._last_exact,
                            self._last_x0, self._last_xn, reset_view=False)

    def _draw_plot(self, results, exact, x0, xn, reset_view=True):
        if not reset_view:
            saved_xl = self.ax.get_xlim()
            saved_yl = self.ax.get_ylim()

        self.ax.cla()
        self.ax.set_facecolor("#181825")
        self.ax.grid(True, color="#2a2d3a", linewidth=0.6, linestyle="--", zorder=0)

        has = False

        # точное решение
        if exact and self._vis["Точное"].get():
            x_plot = np.linspace(x0, xn, 400)
            y_plot = []
            for xv in x_plot:
                try:
                    v = exact(float(xv))
                    y_plot.append(v if math.isfinite(v) else float("nan"))
                except:
                    y_plot.append(float("nan"))
            self.ax.plot(x_plot, y_plot, color="#ffffff", linewidth=1.4,
                         linestyle="--", label="Точное", zorder=1)
            has = True

        for name, (xs, ys) in results.items():
            if not self._vis[name].get():
                continue
            color = METHOD_COLORS.get(name, "#cdd6f4")
            self.ax.plot(xs, ys, color=color, linewidth=1.8, label=name, zorder=2)
            has = True

        if reset_view:
            all_y = []
            for _, (xs, ys) in results.items():
                all_y += [v for v in ys if math.isfinite(v)]
            if exact:
                for xv in np.linspace(x0, xn, 100):
                    try:
                        v = exact(float(xv))
                        if math.isfinite(v): all_y.append(v)
                    except: pass
            if all_y:
                y_span = max(all_y) - min(all_y) or 1
                y_lo = min(all_y) - y_span*0.15
                y_hi = max(all_y) + y_span*0.15
            else:
                y_lo, y_hi = -1, 1
            x_margin = (xn - x0) * 0.05
            self.ax.set_xlim(x0 - x_margin, xn + x_margin)
            self.ax.set_ylim(y_lo, y_hi)
        else:
            self.ax.set_xlim(saved_xl)
            self.ax.set_ylim(saved_yl)

        self.ax.tick_params(colors="#6c7086")
        self.ax.spines[:].set_color("#313244")
        if has:
            self.ax.legend(fontsize=8, facecolor="#313244", edgecolor="#45475a",
                           labelcolor="#cdd6f4")
        self.ax.set_title("Решение ОДУ", color="#cdd6f4", fontsize=10)
        self.fig.tight_layout()
        self.canvas.draw()

    def _save(self):
        if not hasattr(self, "_last_output") or not self._last_output:
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt",
                                            filetypes=[("Text","*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self._last_output)


if __name__ == "__main__":
    App().mainloop()