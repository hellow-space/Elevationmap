#!/usr/bin/env python3
"""Characterize original C++ plane fitting with mathematical ground truth, no ROS.

No production algorithm is reimplemented: two unchanged definitions are extracted
from the repository at build time. The adapter supplies only window size/resolution.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / ('src/elevation_mapping_cupy/plane_segmentation/'
                 'convex_plane_decomposition/src/sliding_window_plane_extraction/'
                 'SlidingWindowPlaneExtractor.cpp')
ANGLE_TOL_DEG = 0.1
ROUGHNESS_TOL_M = 0.0001
NORMAL_TOL = 1e-5


def definition(source, signature):
    """Extract balanced braces for these two known, brace-safe C++ definitions.

Fail on missing/ambiguous signatures; generated code is retained for inspection.
This is intentionally not a general C++ parser.
"""
    if source.count(signature) != 1:
        raise ValueError(f'Expected exactly one definition: {signature}')
    start = source.index(signature)
    opening = source.index('{', start)
    depth = 0
    for end in range(opening, len(source)):
        depth += (source[end] == '{') - (source[end] == '}')
        if depth == 0:
            return source[start:end + 1]
    raise ValueError('Unbalanced function body')


def build(source, directory):
    directory.mkdir(parents=True, exist_ok=True)
    helper = definition(source, 'std::pair<Eigen::Vector3d, double> normalAndErrorFromCovariance(')
    window = definition(source, 'std::pair<Eigen::Vector3d, double> SlidingWindowPlaneExtractor::computeNormalAndErrorForWindow(')
    shell = '''
class SlidingWindowPlaneExtractor {
 public:
  struct { int kernel_size; } parameters_;
  struct { double resolution; } segmentedPlanesMap_;
  std::pair<Eigen::Vector3d, double> computeNormalAndErrorForWindow(
      const Eigen::MatrixXf& windowData) const;
};
'''
    (directory / 'original_fit.inc').write_text(helper + '\n' + shell + window + '\n')
    executable = directory / 'fit_driver'
    subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra',
                    '-isystem', '/usr/include/eigen3', '-I' + str(directory),
                    str(HERE / 'fit_driver.cpp'), '-o', str(executable)], check=True)
    return executable


def expected_plane(gx, gy):
    norm = math.sqrt(1 + gx * gx + gy * gy)
    return [-gx / norm, -gy / norm, 1 / norm]


def map_case(name, gx=0., gy=0., resolution=.05, offset=0., amplitude=0., kernel=3,
             expected_normal=None, expected_roughness=0.):
    # grid_map convention used by ORIGINAL code: row -> -X, column -> -Y.
    heights = [[gx * (20 - row) * resolution + gy * (20 - col) * resolution
                + offset + amplitude * (1, -2, 1)[row % 3] * (1, -2, 1)[col % 3]
                for col in range(41)] for row in range(41)]
    half = kernel // 2
    windows = [[heights[row + dr][col + dc]
                for dr in range(-half, half + 1) for dc in range(-half, half + 1)]
               for row in range(half, 41 - half) for col in range(half, 41 - half)]
    return dict(name=name, kernel=kernel, resolution_m=resolution, windows=windows,
                normal=expected_normal or expected_plane(gx, gy),
                roughness_m=expected_roughness, planted_slope_deg=math.degrees(math.atan(math.hypot(gx, gy))))


def cases():
    tangent = math.tan(math.radians(15))
    result = [map_case('flat')]
    for name, gx, gy in [('x_plus_15', tangent, 0), ('x_minus_15', -tangent, 0),
                         ('y_plus_15', 0, tangent), ('y_minus_15', 0, -tangent),
                         ('diagonal_15', tangent / math.sqrt(2), tangent / math.sqrt(2))]:
        result.append(map_case(name, gx, gy))
    result += [map_case('x_15_offset_10m', tangent, offset=10),
               map_case('x_15_resolution_10cm', tangent, resolution=.1),
               map_case('x_15_window_5', tangent, kernel=5)]
    # q=(1,-2,1); every 3x3 cyclic window of a*q(row)*q(col) has mean 0,
    # Cov(X,Z)=Cov(Y,Z)=0, and mean(Z^2)=4*a^2. XY variances=r^2*2/3.
    # For a=.005 and r=.05, vertical variance is strictly the smallest:
    # fitted plane is horizontal and orthogonal RMS=2*a=.01 m.
    result.append(map_case('rough_flat_10mm', amplitude=.005, expected_roughness=.01))
    result.append(map_case('rough_flat_20mm', amplitude=.01, expected_roughness=.02))
    # Tilted + vertical noise: PCA plane is not exactly the planted 15 deg.
    # Analytic 2x2 XZ covariance eigenpair gives an independent exact oracle.
    v = .05 ** 2 * 2 / 3
    w = .01 ** 2
    a, b, d = v, tangent * v, tangent ** 2 * v + w
    smallest = (a + d - math.hypot(a - d, 2 * b)) / 2
    fitted_gradient = b / (a - smallest)
    result.append(map_case('rough_tilted_analytic', tangent, amplitude=.005,
                           expected_normal=expected_plane(fitted_gradient, 0),
                           expected_roughness=math.sqrt(smallest)))
    nan = float('nan')
    for name, window, valid in [
        ('nan_one_missing', [nan, 0, 0, 0, 0, 0, 0, 0, 0], True),
        ('three_noncollinear', [0, 0, nan, 0, nan, nan, nan, nan, nan], True),
        ('empty_invalid', [nan] * 9, False),
        ('two_points_invalid', [0, 0] + [nan] * 7, False),
        ('collinear_invalid', [0, 0, 0] + [nan] * 6, False),
    ]:
        result.append(dict(name=name, kernel=3, resolution_m=.05, windows=[window],
                           normal=[0, 0, 1], roughness_m=0., invalid=not valid))
    return result


def evaluate(executable, fixtures):
    lines = []
    for case in fixtures:
        for window in case['windows']:
            lines.append(f"{case['kernel']} {case['resolution_m']} " + ' '.join(map(str, window)))
    run = subprocess.run([str(executable)], input='\n'.join(lines) + '\n',
                         text=True, capture_output=True, check=True)
    rows = [list(map(float, line.split())) for line in run.stdout.splitlines()]
    if len(rows) != len(lines):
        raise AssertionError(f'Missing outputs: {len(rows)} != {len(lines)}')
    results, cursor = [], 0
    for case in fixtures:
        count = len(case['windows'])
        values = rows[cursor:cursor + count]
        cursor += count
        expected = case['normal']
        true_angle = math.degrees(math.atan2(math.hypot(*expected[:2]), expected[2]))
        angles, roughnesses, normal_errors = [], [], []
        invalid = case.get('invalid', False)
        for row in values:
            if len(row) != 4 or not all(math.isfinite(x) for x in row):
                raise AssertionError(f"{case['name']}: malformed/nonfinite output {row}")
            nx, ny, nz, mse = row
            if invalid:
                if mse != 1e30 or [nx, ny, nz] != [0, 0, 1]:
                    raise AssertionError(f"{case['name']}: invalid sentinel lost")
                continue
            if mse < 0 or mse >= 1e30:
                raise AssertionError(f"{case['name']}: valid patch rejected")
            angles.append(math.degrees(math.atan2(math.hypot(nx, ny), nz)))
            roughnesses.append(math.sqrt(mse))
            normal_errors.append(max(abs(x - y) for x, y in zip(row[:3], expected)))
        summary = dict(name=case['name'], window_size=case['kernel'],
                       resolution_m=case['resolution_m'], tested_windows=count, invalid_expected=invalid)
        if invalid:
            summary['passed'] = True
        else:
            angle_error = max(abs(x - true_angle) for x in angles)
            rough_error = max(abs(x - case['roughness_m']) for x in roughnesses)
            summary.update(expected_slope_deg=true_angle, mean_slope_deg=sum(angles)/count,
                           max_slope_error_deg=angle_error,
                           expected_roughness_m=case['roughness_m'], mean_roughness_m=sum(roughnesses)/count,
                           max_roughness_error_m=rough_error, max_normal_component_error=max(normal_errors),
                           planted_slope_deg=case.get('planted_slope_deg', 0.),
                           passed=(angle_error < ANGLE_TOL_DEG and rough_error < ROUGHNESS_TOL_M
                                   and max(normal_errors) < NORMAL_TOL))
        results.append(summary)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/geometry_validation/results.json')
    parser.add_argument('--mutation-check', action='store_true')
    args = parser.parse_args()
    source = SOURCE.read_text()
    fixtures = cases()
    build_dir = ROOT / 'build/geometry_validation'
    executable = build(source, build_dir)
    results = evaluate(executable, fixtures)
    mutations = []
    if args.mutation_check:
        for name, before, after in [
            ('zero_roughness', 'return {unitaryNormalVector, squareError};',
             'return {unitaryNormalVector, squareError * 0.0};'),
            ('reverse_x_axis', '-kernel_row * segmentedPlanesMap_.resolution',
             'kernel_row * segmentedPlanesMap_.resolution'),
            ('wrong_resolution', '-kernel_row * segmentedPlanesMap_.resolution',
             '-kernel_row * 2.0 * segmentedPlanesMap_.resolution'),
        ]:
            if source.count(before) != 1:
                raise AssertionError(f'Mutation anchor not unique: {name}')
            with tempfile.TemporaryDirectory(prefix='geometry-mutation-') as directory:
                mutated = build(source.replace(before, after), Path(directory))
                failures = [r['name'] for r in evaluate(mutated, fixtures) if not r['passed']]
            mutations.append(dict(name=name, detected=bool(failures), failed_cases=failures))
    report = dict(source=str(SOURCE.relative_to(ROOT)),
                  source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  compiler=subprocess.check_output(['g++','--version'], text=True).splitlines()[0],
                  platform=platform.platform(),
                  tolerances=dict(slope_deg=ANGLE_TOL_DEG, roughness_m=ROUGHNESS_TOL_M,
                                  normal_component=NORMAL_TOL), cases=results, mutations=mutations,
                  scope='Original extracted function definitions only; no ROS, fusion, or production changes.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    for r in results:
        detail = 'invalid sentinel' if r['invalid_expected'] else (
            f"slope={r['mean_slope_deg']:.8f}deg max_error={r['max_slope_error_deg']:.3g}deg "
            f"roughness={r['mean_roughness_m']:.8g}m max_error={r['max_roughness_error_m']:.3g}m")
        print(f"{'PASS' if r['passed'] else 'FAIL'} {r['name']} n={r['tested_windows']} {detail}")
    for mutation in mutations:
        print(f"Mutation {mutation['name']}: detected={mutation['detected']}")
    print(f'Report: {args.output}')
    return 0 if all(r['passed'] for r in results) and all(m['detected'] for m in mutations) else 1


if __name__ == '__main__':
    raise SystemExit(main())
