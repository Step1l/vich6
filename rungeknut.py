def rungeknut(f,x0,y0,h,n):
    x = [0]*n
    for i in range(n):
        x[i] = x0 + i * h
    y=[0]*n
    y[0]=y0
    for i in range(1,n):
        k1 = h*f(x[i-1],y[i-1])
        k2 = h*f(x[i-1]+h/2,y[i-1]+k1/2)
        k3 = h*f(x[i-1]+h/2,y[i-1]+k2/2)
        k4=h*f(x[i-1]+h,y[i-1]+k3)
        y[i]=y[i-1]+(1/6)*(k1+2*k2+2*k3+k4)
    return x,y