"""Save portable schemas, sample scenarios and input provenance without external data."""
import json
from pathlib import Path
from src.domain import Scenario, Assets
from src.scenarios import SCENARIOS, build
from src.evaluation.economics import CostInputs


def main():
    out=Path('data/scenarios')
    out.mkdir(parents=True,exist_ok=True)
    (out/'schema.json').write_text(json.dumps(Scenario.model_json_schema(),indent=2)+'\n')
    for name in SCENARIOS:
        (out/f'{name}.json').write_text(build(name,7).model_dump_json(indent=2)+'\n')
    inputs={}
    for kind,values in (('assets',Assets().model_dump()),('economics',CostInputs().model_dump())):
        inputs[kind]={}
        for key,value in values.items():
            unit='INR' if 'inr' in key else 'kWh' if 'kwh' in key else 'kW' if 'kw' in key else 'years' if 'years' in key else 'count' if key=='households' else 'fraction / boolean / optional denominator; see field name'
            if '_inr_per_kw' in key:unit='INR/kW'
            if '_inr_per_kwh' in key:unit='INR/kWh'
            inputs[kind][key]=dict(value=value,unit=unit,status='assumed',date='2026-09-20',
                source='Engineering design placeholder, not measured or quoted; see docs/assumptions.md and docs/economics.md',
                range=[value*.7,value*1.4] if isinstance(value,(int,float)) and not isinstance(value,bool) and 'inr' in key else 'See scenario sensitivities; otherwise fixed assumption')
    Path('data/assumptions.json').write_text(json.dumps(inputs,indent=2)+'\n')


if __name__=='__main__':main()
