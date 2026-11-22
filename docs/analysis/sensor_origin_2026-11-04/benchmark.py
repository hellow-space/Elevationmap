"""CPU adapter timing only; does not initialize ROS or measure end-to-end latency."""
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from elevation_mapping_cupy.pointcloud_geometry import sensor_frame_points

rng=np.random.default_rng(20261104)
points=rng.normal(size=(18000,3)).astype(np.float32)*5
r=np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]],dtype=np.float32)
timings=[]
for i in range(230):
    start=perf_counter()
    result,rotation,origin=sensor_frame_points(points,np.eye(3),[10.,-20.,0.],r,[12.,-18.,.5])
    elapsed=(perf_counter()-start)*1000
    if i>=30:timings.append(elapsed)
np.testing.assert_allclose(result @ rotation.T+origin,points+[10.,-20.,0.],atol=5e-6)
metrics={'points':len(points),'measured_runs':len(timings),
         'cpu_adapter_ms':dict(zip(['p50','p95','max'],map(float,np.percentile(timings,[50,95,100])))),
         'scope':'Synthetic CPU affine adapter only; excludes TF, DDS, parsing, GPU fusion and robot motion.'}
out=Path(__file__).resolve().parent
(out/'benchmark.json').write_text(json.dumps(metrics,indent=2)+'\n')
print(json.dumps(metrics,indent=2))
