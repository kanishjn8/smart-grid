from __future__ import annotations
import unittest
from datetime import datetime
from unittest.mock import patch
from pydantic import ValidationError
from fastapi.testclient import TestClient
from dashboard import create_app
from src.domain import Assets, Battery, Scenario, Task, Observation, DispatchPlan, Fault
from src.scenarios import build, profile, SCENARIOS
from src.forecasting import forecast
from src.coordination import AuthorityGate, Transport
from src.evaluation.runner import Runner, compare
from src.evaluation.economics import CostInputs, annualized


def tiny(**changes):
    data=dict(id="fixture",interval_minutes=60,assets=Assets(battery_kwh=10,initial_soc=1,reserve_soc=0,
              eta_charge=1,eta_discharge=1,grid_limit_kw=0,pv_kw=0),critical_kw=(2.,2.),normal_kw=(4.,4.),
              pv_kw=(0.,0.),wind_kw=(0.,0.),grid_kw=(0.,0.))
    data.update(changes)
    return Scenario(**data)


def command(**changes):
    values=dict(issued_round=0,expires_round=2,epoch=1,sequence=0,battery_kw=2,task_kw={},reason="test",controller="B1")
    values.update(changes)
    return DispatchPlan(**values)


class ContractTests(unittest.TestCase):
    def test_invalid_inputs(self):
        for change in ({"battery_kwh":-1},{"eta_charge":0},{"initial_soc":.01},{"pv_kw":float('nan')}):
            with self.assertRaises(ValidationError): Assets(**change)
        for change in ({"pv_kw":(1.,)},{"normal_kw":(-1.,2.)},{"start":datetime(2026,1,1)},
                       {"tasks":(Task(id="late",required_kwh=1,release_step=0,deadline_step=3,max_kw=1),)}):
            with self.assertRaises(ValidationError): tiny(**change)

    def test_night(self):
        for hour in (0,3,6,18,20,23):
            self.assertEqual(profile(hour,100)[2],0)


class PlantTests(unittest.TestCase):
    def test_hand_calculated_energy_priority(self):
        r=Runner(tiny(),"B1").run()
        self.assertAlmostEqual(r["metrics"]["critical_ens_kwh"],0)
        self.assertAlmostEqual(r["metrics"]["total_ens_kwh"],2)
        self.assertAlmostEqual(r["metrics"]["terminal_battery_kwh"],0)
        self.assertEqual(r["series"][1]["critical_served_kw"],2)
        self.assertEqual(r["series"][1]["normal_served_kw"],2)

    def test_efficiency_full_empty_and_bounds(self):
        a=Assets(battery_kwh=10,initial_soc=1,reserve_soc=.1,eta_charge=.8,eta_discharge=.9)
        b=Battery(a)
        self.assertEqual(b.apply(-100,1),0)
        self.assertAlmostEqual(b.apply(100,1),8.1)
        self.assertAlmostEqual(b.energy,1)
        self.assertEqual(b.apply(100,1),0)
        self.assertAlmostEqual(b.apply(-100,1),-11.25)
        self.assertAlmostEqual(b.energy,10)
        self.assertEqual(b.apply(10,1,False),0)
        with self.assertRaises(ValueError):b.apply(float('nan'),1)

    def test_every_scenario_conservation_and_constraints(self):
        for name in SCENARIOS:
            for controller in ('B0','B1','P'):
                scenario=build(name,3)
                run=Runner(scenario,controller).run()
                for row in run['series']:
                    self.assertLess(abs(row['balance_residual_kw']),1e-7)
                    self.assertLessEqual(row['energy_kwh'],scenario.assets.battery_kwh+1e-7)
                    self.assertGreaterEqual(row['energy_kwh'],scenario.assets.battery_kwh*scenario.assets.reserve_soc-1e-7)
                    self.assertEqual(row['charge_kw']*row['discharge_kw'],0)
                    self.assertEqual(row['grid_import_kw']*row['grid_export_kw'],0)
                    self.assertLessEqual(row['grid_import_kw'],row['grid_limit_kw']+1e-7)
                    self.assertLessEqual(row['charge_kw'],scenario.assets.charge_kw)
                    self.assertLessEqual(row['discharge_kw'],scenario.assets.discharge_kw)

    def test_isolation_and_unavailability(self):
        s=tiny(assets=Assets(battery_kwh=10,initial_soc=1,island_capable=False,grid_limit_kw=0,pv_kw=0))
        self.assertEqual(Runner(s,'B1').run()['metrics']['served_kwh'],0)
        s=tiny(faults=(Fault(kind='battery_unavailable',start_step=0,end_step=2),))
        self.assertEqual(Runner(s,'B1').run()['metrics']['served_kwh'],0)

    def test_optout_is_not_rescheduled_and_terminal_misses_count(self):
        s=tiny(assets=Assets(battery_kwh=0,grid_limit_kw=10,pv_kw=0), critical_kw=(0.,0.),normal_kw=(0.,0.),
               grid_kw=(0.,10.),tasks=(Task(id='optout',required_kwh=2,release_step=0,deadline_step=2,max_kw=2,consent=False),))
        r=Runner(s,'P').run()
        self.assertEqual(r['metrics']['flexible_missed_kwh'],2)
        self.assertEqual(r['metrics']['total_ens_kwh'],2)
        self.assertEqual(r['series'][1]['flexible_requested_kw'],0)

    def test_zero_denominators(self):
        r=Runner(tiny(critical_kw=(0.,0.),normal_kw=(0.,0.)),'B1').run()
        self.assertIsNone(r['metrics']['critical_availability_pct'])
        self.assertIsNone(r['metrics']['renewable_utilization_pct'])
        self.assertIsNone(compare(tiny(critical_kw=(0.,0.),normal_kw=(0.,0.)))['delta']['ens_reduction_pct'])


class ForecastAndReplayTests(unittest.TestCase):
    def test_no_future_access(self):
        s=tiny()
        r1=Runner(s,'P'); r1.step()
        changed=s.model_copy(update={'normal_kw':(4.,400.)})
        r2=Runner(changed,'P');r2.step()
        self.assertEqual(r1.forecasts,r2.forecasts)
        self.assertEqual(r1.rows,r2.rows)

    def test_determinism_pause_and_pairing(self):
        s=build('coordinator_failure',9)
        r=Runner(s,'P'); r.step();r.paused=True
        self.assertIsNone(r.step());self.assertEqual(len(r.rows),1)
        r.paused=False
        one=r.run();two=Runner(s,'P').run()
        self.assertEqual(one,two)
        pair=compare(s)
        self.assertEqual(pair['baseline']['manifest']['scenario_hash'],pair['proposed']['manifest']['scenario_hash'])

    def test_invalid_controller_and_packet_loss_fallback(self):
        r=Runner(tiny(),'P',loss=1).run()
        self.assertEqual(r['metrics']['fallback_intervals'],2)
        from src.control import dispatch
        def broken(controller,*args,**kwargs):
            if controller=='P':raise ValueError('invalid heuristic output')
            return dispatch(controller,*args,**kwargs)
        with patch('src.evaluation.runner.dispatch',side_effect=broken):
            r=Runner(tiny(),'P').run()
        self.assertEqual(r['metrics']['fallback_intervals'],2)
        self.assertEqual(r['metrics']['critical_ens_kwh'],0)


class AuthorityTests(unittest.TestCase):
    def test_stale_duplicate_expired_and_partition(self):
        gate=AuthorityGate()
        self.assertTrue(gate.accept(command(),0)[0])
        self.assertFalse(gate.accept(command(),0)[0])
        self.assertFalse(gate.accept(command(sequence=1),3)[0])
        self.assertFalse(gate.accept(command(sequence=1),1,False)[0])
        self.assertTrue(gate.failover(3))
        self.assertFalse(gate.accept(command(sequence=2),3)[0])
        self.assertTrue(gate.accept(command(epoch=2,issued_round=3,expires_round=5,sequence=3),3)[0])

    def test_transport_duplication_reordering(self):
        t=Transport(7,duplicate=1,delay_rounds=3)
        for i in range(4):t.send(command(sequence=i,expires_round=20),0)
        packets=t.receive(10)
        self.assertEqual(len(packets),8)
        gate=AuthorityGate()
        accepted=[p.sequence for p in packets if gate.accept(p,1)[0]]
        self.assertEqual(accepted,sorted(set(accepted)))
        t.send(command(),10,partition=True)
        self.assertEqual(t.receive(20),[])

    def test_failure_recovers_and_partition_falls_back(self):
        failure=Runner(build('coordinator_failure'),'P').run()
        self.assertGreater(failure['metrics']['rejected_commands'],0)
        self.assertTrue(any(e['event']=='failure_detected_and_replacement_granted' for e in failure['events']))
        partition=Runner(build('partition'),'P').run()
        self.assertEqual(partition['metrics']['fallback_intervals'],24)
        self.assertTrue(all(r['actuation']['actual_kw']<=50 for r in partition['series']))


class EconomicsTests(unittest.TestCase):
    def test_zero_discount_hand_calculation(self):
        c=CostInputs(pv_inr_per_kw=0,battery_inr_per_kwh=0,inverter_inr=1200,protection_isolation_inr=0,
                     meters_inr=0,gateway_inr=0,installation_inr=0,annual_connectivity_inr=0,annual_operator_inr=0,
                     annual_maintenance_fraction=0,recycling_inr=0,discount_rate=0,lifetime_years=10,households=1)
        r=annualized(Assets(),c)
        self.assertEqual(r['annualized_system_cost_inr'],120)
        self.assertEqual(r['household_monthly_inr'],10)
        self.assertIsNone(r['inr_per_avoided_unserved_kwh'])


class RunApiTests(unittest.TestCase):
    def test_lifecycle_validation_and_export(self):
        with TestClient(create_app()) as c:
            self.assertEqual(len(c.get('/api/scenarios').json()),7)
            self.assertEqual(c.post('/api/runs',json={'scenario':'bad'}).status_code,422)
            self.assertEqual(c.post('/api/runs',json={'assets':{'battery_kwh':-2}}).status_code,422)
            id=c.post('/api/runs',json={}).json()['id']
            c.post(f'/api/runs/{id}/control',json={'action':'step','steps':4})
            c.post(f'/api/runs/{id}/control',json={'action':'pause'})
            result=c.post(f'/api/runs/{id}/control',json={'action':'step'}).json()
            self.assertEqual(len(result['series']),4)
            c.post(f'/api/runs/{id}/control',json={'action':'resume'})
            final=c.post(f'/api/runs/{id}/control',json={'action':'complete'}).json()
            self.assertEqual(final,c.get(f'/api/runs/{id}/export').json())
            c.post(f'/api/runs/{id}/control',json={'action':'reset'})
            again=c.post(f'/api/runs/{id}/control',json={'action':'complete'}).json()
            self.assertEqual(final,again)
            c.delete(f'/api/runs/{id}')
            self.assertEqual(c.get(f'/api/runs/{id}').status_code,404)

    def test_comparison_and_economics(self):
        with TestClient(create_app()) as c:
            pair=c.post('/api/comparisons',json={}).json()
            self.assertEqual(pair['baseline']['scenario'],pair['proposed']['scenario'])
            exported=c.get('/api/comparisons/'+pair['id']).json()
            self.assertEqual(pair['proposed']['metrics'],exported['proposed']['metrics'])
            self.assertEqual(c.post('/api/economics',json={}).json()['status'],'assumed')


class AdditionalSafetyTests(unittest.TestCase):
    def test_telemetry_origin_sequence_and_expiry(self):
        from src.coordination import TelemetryStore
        store=TelemetryStore()
        self.assertTrue(store.merge('battery',2,10,{'energy':5}))
        self.assertFalse(store.merge('battery',1,20,{'energy':10}))
        self.assertEqual(store.read('battery',12,2),{'energy':5})
        self.assertIsNone(store.read('battery',13,2))

    def test_repeated_failures_get_new_epochs(self):
        scenario=build('normal').model_copy(update={'faults':(
            Fault(kind='controller_failure',start_step=10,end_step=12),
            Fault(kind='controller_failure',start_step=15,end_step=17))})
        result=Runner(scenario,'P').run()
        self.assertEqual(result['series'][-1]['authority_epoch'],3)
        self.assertEqual(len(result['metrics']['recovery_latency_rounds']),2)
        self.assertEqual(result['metrics']['detection_latency_rounds'],[2,2])
        self.assertTrue(all(e['reconciled_energy_kwh']>=0 for e in result['events'] if 'reconciled_energy_kwh' in e))

    def test_surplus_export_and_random_power_balance(self):
        import random
        rng=random.Random(71)
        for trial in range(12):
            asset=Assets(battery_kwh=rng.uniform(1,200),initial_soc=rng.uniform(.1,1),pv_kw=100,
                         grid_limit_kw=30,export_limit_kw=20,charge_kw=10,discharge_kw=8)
            scenario=Scenario(id=f'random-{trial}',assets=asset,critical_kw=tuple(rng.uniform(0,10) for _ in range(20)),
                              normal_kw=tuple(rng.uniform(0,60) for _ in range(20)),pv_kw=tuple(rng.uniform(0,100) for _ in range(20)),
                              wind_kw=(0.,)*20,grid_kw=tuple(rng.choice((0.,30.)) for _ in range(20)))
            run=Runner(scenario,'P').run()
            self.assertLess(run['metrics']['max_balance_residual_kw'],1e-7)
            for row in run['series']:
                self.assertEqual(row['grid_import_kw']*row['grid_export_kw'],0)
                self.assertLessEqual(row['grid_export_kw'],asset.export_limit_kw)
                self.assertAlmostEqual(row['renewable_available_kw'],row['renewable_used_kw']+row['curtailed_kw'])

    def test_injected_fault_export_replays_and_runs_are_isolated(self):
        with TestClient(create_app()) as client:
            a=client.post('/api/runs',json={}).json()['id']
            b=client.post('/api/runs',json={}).json()['id']
            client.post(f'/api/runs/{a}/control',json={'action':'step','steps':3})
            client.post(f'/api/runs/{a}/control',json={'action':'fault','fault':'partition','duration_steps':5})
            result=client.post(f'/api/runs/{a}/control',json={'action':'complete'}).json()
            self.assertEqual(client.get(f'/api/runs/{b}').json()['progress'],0)
            replay=Runner(Scenario.model_validate(result['scenario']),'P').run()
            self.assertEqual(replay['metrics'],result['metrics'])
            self.assertEqual(replay['series'],result['series'])


class SnapshotTests(unittest.TestCase):
    def test_export_is_an_independent_copy(self):
        runner=Runner(tiny(),'B1')
        runner.step()
        snapshot=runner.export()
        runner.step()
        self.assertEqual(len(snapshot['series']),1)
        snapshot['series'][0]['task_remaining_kwh']['new']=99
        self.assertNotIn('new',runner.rows[0]['task_remaining_kwh'])


class ReliabilityEvidenceTests(unittest.TestCase):
    def test_hand_calculated_interruption_and_window(self):
        scenario = tiny(assets=Assets(battery_kwh=0, pv_kw=0, grid_limit_kw=6),
                        grid_kw=(6., 0.))
        m = Runner(scenario, "B1").run()["metrics"]
        self.assertEqual(m["critical_interruption_hours"], 1)
        self.assertEqual(m["critical_availability_pct"], 50)
        self.assertEqual(m["scarcity_window_hours"], 1)
        self.assertEqual(m["scarcity_critical_availability_pct"], 0)
        no_window = Runner(tiny(assets=Assets(grid_limit_kw=6), grid_kw=(6., 6.)), "B1").run()["metrics"]
        self.assertEqual(no_window["scarcity_window_hours"], 0)
        self.assertIsNone(no_window["scarcity_critical_availability_pct"])

    def test_only_current_app_routes(self):
        with TestClient(create_app()) as client:
            self.assertEqual(client.get("/").status_code, 200)
            self.assertEqual(client.get("/api/health").json(), {"status": "ok"})
            for path in ("/legacy", "/api/state", "/static/legacy.html"):
                self.assertEqual(client.get(path).status_code, 404)
