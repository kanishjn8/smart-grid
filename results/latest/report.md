# Computed held-out synthetic evaluation

10 paired seeds per scenario (100 onward). P versus B1; kWh. Negative results retained.

|Scenario|Controller|n|Critical ENS mean [min, max]|Total ENS mean [min, max]|Terminal energy mean|
|---|---|---:|---:|---:|---:|
|normal|B1|10|0.00 [0.00, 0.00]|0.00 [0.00, 0.00]|160.00|
|normal|P|10|0.00 [0.00, 0.00]|0.00 [0.00, 0.00]|160.00|
|cloudy_evening|B1|10|0.00 [0.00, 0.00]|7.78 [5.75, 9.14]|16.00|
|cloudy_evening|P|10|0.00 [0.00, 0.00]|7.78 [5.75, 9.14]|73.27|
|extended_outage|B1|10|37.89 [37.58, 38.00]|165.50 [163.60, 166.80]|16.00|
|extended_outage|P|10|0.00 [0.00, 0.00]|177.24 [175.38, 178.45]|59.71|
|coordinator_failure|B1|10|0.00 [0.00, 0.00]|7.78 [5.75, 9.14]|16.00|
|coordinator_failure|P|10|0.00 [0.00, 0.00]|7.78 [5.75, 9.14]|73.27|
|partition|B1|10|0.00 [0.00, 0.00]|7.78 [5.75, 9.14]|16.00|
|partition|P|10|0.00 [0.00, 0.00]|7.78 [5.75, 9.14]|73.27|
|flex_arrival|B1|10|0.00 [0.00, 0.00]|200.63 [198.76, 202.04]|16.00|
|flex_arrival|P|10|0.00 [0.00, 0.00]|200.61 [198.68, 202.04]|47.46|
|resource_exhaustion|B1|10|61.01 [61.00, 61.09]|257.48 [255.74, 259.12]|16.00|
|resource_exhaustion|P|10|17.02 [16.65, 17.60]|257.48 [255.74, 259.12]|16.00|

## Requirement 4 — software prototype

Run `make run` for the interactive simulator or open `web/offline.html` for saved playback. No hardware build is required.

## Requirement 5 — measured reliability against B1

B1 and P use identical assets, starting SOC, realized profiles and participation. B1 prioritizes critical demand, charges renewable surplus, discharges deficits and schedules available tasks by earliest deadline. P uses a three-hour forecast heuristic. Positive hours avoided means improvement; negative means regression.

Critical interruption hours count intervals with any unmet critical demand. Scarcity windows are identical external-input intervals where renewable supply plus grid capacity is below fixed critical + normal demand, before battery dispatch. Availability is the percentage of positive-critical-demand intervals fully served, not the energy-served percentage.

|Scenario|B1 critical interruption h|P critical interruption h|Paired hours avoided mean [min, max]|Scarcity critical availability B1 → P (%)|
|---|---:|---:|---:|---:|
|normal|0.000|0.000|0.000 [0.000, 0.000]|N/A → N/A|
|cloudy_evening|0.000|0.000|0.000 [0.000, 0.000]|100.00 → 100.00|
|extended_outage|3.167|0.000|3.167 [3.167, 3.167]|47.22 → 100.00|
|coordinator_failure|0.000|0.000|0.000 [0.000, 0.000]|100.00 → 100.00|
|partition|0.000|0.000|0.000 [0.000, 0.000]|100.00 → 100.00|
|flex_arrival|0.000|0.000|0.000 [0.000, 0.000]|100.00 → 100.00|
|resource_exhaustion|5.342|1.717|3.625 [3.583, 3.667]|46.58 → 82.83|

No real-world reliability claim. Terminal SOC is reported; no salvage credit. Forecast and scenario assumptions are in each run manifest. Task misses count in total ENS once. Aggregated customer service uses equal proportional allocation.
