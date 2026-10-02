"""Editable INR design assumptions, no quotation, incentive or emissions claim."""
from pydantic import Field
from src.domain import Contract


class CostInputs(Contract):
    pv_inr_per_kw: float = Field(default=45000, ge=0, le=1e7)
    battery_inr_per_kwh: float = Field(default=18000, ge=0, le=1e7)
    inverter_inr: float = Field(default=700000, ge=0, le=1e9)
    protection_isolation_inr: float = Field(default=400000, ge=0, le=1e9)
    meters_inr: float = Field(default=200000, ge=0, le=1e9)
    gateway_inr: float = Field(default=30000, ge=0, le=1e9)
    installation_inr: float = Field(default=450000, ge=0, le=1e9)
    annual_connectivity_inr: float = Field(default=12000, ge=0, le=1e9)
    annual_operator_inr: float = Field(default=120000, ge=0, le=1e9)
    annual_maintenance_fraction: float = Field(default=.02, ge=0, le=1)
    recycling_inr: float = Field(default=100000, ge=0, le=1e9)
    discount_rate: float = Field(default=.08, ge=0, le=1)
    lifetime_years: int = Field(default=20, ge=1, le=50)
    battery_replacement_years: int = Field(default=10, ge=1, le=50)
    households: int = Field(default=100, ge=1, le=10000)
    existing_pv: bool = False
    existing_battery: bool = False
    tariff_inr_per_kwh: float = Field(default=7, ge=0, le=1000)
    annual_served_kwh: float | None = Field(default=None, gt=0)
    annual_avoided_ens_kwh: float | None = Field(default=None, gt=0)


def annualized(assets, inputs: CostInputs, multiplier: float = 1):
    c = inputs
    battery = assets.battery_kwh*c.battery_inr_per_kwh
    capex = ((0 if c.existing_pv else assets.pv_kw*c.pv_inr_per_kw) + (0 if c.existing_battery else battery)
             + c.inverter_inr+c.protection_isolation_inr+c.meters_inr+c.gateway_inr+c.installation_inr)*multiplier
    rate, years = c.discount_rate, c.lifetime_years
    crf = rate*(1+rate)**years/((1+rate)**years-1) if rate else 1/years
    replacement_pv = sum(battery*multiplier/(1+rate)**year for year in range(c.battery_replacement_years, years, c.battery_replacement_years))
    recycling_pv = c.recycling_inr*multiplier/(1+rate)**years
    annual = (capex+replacement_pv+recycling_pv)*crf + capex*c.annual_maintenance_fraction + (c.annual_connectivity_inr+c.annual_operator_inr)*multiplier
    return dict(initial_capex_inr=capex, annualized_system_cost_inr=annual,
                household_monthly_inr=annual/c.households/12,
                inr_per_served_kwh=annual/c.annual_served_kwh if c.annual_served_kwh else None,
                inr_per_avoided_unserved_kwh=annual/c.annual_avoided_ens_kwh if c.annual_avoided_ens_kwh else None)


def economics(assets, inputs: CostInputs):
    return dict(currency="INR", status="assumed", source="Unvalidated engineering budget placeholders; replace with dated local quotations",
                date="2026-09-20", range_basis="All monetary inputs ×0.7 / ×1 / ×1.4; sensitivity, not confidence bounds",
                inputs=inputs.model_dump(), low=annualized(assets,inputs,.7), base=annualized(assets,inputs), high=annualized(assets,inputs,1.4),
                incentives_inr=0, emissions_kgco2e=None,
                emissions_note="Not calculated: no verified location/year-specific grid factor or generator fuel trace supplied.",
                boundary="Capital and O&M only. Energy purchases, financing taxes, outage losses and tariff savings are separate; no annual extrapolation of a stress day.")
