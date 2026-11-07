from html import escape
from .model import predict
from .simulation import simulate
from .storage import initialize,save

def build_report(card, config):
    weights=config["weights"]; beta=config["beta"]; runs=config["monte_carlo_runs"]
    rows=[]
    initialize()
    event=card.get("event",{})
    for fight in card.get("fights",[]):
        empirical=fight.get("empirical_prediction")
        if isinstance(empirical,dict) and empirical.get("p_a") is not None:
            p_a=float(empirical["p_a"])
            pred={"p_a":p_a,"p_b":float(empirical.get("p_b",1-p_a)),"score_diff":None,
                  "model_name":str(empirical.get("model","empirical model"))}
        else:
            pred=predict(fight,weights,beta)
        sim=simulate(fight,pred["p_a"],runs)
        payload={"prediction":pred,"simulation":sim}
        save(event.get("name","N/D"),fight["fighter_a"],fight["fighter_b"],payload)
        rows.append((fight,pred,sim))
    body=[]
    for f,p,s in rows:
        dist=s["outcomes"]
        body.append(f"""<section><h2>{escape(f['fighter_a'])} vs {escape(f['fighter_b'])}</h2>
        <p>Division: {escape(str(f.get('division','N/D')))} | Rounds: {f.get('rounds','N/D')}</p>
        <p><b>{escape(str(p.get('model_name','Configured baseline model')))} win probabilities:</b> A {p['p_a']:.1%} / B {p['p_b']:.1%}</p>
        <p><b>Monte Carlo:</b> A {s['p_a_sim']:.1%} / B {s['p_b_sim']:.1%}; 95% MC sampling interval for A: {s['mc_95_interval_a'][0]:.1%}–{s['mc_95_interval_a'][1]:.1%}</p>
        <p><b>Method distribution:</b><br>{'<br>'.join(f'{escape(k)}: {v:.1%}' for k,v in dist.items())}</p>
        <p><b>Data quality:</b> {escape(str(f.get('data_quality','N/D')))}</p>
        </section>""")
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>UFC Quant Report</title>
    <style>body{{font-family:Arial,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}}section{{border:1px solid #ddd;padding:1rem;margin:1rem 0}}.warn{{color:#8b0000}}</style></head>
    <body><h1>UFC Main Card Quantitative Report</h1><h2>{escape(str(event.get('name','N/D')))}</h2>
    <p>Date: {escape(str(event.get('date','N/D')))} | Location: {escape(str(event.get('location','N/D')))}</p>
    <p class="warn">Probabilities are model estimates. Demo card or uncalibrated inputs must not be treated as verified forecasts.</p>{''.join(body)}</body></html>"""
