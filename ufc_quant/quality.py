"""Quality checks to prevent forecasts from being presented on incomplete/mismatched inputs."""
from __future__ import annotations
REQUIRED_STATS=("slpm","str_acc","sapm","str_def","td_avg","td_acc","td_def","sub_avg")
def audit_fighter_stats(stats):
    missing=[key for key in REQUIRED_STATS if getattr(stats,key,None) is None]
    flags=[]
    if missing: flags.append("missing_stats:"+",".join(missing))
    if not getattr(stats,"name",""): flags.append("missing_name")
    return {"ok":not flags,"missing":missing,"flags":flags}
def require_verified_main_card(bouts, verified_urls):
    """verified_urls must be supplied from the official UFC.com event page."""
    return [b for b in bouts if b.fight_url in set(verified_urls)]
