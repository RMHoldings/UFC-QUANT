"""Temporal backtesting for binary fight outcomes.
Input CSV must contain one row per bout, pre-fight feature columns, and outcome column y.
Avoid leakage: features must be snapshots known before bout date.
"""
from __future__ import annotations
import csv, json, math
from dataclasses import dataclass
from typing import Sequence
import numpy as np

@dataclass
class Metrics:
    n: int
    accuracy: float
    brier: float
    log_loss: float
    auc: float

def sigmoid(z):
    z=np.clip(z,-35,35)
    return 1.0/(1.0+np.exp(-z))

def standardize_fit(x):
    mu=x.mean(axis=0)
    sd=x.std(axis=0)
    sd=np.where(sd<1e-9,1.0,sd)
    return mu,sd

def fit_logistic(x,y,lr=0.05,epochs=2500,l2=0.01):
    """Simple deterministic logistic regression, no sklearn dependency."""
    x=np.asarray(x,dtype=float); y=np.asarray(y,dtype=float)
    mu,sd=standardize_fit(x)
    xs=(x-mu)/sd
    xs=np.column_stack([np.ones(len(xs)),xs])
    w=np.zeros(xs.shape[1],dtype=float)
    for _ in range(epochs):
        p=sigmoid(xs@w)
        grad=(xs.T@(p-y))/len(y)
        grad[1:]+=l2*w[1:]
        w-=lr*grad
    return {"weights":w.tolist(),"mean":mu.tolist(),"scale":sd.tolist()}

def predict(model,x):
    x=np.asarray(x,dtype=float)
    mu=np.asarray(model["mean"]); sd=np.asarray(model["scale"])
    xs=(x-mu)/sd
    xs=np.column_stack([np.ones(len(xs)),xs])
    return sigmoid(xs@np.asarray(model["weights"]))

def auc_score(y,p):
    y=np.asarray(y,dtype=int); p=np.asarray(p,dtype=float)
    pos=p[y==1]; neg=p[y==0]
    if len(pos)==0 or len(neg)==0: return float("nan")
    # Pairwise rank AUC; appropriate for modest backtest batches.
    return float((sum((a>b)+0.5*(a==b) for a in pos for b in neg))/(len(pos)*len(neg)))

def evaluate(y,p):
    y=np.asarray(y,dtype=float); p=np.clip(np.asarray(p,dtype=float),1e-8,1-1e-8)
    return Metrics(
        n=len(y), accuracy=float(np.mean((p>=0.5)==(y>=0.5))),
        brier=float(np.mean((p-y)**2)),
        log_loss=float(-np.mean(y*np.log(p)+(1-y)*np.log(1-p))),
        auc=auc_score(y,p)
    )

def temporal_backtest(csv_path, feature_columns:Sequence[str], outcome_column="y", date_column="date", train_fraction=0.7):
    with open(csv_path,newline="",encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    rows=sorted(rows,key=lambda r:r[date_column])
    if len(rows)<30: raise ValueError("Need at least 30 historical bouts for a minimally meaningful temporal split.")
    split=max(1,min(len(rows)-1,int(len(rows)*train_fraction)))
    x=np.array([[float(r[c]) for c in feature_columns] for r in rows])
    y=np.array([int(r[outcome_column]) for r in rows])
    model=fit_logistic(x[:split],y[:split])
    p=predict(model,x[split:])
    metrics=evaluate(y[split:],p)
    return {"train_n":split,"test_n":len(rows)-split,"features":list(feature_columns),
            "metrics":metrics.__dict__,"predictions":[{"date":rows[i+split][date_column],"p":float(p[i]),"y":int(y[i+split])} for i in range(len(p))],
            "model":model}

def save_result(result, path):
    with open(path,"w",encoding="utf-8") as f: json.dump(result,f,indent=2)
