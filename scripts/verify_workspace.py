"""Explicit local smoke check; never downloads weights or runs during app import."""
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from component_ai.images import decode_image, discover_samples
    from component_ai.jobs import configuration, predict
    from component_ai.models import classify
    from component_ai.registry import discover_models
    sample = discover_samples(ROOT / 'component_aiimage')[0]
    image = decode_image(sample.read_bytes())
    # Bounded execution check, not an accuracy test or full-slide benchmark.
    image.thumbnail((640,640))
    checks = []
    for model in ('yolo26n','yolo26x','Faster R-CNN'):
        started = perf_counter()
        try:
            result = predict(image,configuration(model,.7))
            checks.append({'model':model,'status':'passed','objects':len(result['detections']),
                           'timing':result['timing'],'sha256':result['model_sha256']})
        except Exception as exc:
            checks.append({'model':model,'status':'failed','error':str(exc)[:3000]})
        checks[-1]['elapsed_seconds'] = perf_counter()-started
        print(json.dumps(checks[-1]), flush=True)
    paths = discover_models()
    started = perf_counter()
    result = classify(image.crop((0,0,min(160,image.width),min(160,image.height))),paths[:1])
    checks.append({'model':'Keras first available','status':'passed' if result['predictions'] and not result['errors'] else 'failed',
                   'errors':result['errors'],'elapsed_seconds':perf_counter()-started})
    print(json.dumps(checks[-1]), flush=True)
    output = ROOT / '.qa' / 'advanced_model_checks.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps({'sample':sample.name,'check_size':list(image.size),'clinical_validation':False,'checks':checks},indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
