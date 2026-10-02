# Editable affordability model

`src/evaluation/economics.py`, `/api/economics`, and the Affordability view calculate low/base/high capital and operating costs in INR. **Every cost is an assumed budget placeholder, dated 2026-09-20.** There are no vendor quotes. The API includes source/status/date/range labels. `data/assumptions.json` preserves the default inputs and `results/latest/economics.json` the computed amounts.

Costs cover PV, storage, inverter, isolation/protection, meters, gateway, installation, connectivity, maintenance, battery replacement, recycling and operator time. Existing PV/battery flags remove initial acquisition costs; battery replacement remains included. They do not assert existing equipment meets islanding requirements. The inverter/protection budget still needs an electrical design and site quotation.

Annualization uses the capital-recovery factor at the editable real discount rate and horizon, plus discounted battery replacements before project end, discounted recycling, annual maintenance, connectivity and operator costs. Zero discount uses straight-line annualization. Low/base/high multiply monetary assumptions by 0.7/1/1.4; these are sensitivity bounds, not market price confidence intervals. Household-month cost divides annual cost by 12 and participating households.

Annual served or avoided-unserved energy can be provided explicitly for corresponding unit costs. The calculator leaves these ratios N/A by default: a 24-hour synthetic stress case is not a representative annual outage distribution. This ratio is total-system cost per avoided-unserved kWh, not an incremental benefit-cost ratio. No annual savings, outage valuation or tariff revenue is invented. Tariff purchase costs can be computed per run from imports, but household billing requires allocation rules not supplied here.

No demand-response incentive or emissions benefit is assumed. Batteries have charging losses and grid charging can increase imports. Verified grid/generator factors and an energy-source ledger are needed before estimating operational avoided emissions; manufacturing, replacement and recycling inputs are required for lifecycle claims.

## Alternatives and service targets

The evaluator includes 80/160/320 kWh same-policy battery sensitivities and B0/B1/P ablations. Compare larger-battery B1 and forecast-aware dispatch at the same critical-energy target; do not call unequal target outcomes cost equivalent. Diesel/UPS alternatives require fuel curves, installation costs, noise/emissions constraints and local quotations; their procurement comparison is an open external-data item, not an implemented claimed saving. Second-life storage remains a future option requiring capacity testing, warranty and safety assessment.

The proposed community model includes households without owned PV or batteries. Affordability has not been validated with residents. A cooperative or service provider would need an agreed cost share, hardship policy and complaint mechanism before any pilot.
