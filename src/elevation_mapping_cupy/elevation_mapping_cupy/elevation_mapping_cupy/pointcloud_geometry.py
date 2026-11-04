"""Re-express registered clouds in the physical sensor frame for GPU fusion."""
import numpy as np


def sensor_frame_points(points, cloud_rotation, cloud_translation, sensor_rotation, sensor_origin):
    """Keep world geometry while giving kernels sensor-relative coordinates.

    The existing fusion API uses raw XYZ for range-dependent noise and R,t for
    both world placement and ray origin. Registered/world-frame XYZ must first
    be expressed in the current sensor frame. Extra channels are copied intact.
    """
    points = np.asarray(points)
    if points.ndim != 2 or points.shape[1] < 3:
        raise ValueError('point cloud must have at least three columns')
    rotations = []
    for value in (cloud_rotation, sensor_rotation):
        r = np.asarray(value, dtype=np.float32)
        if (r.shape != (3, 3) or not np.all(np.isfinite(r)) or
                not np.allclose(r.T @ r, np.eye(3), atol=1e-5) or
                not np.isclose(np.linalg.det(r), 1., atol=1e-5)):
            raise ValueError('point cloud transforms must contain proper rotations')
        rotations.append(r)
    translations = []
    for value in (cloud_translation, sensor_origin):
        t = np.asarray(value, dtype=np.float32)
        if t.shape != (3,) or not np.all(np.isfinite(t)):
            raise ValueError('point cloud translations must be finite 3D vectors')
        translations.append(t)
    cloud_r, sensor_r = rotations
    cloud_t, origin = translations
    result = np.array(points[np.isfinite(points[:, :3]).all(axis=1)], copy=True)
    if not np.issubdtype(result.dtype, np.floating):
        result = result.astype(np.float32)
    relative_r = sensor_r.T @ cloud_r
    relative_t = sensor_r.T @ (cloud_t-origin)
    result[:, :3] = result[:, :3] @ relative_r.T + relative_t
    return result, sensor_r, origin
