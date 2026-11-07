import os, sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
import numpy as np
from ufc_quant.backtest import fit_logistic,predict,evaluate
def test_logistic_probabilities():
    x=np.array([[-2],[-1],[1],[2]],dtype=float); y=np.array([0,0,1,1])
    m=fit_logistic(x,y,epochs=1000)
    p=predict(m,x)
    assert p[0]<p[-1]
    assert all(0<pv<1 for pv in p)
def test_metrics():
    m=evaluate([0,1],[0.1,0.9])
    assert m.accuracy==1.0 and m.brier<0.02
