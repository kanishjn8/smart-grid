from src.domain import ForecastBundle, Observation, Assets
from src.scenarios import profile


def forecast(obs: Observation, assets: Assets, interval_minutes: int, model: str = "profile", horizon: int = 36,
             error_scale: float = 1) -> ForecastBundle:
    if model not in {"profile", "persistence"}:
        raise ValueError("unknown forecast model")
    hour = obs.timestamp.hour + obs.timestamp.minute/60
    current_template = profile(hour, assets.pv_kw)[2]
    cloud = min(1, obs.renewable_kw/current_template) if current_template > 1 else .85
    demand, solar = [], []
    for j in range(1, horizon+1):
        h = (hour + j*interval_minutes/60) % 24
        c, n, p = profile(h, assets.pv_kw)
        demand.append((c+n if model == "profile" else obs.critical_kw+obs.normal_kw)*error_scale)
        solar.append((p*cloud if model == "profile" else obs.renewable_kw)*error_scale)
    return ForecastBundle(issue_step=obs.step, demand_kw=tuple(demand), pv_kw=tuple(solar),
                          lower_pv_kw=tuple(p*.65 for p in solar), upper_pv_kw=tuple(p*1.2 for p in solar),
                          model_version=f"{model}-v1")
