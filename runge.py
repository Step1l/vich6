import miln

def make_n(x0, xn, h):
    return round((xn - x0) / h) + 1
def rungstep(method,f,x0,y0,xn,h,eps,p):
    R = eps+1
    xh,yh=[],[]
    h=h*2
    for i in range(200):
        h=h/2
        n1 = make_n(x0, xn, h)
        n2 = make_n(x0, xn, h / 2)
        xh,yh = method(f,x0,y0,h,n1)
        xh2,yh2 = method(f,x0,y0,h/2,n2)
        R = abs(yh[n1-1]-yh2[n2-1])/(2**p-1)
        if R<=eps:break
    else:
        raise ValueError(
            f"Метод не сошелся за 1000 итераций к нужной погрешности")
    return (xh,yh),h

def rungforecast(method,f,x0,y0,xn,h,eps,exact_fn):
    n = make_n(x0,xn,h)
    xh, yh = method(f, x0, y0, h, n, eps)
    return (xh,yh),h


