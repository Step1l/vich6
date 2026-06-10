def modeulerum(f,x0,y0,h,n):
    x = [0]* n
    for i in range(n):
        x[i]=x0+i*h
    y=[0]*n
    y[0]=y0
    for i in range(1,n):
        y[i]=y[i-1]+(h/2)*(f(x[i-1],y[i-1]) +f(x[i],y[i-1]+h*f(x[i-1],y[i-1])))
    return x,y
