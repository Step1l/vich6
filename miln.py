import rungeknut
def miln(f, x0, y0, h,n, eps):
    F = [0] * n
    x,y = rungeknut.rungeknut(f,x0,y0,h,4)
    for i in range(4):
        F[i] = f(x[i], y[i])
    x = list(x) + [0.0] * (n - 4)
    y = list(y) + [0.0] * (n - 4)
    for i in range(3, n - 1):
        p = y[i - 3] + (4 * h / 3) * (2 * F[i - 2] - F[i - 1] + 2 * F[i])
        x_next = x[i] + h
        x[i + 1] = x_next
        y_prev = p
        while True:
            fp = f(x_next, y_prev)
            y_corr = y[i - 1] + (h / 3) * (F[i - 1] + 4 * F[i] + fp)
            if abs(y_corr - y_prev) < eps:
                y_next = y_corr
                break
            y_prev = y_corr
        y[i + 1] = y_next
        F[i + 1] = f(x_next, y_next)
    return x, y