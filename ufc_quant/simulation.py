import numpy as np

def simulate(fight, p_a, runs=10000, seed=42):
    """Monte Carlo over categorical fight outcomes. Parameters are explicit inputs.

    finish_rates keys: a_ko, a_sub, b_ko, b_sub; remainder is decision.
    This baseline samples outcome/method, not exchange-by-exchange trajectories.
    """
    rates=fight.get("finish_rates",{})
    a_ko=max(0,float(rates.get("a_ko",0)))
    a_sub=max(0,float(rates.get("a_sub",0)))
    b_ko=max(0,float(rates.get("b_ko",0)))
    b_sub=max(0,float(rates.get("b_sub",0)))
    total_finish=a_ko+a_sub+b_ko+b_sub
    if total_finish>1:
        # Normalize finishing rates to leave no negative decision probability.
        scale=1/total_finish
        a_ko*=scale; a_sub*=scale; b_ko*=scale; b_sub*=scale
        total_finish=1.0
    # Decision split follows model win probability conditional on decision.
    decision=max(0,1-total_finish)
    outcomes=[a_ko,a_sub,b_ko,b_sub,decision*p_a,decision*(1-p_a)]
    labels=["A KO/TKO","A submission","B KO/TKO","B submission","A decision","B decision"]
    rng=np.random.default_rng(seed)
    draws=rng.choice(len(labels),size=runs,p=outcomes)
    counts=np.bincount(draws,minlength=len(labels))
    results={labels[i]:float(counts[i]/runs) for i in range(len(labels))}
    wins_a=results["A KO/TKO"]+results["A submission"]+results["A decision"]
    wins_b=1-wins_a
    # Wilson interval for Monte Carlo sampling uncertainty, not model uncertainty.
    def wilson(k,n,z=1.96):
        ph=k/n; den=1+z*z/n
        center=(ph+z*z/(2*n))/den
        half=z*math.sqrt(ph*(1-ph)/n+z*z/(4*n*n))/den
        return [max(0,center-half),min(1,center+half)]
    import math
    k=round(wins_a*runs)
    return {"runs":runs,"outcomes":results,"p_a_sim":wins_a,"p_b_sim":wins_b,
            "mc_95_interval_a":wilson(k,runs),"note":"Monte Carlo sampling interval only; does not capture parameter/model uncertainty."}
