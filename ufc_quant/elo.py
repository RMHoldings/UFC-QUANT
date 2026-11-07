"""Pre-bout Elo rating features and chronological rating updates."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

@dataclass
class EloConfig:
    initial_rating: float = 1500.0
    k_factor: float = 32.0
    scale: float = 400.0
    home_advantage: float = 0.0  # neutral-site MMA defaults to zero

class Elo:
    def __init__(self, config=None):
        self.config=config or EloConfig()
        self.ratings={}

    def rating(self,name):
        return self.ratings.get(name,self.config.initial_rating)

    def expected(self,a,b):
        ra,rb=self.rating(a),self.rating(b)
        return 1.0/(1.0+10.0**((rb-ra-self.config.home_advantage)/self.config.scale))

    def update(self,a,b,score_a):
        """score_a=1 win, .5 draw, 0 loss. Returns pre-fight ratings and expectation."""
        ra,rb=self.rating(a),self.rating(b)
        ea=self.expected(a,b)
        self.ratings[a]=ra+self.config.k_factor*(float(score_a)-ea)
        self.ratings[b]=rb+self.config.k_factor*((1.0-float(score_a))-(1.0-ea))
        return {"rating_a_pre":ra,"rating_b_pre":rb,"elo_diff_pre":ra-rb,"expected_a":ea}

def build_elo_snapshots(bouts:Iterable[dict], date_key="date", fighter_a_key="red_name",
                        fighter_b_key="blue_name", outcome_key="y"):
    """Input rows chronologically sorted internally; outcome y is fighter A win (0/1).
    Returns feature rows with strictly pre-bout Elo values. Rows with unknown outcome are
    emitted with snapshots but don't update ratings.
    """
    engine=Elo()
    rows=sorted(list(bouts),key=lambda r:r.get(date_key,""))
    out=[]
    for row in rows:
        a=row[fighter_a_key]; b=row[fighter_b_key]
        snap=engine.expected(a,b)
        pre={"rating_a_pre":engine.rating(a),"rating_b_pre":engine.rating(b),
             "elo_diff_pre":engine.rating(a)-engine.rating(b),"elo_expected_a":snap}
        item=dict(row); item.update(pre); out.append(item)
        y=row.get(outcome_key)
        if y not in (None,"","NA","na"):
            try: engine.update(a,b,float(y))
            except (TypeError,ValueError): pass
    return out
