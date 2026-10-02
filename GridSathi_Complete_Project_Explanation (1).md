# GridSathi 

### _Complete project explanation_ 

GridSathi is a proposed neighbourhood energy-management system. It coordinates local renewable generation, shared batteries and participating electricity loads so that limited energy is used deliberately, especially when supply is uncertain. Its central job is to decide what to power now, what can wait and how much stored energy must be protected for later. 

The system combines forecasting, constrained scheduling, local safety checks and resilient control. A community operator sees which services are being supplied and why. A distribution utility can receive an aggregate view of demand and available flexibility. Residents retain control over which eligible loads may be rescheduled. 

This document explains the intended design rather than claiming a completed deployment. All numerical examples are illustrative calculations, not measured performance. The prototype represents electrical assets in software; field operation would require compatible certified equipment and independent engineering validation. 

### **How to read this document** 

|**Section**|**What it explains**|
|---|---|
|1 and 2|The problem, users and electrical operating boundary|
|3 and 4|Components, input data and the full operating cycle|
|5 and 6|Energy accounting, battery behaviour and forecasting|
|7 and 8|Scheduling, priorities, fairness and flexible loads|
|9 and 10|Controller coordination, failures and recovery|
|11|A worked example of energy reservation and load shifting|
|12 and 13|Backend, dashboard, data protection and evaluation|
|14 and 15|Ownership, affordability, limitations and key questions|



### **The main idea** 

A battery can postpone a shortage, but it cannot supply unlimited energy. Forecasting can reveal a future gap, but cannot guarantee that the forecast is correct. GridSathi connects those facts: it makes a feasible plan, checks every command locally, observes what actually happened and updates the plan repeatedly. 

GridSathi  |  1 

## **1 The problem GridSathi addresses** 

Electricity demand and renewable production do not necessarily rise and fall together. Solar generation may be high in the afternoon while household demand peaks after sunset. Cloud cover can reduce output before demand changes. If an upstream connection is constrained or unavailable, a neighbourhood must operate using whatever local energy and storage are physically available. 

Treating every load identically can waste that limited supply. An electric vehicle may be able to charge later, while essential lighting or clinic refrigeration needs service immediately. A battery that supplies every optional load early in an outage may have little energy left for essential services later. 

### **The decisions the system makes** 

GridSathi decides how much battery power to charge or discharge, which consenting flexible tasks to run, how much power to import within a feeder limit and whether unavoidable shortages require curtailment. Curtailment means deliberately reducing supply to a load or reducing renewable output; the dashboard distinguishes these two meanings. 

The system also decides when it cannot make a reliable coordinated plan. If telemetry becomes stale or controller authority is uncertain, it moves to a bounded local fallback. A missed optimization cycle must not become a command to exceed battery limits. 

### **Who uses it** 

Residents specify eligible tasks and preferences, such as an EV charging deadline. A local operator configures assets, reviews alerts and handles maintenance escalation. A DISCOM, meaning an electricity distribution company, may provide a feeder import constraint or an authorized demand-response request. Demand response means changing controllable demand for an agreed period; it does not create additional generation. 

The operator classifies essential circuits using an agreed community policy. Classification is not inferred from private household activity and is not automatically assigned according to willingness to pay. A clinic may contain both essential refrigeration and deferrable equipment, so the model classifies circuits or services rather than making every device in a building critical. 

### **What success means** 

Success means less unmet essential demand, acceptable completion of deferred tasks and a credible cost of providing that service. It is possible to reduce a peak while making residents worse off by never completing their tasks. GridSathi therefore evaluates service delivery and inconvenience together. 

There is no promise of eliminating every outage. If the available energy is insufficient, the correct behaviour is to preserve the highest-priority services within physical limits, show the remaining deficit clearly and explain which assumption or resource is limiting performance. 

GridSathi  |  2 

## **2 The neighbourhood and electrical boundary** 

The reference setting is a local microgrid: a defined group of loads and energy assets behind an identifiable electrical connection point. It can contain homes, shops, essential community services, rooftop solar and a shared battery. The number and capacity of these assets are configurable. A model of 100 homes is a scenario choice, not evidence of an actual pilot. 

### **Grid connected operation** 

When the upstream grid is available, local generation supplies demand and surplus may charge the battery. The controller can import additional energy within the configured limit. Export is allowed only when the scenario explicitly supports it. If export is unavailable and the battery cannot accept more energy, surplus renewable output is recorded as curtailed rather than silently disappearing. 

The feeder limit represents a permitted aggregate import level in this simplified model. It is not a complete model of cable heating, phase imbalance, voltage drop or protection behaviour. GridSathi can report importlimit violations without claiming to calculate actual feeder voltage. 

### **Islanded operation** 

Islanded operation means a local electrical system is disconnected from the upstream network but continues supplying supported circuits. The GridSathi model allows this only when an island-capable physical installation is assumed. A battery and software alone cannot safely energize an arbitrary disconnected public feeder. 

A real installation would need suitable inverters, isolation and transfer equipment, electrical protection and qualified commissioning. GridSathi is a supervisory energy scheduler. It does not replace the fast inverter controls that regulate voltage and frequency, or the protective equipment that disconnects unsafe circuits. 

### **The assets have different roles** 

|**Asset**|**What the model tracks**|
|---|---|
|Solar generation|Available power and the portion used or curtailed|
|Shared battery|Stored energy, reserve, efficiency and power limits|
|Grid connection|Availability and permitted import or export|
|Fixed loads|Requested and actually served power by priority|
|Flexible tasks|Required energy, deadline, power limit and consent|
|Local controller|Observations, plans and command authority; no generation|



Wind or a fuel-powered generator can be optional assets, but they must have explicit availability and operating assumptions. A backup source is never treated as free, unlimited electricity. The simplest coherent prototype can use solar, one shared battery and a constrained grid connection. 

GridSathi  |  3 

## **3 Architecture and component responsibilities** 

GridSathi separates the physical world from the software that observes and controls it. In a prototype, the simulator owns the physical truth. The controller receives only the observations and forecasts that would be available at that moment. This separation prevents the controller from using future information to manufacture a good result. 

|**Component**|**Receives**|**Produces**|
|---|---|---|
|Scenario engine|Profiles, faults and asset configuration|Realized conditions for each interval|
|Asset model|Conditions and accepted commands|Actual service, battery state and losses|
|Telemetry layer|Meter and asset observations|Validated readings with freshness labels|
|Forecaster|Historical readings and allowed inputs|Demand and generation estimates|
|Scheduler|Current state, forecasts and constraints|A time-bounded proposed dispatch plan|
|Authority and safety<br>gate|Plan, active authority and local limits|Accepted or rejected setpoints|
|Evaluator|Actual results and run configuration|Reliability and cost comparisons|
|Backend and dashboard|Observations, plans, results and events|Operator views and permitted controls|



### **Three different flows** 

Energy flows through the electrical installation: generation and imports supply loads or charge storage. Data flows from meters and asset models into the controller. Commands flow from an authorized coordinator to actuators. Drawing these separately matters because a communications link does not imply an electrical connection between two houses. 

### **Where computation lives** 

The proposed operating model places essential scheduling and fallback capability on a local gateway, with standby controllers for recovery. Internet access supports reporting or remote supervision but is not required for every control cycle. A disconnected browser should not stop the local energy policy. 

A single-machine simulation can represent several controllers and communication links. That is useful for repeatable experiments but is not evidence of a deployed distributed system. The architecture allows a transport adapter to later replace in-memory messages without changing the energy-accounting rules. 

### **Why these boundaries matter** 

The scheduler can request an action that later becomes impossible. A battery might be unavailable, a message might arrive too late or a resident might withdraw consent. The asset result, not the proposed plan, determines the service metrics. Recording requested, accepted and actual actions makes that distinction visible. 

GridSathi  |  4 

## **4 The complete operating cycle** 

The reference energy schedule advances in five-minute intervals. This interval is a design choice for planning and evaluation, not an electrical protection response time. Communications events can run on a separate, finer clock. Changing dashboard playback speed never changes how much simulated energy a device consumes. 

### **Step 1 Observe and validate** 

At the beginning of an interval, the system obtains demand readings, available renewable power, battery state, grid status and unfinished tasks. Each reading has an asset identifier, units, event time, sequence number and quality flag. Duplicate readings are ignored. Old or missing data is marked stale rather than interpreted as zero consumption. 

### **Step 2 Estimate what is coming** 

The forecaster produces a demand and generation trajectory over the next few hours. It records when the forecast was issued and how uncertain it is. The scheduler combines that trajectory with known deadlines, power limits and available battery energy to identify likely shortages. 

### **Step 3 Construct a feasible plan** 

The scheduler first preserves critical service as far as feasible. It then allocates normal demand and flexible jobs according to the configured priorities. It chooses charging or discharging and considers later demand, task deadlines and a terminal energy target. It does not simply empty the battery whenever there is a small current deficit. 

### **Step 4 Validate and apply the immediate action** 

The controller sends only the first interval of the plan for execution. The actuator authority gate checks the sender, controller epoch, validity time and duplicate identifier. Local checks enforce device limits and current consent. An acknowledgement reports what was accepted and why anything was rejected. 

### **Step 5 Measure the outcome** 

The environment reveals the actual generation and demand for the interval. The physical model computes delivered energy, curtailed output, imports, battery losses and remaining task energy. The evaluator records any unmet demand. The controller cannot revise these actual results to match its forecast. 

### **Step 6 Replan** 

The next cycle starts from the resulting state, not from the state the controller hoped to reach. If a cloud reduced generation more than expected, the new battery measurement and demand observations enter the next plan. Repeating this process is called rolling-horizon control: plan ahead, execute a small part, then plan again. 

Every cycle produces an audit trail containing the observations used, forecast version, proposed plan, validation outcome and actual result. An operator can therefore answer both “What did GridSathi decide?” and “What actually happened?” 

GridSathi  |  5 

## **5 Energy accounting and battery logic** 

### **Power and energy are different** 

Power is the rate at which electricity is produced or consumed, measured in kilowatts. Energy is the amount accumulated over time, measured in kilowatt-hours. A 6 kW load running for half an hour consumes 3 kWh. A five-minute interval is one twelfth of an hour, so a constant 12 kW load consumes 1 kWh in that interval. 

A battery has both an energy capacity and a power limit. A 20 kWh battery with a 5 kW discharge limit cannot provide 10 kW just because it contains enough energy. Both constraints must be checked independently. 

### **Stored energy and reserve** 

State of charge, or SOC, is stored energy expressed as a percentage of usable capacity. With a 20 kWh modeled capacity and 12 kWh stored, SOC is 60 percent. The model also records minimum stored energy, maximum stored energy and charging and discharging limits. 

Separate a hard device minimum from a discretionary planning reserve. The hard minimum is never violated. A planning reserve is energy intentionally held for future uncertainty; a documented emergency policy may release some of it to protect current critical service. Calling both values “minimum SOC” would hide an important decision. 

### **Efficiency and state updates** 

Charging does not store every kWh received from the AC bus. At 90 percent charging efficiency, 2 kWh delivered to the battery adds 1.8 kWh to stored energy. At 90 percent discharge efficiency, delivering 1.8 kWh to the loads removes 2 kWh from storage. These values are illustrative, not assumed specifications for every battery. 

For each interval, the model adds the energy stored from charging and subtracts the stored energy required for discharge. It forbids simultaneous charging and discharging. The requested setpoint is limited before execution; clamping a negative energy balance after execution would hide physically impossible service. 

### **Conservation at the shared electrical bus** 

In every interval, energy entering the bus from used renewables, imports and battery discharge must equal energy sent to served loads, battery charging, exports and explicitly modeled network losses. Available renewable generation is split into used and curtailed generation. Battery efficiency losses are reflected in stored-energy changes and must not be counted again as network losses. 

Suppose loads require 8 kW, solar supplies 3 kW and imports are capped at 2 kW. The remaining 3 kW must come from an available battery or become unmet or legitimately deferred demand. A controller node never supplies the missing power itself. 

A full battery blocks further charging. An empty or reserve-limited battery blocks discharge. If resources run out, the result is a service shortfall with an explicit quantity, not a fictitious backup contribution. 

GridSathi  |  6 

## **6 Forecasting and uncertainty** 

The forecaster estimates future demand and renewable generation. The scheduler uses those estimates to decide when energy should be saved, when tasks can run and whether available flexibility can cover an expected shortfall. A forecast is an input to a decision, not a guarantee. 

### **Inputs and outputs** 

Demand inputs can include recent consumption, time of day, day type and known task requests. Solar inputs can include recent output, the daylight pattern and available weather forecasts. A weather forecast is permitted only if it was available at the decision time. Actual future weather from the simulator is not permitted. 

The output contains a sequence of expected kW values for each future interval, the issue time, horizon, model version and uncertainty information. The system forecasts the demand and generation quantities consistently with the asset model; it must not subtract flexible demand twice by treating it as both forecast background load and a separate task. 

### **A simple model is a valid starting point** 

A persistence model assumes the near future resembles the latest observation. A profile model uses typical behaviour for the time of day. Solar estimates must respect the configured night period. A learned model can use lagged readings and calendar/weather features, but extra complexity is justified only if evaluation shows useful improvement. 

If a learned model is used, training data comes before validation and test data in time. Preprocessing is fitted on training data only. Randomly mixing future intervals into training can make forecast accuracy look better than a real deployment would achieve. 

### **How uncertainty changes the plan** 

An optimistic solar estimate may lead the system to release battery energy too early. GridSathi therefore evaluates conservative generation or higher-demand cases when setting its planning reserve. This may be implemented through a reserve margin or a small set of forecast scenarios. It is a tradeoff: more reserve can protect future service but postpone more current tasks. 

The dashboard can show an expected shortage window and a range rather than one falsely precise prediction. A forecast-error alert compares realized values with predictions and prompts replanning. Stale forecasts are replaced by a simpler profile or persistence fallback with a visible quality label. 

### **How forecasts are evaluated** 

Mean absolute error measures the average size of prediction errors in kW. Normalized errors need a stated denominator. Ordinary percentage error is problematic when actual solar output is zero, so night periods must not generate misleading percentages. 

Forecast accuracy is not the final success metric. Two models can have similar average error yet differ at the one evening interval that matters for essential service. GridSathi therefore compares downstream energy not served, battery behaviour and task completion using each forecasting method. 

GridSathi  |  7 

## **7 The dispatch decision** 

Dispatch means assigning operating power to controllable assets and loads. At each cycle, GridSathi asks which combination of actions gives the best feasible service over the planning horizon, given the information available now. 

### **Decision variables** 

The scheduler chooses battery charge/discharge power, grid import/export, renewable curtailment, served fixed demand and the power allocated to each flexible task. These choices are made for every interval in the horizon, while only the first interval is executed immediately. 

### **Constraints** 

The plan must conserve energy, respect battery energy and power limits, obey the import/export limits and honor device availability. A task cannot start before its release time, exceed its power rating or claim completion without receiving its required energy. Opted-out tasks are not treated as freely controllable resources. 

Some constraints express preferences, such as a completion deadline or a fairness target, that may become impossible during a long outage. Instead of failing silently, the scheduler represents an explicit violation and gives it a stated priority. Physical constraints remain hard limits. 

### **Objective ordering** 

The intended hierarchy is to minimize critical unmet energy first, then other unmet service and important task violations, and then operating cost, feeder peaks and battery wear. This can be implemented as successive optimization stages. If a weighted objective is used, weights and units must be documented so a small cost saving cannot accidentally outweigh essential service. 

A battery terminal target tells the optimizer that energy remaining at the end of its horizon still matters. Without that target or another future-energy valuation, it may drain storage just before the horizon ends and appear effective while creating a shortage immediately afterward. 

### **Why the best decision is not always immediate discharge** 

If a pump can run later and an essential shortfall is expected soon, preserving battery energy can be better than meeting the pump request immediately. If the grid is healthy and sufficient power is available, running the pump now may avoid a later conflict. The right action depends on the complete state and service obligations, not a rule that always delays optional loads. 

### **Solver failure and fallback** 

A bounded optimization time prevents an old plan from arriving too late. If no valid plan is available, a deterministic fallback serves critical loads first, respects all battery/grid limits, postpones only eligible tasks and reports shortages. It may use a conservative planning reserve. Fallback is deliberately simple enough to test independently. 

Every accepted action records its reason: for example, “EV delayed until 21:00 because the expected essentialservice deficit requires the available reserve.” The explanation comes from the decision state and constraints; it does not require an LLM to invent a narrative. 

GridSathi  |  8 

## **8 Flexible loads priorities and fair access** 

A flexible load is a service whose timing or rate may change within agreed limits. GridSathi manages the service obligation rather than pretending the demand disappeared. Consent and operating constraints define the amount of flexibility actually available. 

### **A task example** 

An EV requests 6 kWh between 18:00 and 23:00 and accepts charging up to 3 kW. At that power it needs two hours in total. The scheduler can allocate four half-hour slots or another valid pattern if interruption is allowed. Each completed interval reduces remaining energy. A zero-power interval is a delay, not an energy saving. 

If only one hour remains before the deadline and 6 kWh is still needed, the task is infeasible at 3 kW. The system exposes the maximum deliverable energy and expected missed requirement. It must not label the EV fully charged or keep pushing its deadline forward invisibly. 

### **Service constraints determine flexibility** 

A water pump may be deferred while a tank contains enough water. The tank level, withdrawal estimate and minimum service level determine the latest safe start. A refrigerator cannot simply be switched off because it is a household appliance; flexible control would need a validated temperature model and appropriate consent. Without that model it remains a fixed load. 

Some tasks require uninterrupted operation or minimum on/off periods. These constraints either enter the scheduler or the task is excluded from automated flexibility. A prototype should support a small set of welldefined devices before claiming universal appliance control. 

### **Allocation during shortages** 

Critical circuits receive the highest service priority. Remaining energy is distributed using transparent rules, such as a cap on consecutive curtailment and a record of each household’s recent served fraction. Rotating curtailment applies only to noncritical controllable service, not blindly to medical or safety-critical circuits. 

Fairness may conflict with efficiency. Serving one large task can maximize delivered kWh while repeatedly denying small households. GridSathi reports worst-served users and service disparity alongside total energy, so aggregate gains cannot hide this outcome. 

### **Opt out and override** 

A resident may withdraw permission for future scheduling. The next plan removes that discretionary flexibility and checks feasibility again. Withdrawing consent does not guarantee electricity during a physical shortage; the product must explain that distinction. An operator override is logged with identity, scope and expiry and cannot bypass the battery’s hard limits. 

After a shortage, delayed tasks are released gradually. Starting every postponed device at once can create a rebound peak. GridSathi therefore schedules recovery as another constrained demand period rather than resetting all tasks to “on.” 

GridSathi  |  9 

## **9 Coordination and command authority** 

Resilience requires more than displaying a replacement leader. GridSathi must prevent two controllers from issuing conflicting accepted commands to shared equipment. It separates information sharing, coordinator selection and the authority to actuate. 

### **Information sharing** 

Controllers exchange observations about demand, generation, task progress and equipment availability. Gossip is one possible method: each node periodically shares recent records with a few peers. Repeated exchanges spread information without requiring every update to travel directly through one coordinator. 

Each record retains its originating asset and version. Event timestamps determine freshness. Logical clocks can help order distributed events, but a larger logical clock does not prove a meter reading is recent in real time. Gossip may temporarily produce different views, so critical command checks still use local device state. 

### **Coordinator selection** 

The design uses a fixed set of eligible controllers with heartbeats to detect a missing coordinator. For a concrete prototype, three controller processes can model a majority rule: two must agree before a candidate is authorized for a new term. A controller isolated from the majority cannot independently assume command authority. 

The implementation must use a tested leader-authority mechanism or a precisely specified simulation of it. Heartbeats and an election label alone are not a full consensus protocol. If a safe authority mechanism is unavailable, the system remains in local fallback rather than claiming automatic distributed control. 

### **Actuator authority gate** 

A command contains a unique ID, asset ID, epoch or term, issue time, expiry time and setpoint. A new term is installed only through the configured authorization mechanism. The actuator gate rejects old terms, expired instructions, duplicate commands and unauthorized senders. Merely supplying a larger integer is not enough to become the new controller. 

If leases are used to bound authority in time, clock and expiration assumptions are explicit. When authority expires, the actuator applies its local fallback. A recovered former leader cannot continue controlling equipment using delayed commands from its old term. 

### **State recovery** 

Standby controllers retain task progress, the latest accepted command IDs, policy configuration and recent observations. After failover, the new coordinator reads current battery and actuator telemetry before planning. Restoring an old snapshot must not restore old battery energy or repeat a task that has already consumed electricity. 

This design still depends on the physical actuator and its safety gate. Replicated schedulers do not eliminate every hardware failure point. The prototype must disclose which failures are tolerated and which cause reduced or stopped service. 

GridSathi  |  10 

## **10 Failure handling and operating modes** 

GridSathi classifies failures by what has stopped working. A communications outage does not mean generation is zero. A controller crash does not mean the electrical grid has failed. A battery fault does not mean the remaining loads have disappeared. 

|**Condition**|**Control response**|**What remains visible**|
|---|---|---|
|Upstream outage|Set imports to zero; use islanded model only<br>where supported|Available local energy and unmet demand|
|Cloud or generation loss|Revise available supply and replan|Forecast error and service impact|
|Stale battery telemetry|Remove uncertain dispatch capability or use<br>validated local fallback|Unknown state rather than false SOC|
|Coordinator failure|Local fallback while valid replacement<br>authority is established|Detection and recovery events|
|Network partition|Minority loses coordinated authority; local<br>safety remains|Affected nodes and operating limits|
|Solver timeout|Reject late plan and use deterministic<br>fallback|Solver status and fallback action|
|Battery unavailable|Remove its charge/discharge capacity from<br>the plan|Asset fault and unavoidable shortfall|
|Dashboard disconnected|Continue local operations and retain events|A visible stale-data label on reconnect|



### **Mode transitions** 

Normal coordinated mode requires fresh-enough inputs and valid controller authority. Degraded mode uses reduced flexibility or conservative estimates when some information is missing. Local fallback takes over when coordinated authority or planning is unavailable. Resource exhaustion is a separate physical condition that can occur in any of these modes. 

Returning to coordinated mode requires state reconciliation, valid authority and fresh telemetry. The controller verifies actual task progress and battery energy, computes a new plan, and sends bounded commands. It does not replay a queue of expired instructions. 

### **Avoiding oscillation** 

A noisy threshold should not repeatedly switch the system between modes. Separate entry and exit thresholds or require a short period of stable observations before recovery. Record these timing choices so recovery measurements are reproducible. Safety-critical local protection remains independent of these supervisory delays. 

If a fault prevents critical service, the dashboard reports the missing power and energy, affected service class and limiting resource. It must never display “stable” merely because the scheduler has stopped requesting power for the disconnected loads. 

GridSathi  |  11 

## **11 A worked energy management example** 

Consider a simplified local microgrid during an upstream outage. It has no solar generation during the next two hours. The battery contains 10 kWh, with a hard minimum of 2 kWh and a 5 kW discharge limit. For this calculation only, discharge efficiency is 100 percent. Therefore 8 kWh can be delivered before the hard minimum is reached. 

Essential fixed demand is 4 kW for two hours, requiring exactly 8 kWh. An eligible pump also needs 2 kWh, can run at 1 kW and has a deadline after the outage ends. Total requested energy exceeds the available battery energy if the pump runs during the outage. 

### **Two feasible policies with different outcomes** 

A reactive policy may serve both loads while power and energy permit, then shed the pump first when constraints bind. A forecast-aware policy recognizes that the entire usable battery is needed for essential demand, so it defers the pump from the start. The table uses one-hour reporting intervals for readability, not the five-minute reference control interval. 

|**Interval**|**Reactive policy**|**Forecast aware policy**|
|---|---|---|
|Start|10 kWh stored|10 kWh stored|
|Hour 1|4 kWh essential + 1 kWh pump; 5 kWh remain|4 kWh essential; 6 kWh remain|
|Hour 2|Only 3 kWh usable; pump deferred; 1 kWh<br>essential unmet|4 kWh essential; 2 kWh remain|
|End of outage|7 of 8 kWh essential supplied; pump needs 1<br>kWh|8 of 8 kWh essential supplied; pump needs 2<br>kWh|
|After restoration|Complete remaining 1 kWh pump obligation|Complete remaining 2 kWh pump obligation|



Both policies have used the same 8 kWh of battery energy and respected the same power limit. The difference is allocation over time: the forecast-aware policy preserved essential service by delaying a task whose deadline allowed it. It did not create extra energy or eliminate the pump’s consumption. 

### **What changes when assumptions change** 

At 90 percent discharge efficiency, 8 kWh of usable stored energy delivers only 7.2 kWh to loads. Even the forecast-aware policy then leaves 0.8 kWh of essential demand unmet. If the outage lasts three hours, more essential energy is needed. If the pump cannot be delayed because its tank is empty, the controller faces a different service conflict. 

This is a teaching example, not a benchmark result or a guarantee that every reactive controller behaves this way. A serious evaluation also compares against competent reserve-aware rules using identical assets. Forecasting is valuable only where it changes a decision usefully and without hidden advantages. 

GridSathi  |  12 

## **12 Backend data model and user experience** 

The backend separates configuration, telemetry, decisions and results. An immutable scenario identifier and configuration hash allow each run to be reproduced. 

### **Core records** 

|**Record**|**Important fields**|
|---|---|
|Asset|ID, type, capacity, operating limits, availability and topology|
|Observation|Asset, timestamp, units, value, origin sequence and quality|
|Task|Owner, consent, release, deadline, required and remaining energy|
|Forecast|Issue time, horizon, interval values, uncertainty and version|
|Plan|Run, authority term, setpoints, constraints, reasons and validity|
|Actuation|Command ID, acceptance, actual setpoint and rejection reason|
|Step result|Delivered energy, unmet demand, SOC, losses and task progress|
|Run manifest|Code/config/data versions, controller, seed and outputs|



### **Backend workflow** 

A Python service hosts the simulator and typed API. Users create runs, choose scenarios and controllers, retrieve snapshots, inject permitted demo faults and export results. Experiments run separately from request handling, with isolated state for each run. 

The browser polls for results without recomputing energy logic. Pause and playback controls affect progression, not the duration used in energy calculations. 

### **What the operator sees** 

The primary screen shows critical service, supply, SOC, predicted shortfalls and accepted actions. Comparison views align baseline and GridSathi traces. The utility view shows aggregate demand and requested versus delivered flexibility. Diagnostics expose controller health, delays and recovery. 

Displays distinguish actual, forecast and unknown values. A sent command becomes a confirmed action only after acknowledgement or measurement. Exports retain units, assumptions and run identifiers. 

### **Privacy and access** 

Residents should not see other households’ detailed usage. Utilities receive aggregate information where authorized. Operators have role-limited controls, and overrides are auditable. Authentication, bounded requests, safe configuration parsing and retention controls are required before an externally accessible deployment. A local demo must not be presented as having production security merely because it exposes an API. 

GridSathi  |  13 

## **13 How the project proves its value** 

GridSathi needs evidence that its decisions improve service, not merely that the dashboard moves. Evaluation runs multiple controllers against the same realized generation, demand, faults, assets, starting battery state and resident participation constraints. 

### **Baselines and comparisons** 

A no-storage reference helps explain the value of adding equipment, but cannot isolate the value of control software. The primary baseline is a competent rule-based controller with the same equipment: it prioritizes critical demand, charges on surplus, discharges within limits and schedules eligible tasks using a documented rule. A reserve-aware rule is an important additional comparison. 

The proposed controller must not receive perfect future data while the baseline receives noisy observations. A perfect-forecast run can be included as a labeled upper-bound experiment. Final battery energy and unfinished tasks are reported or equalized so one controller cannot win by consuming all resources just before evaluation stops. 

### **Metrics with precise meanings** 

Energy not served is the sum of unmet power multiplied by interval duration, expressed in kWh. Critical energy served percentage divides delivered critical energy by requested critical energy. Time availability instead counts intervals in which the defined service is fully met; it is a different quantity. 

Peak import is the largest interval-average grid import. Flexible-service metrics include completed jobs, missed energy, delay and rebound peaks. Fairness metrics include the worst served household and longest curtailment. Recovery metrics separate failure detection from the time to the first valid accepted replacement command. 

A zero baseline shortage makes percentage reduction undefined; report absolute change instead. Aggregate shortfall duration should not be labeled as a measured utility reliability index without customer-level interruption data and the appropriate definition. 

### **Experiment set** 

Test normal operation, sudden renewable loss, prolonged upstream outage, controller failure, communication partition, battery unavailability and flexible-load arrival. Include cases with low initial SOC and poor forecasts. Repeat stochastic cases with several seeds and report sample counts, ranges and failures, not just the best run. 

Ablation experiments remove one capability at a time: forecasting, flexibility or coordinated recovery. They reveal which component causes a benefit. Sensitivity experiments vary battery size, outage duration and participation to show where the design stops being effective. 

### **Correctness before claims** 

Tests must enforce energy conservation, SOC and power bounds, no future-data leakage, consent rules, deadline accounting and stale-command rejection. A repeated run with the same configuration should produce the same energy results. Measured prototype outcomes remain simulated evidence until independent physical testing supports field claims. 

GridSathi  |  14 

## **14 Ownership affordability and sustainability** 

A plausible operating model is a community cooperative or energy-service provider managing shared assets. A trained operator handles routine checks and service requests; qualified electrical personnel handle installation and battery or protection faults. The exact ownership model is a proposed deployment choice, not an established partnership. 

### **Who pays and what they receive** 

Costs include storage, inverter and isolation equipment where needed, metering, gateway, installation, communications, maintenance, battery replacement and end-of-life handling. Existing-asset retrofits and new installations have different economics. Low software cost does not imply that a complete electrical installation is inexpensive. 

Residents could pay a membership or service fee under an agreed model. The cost analysis divides annualized costs among participating users and compares the service obtained, including essential-service duration. It reports who funds upfront capital and who bears replacement risk. It must not assume that every home owns solar panels or can purchase a battery. 

### **Economic calculations** 

The model records every input’s unit, source or assumption label, date and plausible range. It estimates annual operating cost, annualized capital cost, cost per participating household and cost per unit of useful service. Low, base and high cases show how battery life, utilization and participation affect affordability. 

Cash bill savings are distinct from the economic value of avoiding a shop interruption. Do not count the same benefit twice. A demand-response payment is included only in a clearly labeled scenario where such a payment is available. A no-incentive case reveals whether affordability depends entirely on an uncertain revenue source. 

### **Maintenance and accountability** 

An operating plan identifies who responds to communications faults, checks battery health, updates software and reviews unfair allocation complaints. Device limitations, overrides and incidents are retained in an audit trail. Residents need a clear way to withdraw discretionary participation and understand service limitations during shortages. 

### **Sustainability boundaries** 

Using more available renewable energy may reduce curtailment, but battery cycling also causes losses and wear. Renewable utilization tracks the portion of available renewable generation actually used. Battery throughput is a wear proxy, not a validated lifetime prediction. 

Emissions estimates require explicit electricity or fuel emission factors and an accounting boundary. Battery discharge is not automatically zero-carbon or avoided emissions: the charging energy has an origin, and losses matter. A second-life battery scenario must account for usable capacity, testing, reliability and eventual recycling rather than assuming reuse is always superior. 

The project’s sustainability claim should therefore state what was measured or modeled, under which assumptions, and which lifecycle effects remain outside scope. 

GridSathi  |  15 

## **15 Key questions and the complete mental model** 

### **Is GridSathi an electricity generator** 

No. Generation assets produce electricity and the battery stores energy. GridSathi chooses feasible timing and allocation. Its benefit comes from using the same resources more effectively, not from creating additional supply. 

### **Why use forecasting if the system can react** 

Reaction handles a shortage after it appears. Forecasting can reveal that using energy now would prevent an essential service later. It is useful only when there are choices to make, such as a deferrable task or charge opportunity. Bad forecasts can hurt, which is why uncertainty, feedback and baseline evaluation matter. 

### **Why not install a larger battery** 

More storage may be the best choice in some settings. GridSathi should be compared with that alternative at an equivalent service target and cost. The project does not assume software always beats capacity expansion; it tests whether coordination reduces the capacity or cost needed for a particular service level. 

### **Is the system centralized or decentralized** 

It uses a local coordinated scheduler with distributed observations, standby controllers and device-level fallback. That is a hybrid architecture. Calling it fully decentralized would obscure the shared-battery authority gate and the coordination decisions that still require agreement. 

### **Does it require machine learning or an LLM** 

No. Forecasting can start with transparent profiles and persistence. Dispatch can use mathematical optimization or a tested heuristic. An LLM is not required for safety, scheduling or explanations. A learned forecast is an optional component whose benefit must be demonstrated. 

### **What happens when there simply is not enough energy** 

The system records an unavoidable shortfall, applies its agreed priority and fairness rules, and reports the limiting resources. It cannot guarantee all critical demand indefinitely. Safe, honest degradation is part of the design. 

### **What would make it a real deployment** 

The software would need validated adapters, physical metering, compatible controls, engineered protection, cybersecurity review, operational procedures and field testing. The simulator demonstrates the scheduling logic under declared assumptions. It does not certify electrical safety, voltage control or real-world reliability. 

### **GridSathi in one connected explanation** 

GridSathi observes a defined local energy system, estimates upcoming supply and demand, and schedules storage and consenting loads within physical limits. An authority gate checks commands, local devices apply bounded actions, and measurements show what was actually delivered. The system replans as conditions change, falls back when coordination fails and evaluates its value against equivalent alternatives. Its central promise is better-informed allocation of limited energy, with evidence and limits made visible. 

GridSathi  |  16 

