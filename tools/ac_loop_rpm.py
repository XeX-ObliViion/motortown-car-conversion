import sys, wave, numpy as np
def spec(p):
    w=wave.open(p); sr=w.getframerate(); ch=w.getnchannels()
    x=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float)
    if ch>1: x=x.reshape(-1,ch).mean(1)
    N=1<<16; acc=np.zeros(N//2+1)
    for t0 in range(0,max(1,len(x)-N),N//2): acc+=np.abs(np.fft.rfft(x[t0:t0+N]*np.hanning(N)))
    return np.fft.rfftfreq(N,1/sr), acc
for p in sys.argv[2:]:
    f,a=spec(p); a=a/a.max()
    best=[]
    for R in range(1000,9001,5):
        base=R/120.0   # half order
        sc=0
        for k in range(1,25):
            i=int(round(k*base/(f[1]-f[0])))
            if i<len(a): sc+=a[max(0,i-2):i+3].max()*(2.0 if k%10==0 else 1.0)   # firing (rpm/12) = 10th half-order, weighted
        best.append((sc,R))
    best.sort(reverse=True)
    print(p.split('/')[-1], [r for _,r in best[:4]])
