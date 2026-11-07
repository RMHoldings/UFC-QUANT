import math
import json

def validate_weights(weights):
    total=sum(weights.values())
    if abs(total-1.0)>1e-8:
        raise ValueError(f"Weights must sum to 1.0, got {total}")
    return weights

def score_diff(fight, weights):
    validate_weights(weights)
    a=fight["features_a"]; b=fight["features_b"]
    return sum(weights[k]*(float(a.get(k,0))-float(b.get(k,0))) for k in weights)

def logistic_probability(score, beta):
    z=max(-35.0,min(35.0,beta*score))
    return 1.0/(1.0+math.exp(-z))

def predict(fight, weights, beta):
    s=score_diff(fight,weights)
    p=logistic_probability(s,beta)
    return {"score_diff":s,"p_a":p,"p_b":1-p}
