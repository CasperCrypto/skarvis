"""Tests for geometry: angles, circular statistics, triangulation.

These tests check the maths against ground truth that is known by construction,
which is the only way to verify a position engine before there is a radio.
"""

from __future__ import annotations

import math
import unittest

from czapla.geometry import (
    bearing_to_unit,
    circular_mean_deg,
    circular_std_deg,
    latlon_to_local,
    local_to_latlon,
    triangulate,
    unit_to_bearing,
    wrap_180,
    wrap_deg,
)


class TestAngles(unittest.TestCase):
    def test_wrap_deg(self):
        self.assertAlmostEqual(wrap_deg(370.0), 10.0, places=9)
        self.assertAlmostEqual(wrap_deg(-10.0), 350.0, places=9)
        self.assertAlmostEqual(wrap_deg(0.0), 0.0, places=9)

    def test_wrap_180(self):
        self.assertAlmostEqual(wrap_180(190.0), -170.0, places=9)
        self.assertAlmostEqual(wrap_180(-190.0), 170.0, places=9)
        self.assertAlmostEqual(wrap_180(0.0), 0.0, places=9)

    def test_bearing_unit_roundtrip(self):
        for bearing in (0.0, 45.0, 90.0, 137.5, 180.0, 270.0, 359.0):
            east, north = bearing_to_unit(bearing)
            self.assertAlmostEqual(unit_to_bearing(east, north), bearing, places=6)

    def test_compass_convention(self):
        # 0 degrees must point north (+y in our local plane), 90 east (+x).
        east, north = bearing_to_unit(0.0)
        self.assertAlmostEqual(east, 0.0, places=9)
        self.assertAlmostEqual(north, 1.0, places=9)
        east, north = bearing_to_unit(90.0)
        self.assertAlmostEqual(east, 1.0, places=9)
        self.assertAlmostEqual(north, 0.0, places=9)


class TestCircularStats(unittest.TestCase):
    def test_mean_handles_wraparound(self):
        # The naive average of 350 and 10 is 180, which is exactly wrong.
        mean = circular_mean_deg([350.0, 10.0])
        self.assertTrue(mean < 1.0 or mean > 359.0, f"got {mean}")

    def test_mean_of_identical(self):
        self.assertAlmostEqual(circular_mean_deg([90.0, 90.0, 90.0]), 90.0, places=6)

    def test_std_zero_for_identical(self):
        self.assertAlmostEqual(circular_std_deg([120.0] * 5), 0.0, places=6)

    def test_std_grows_with_spread(self):
        tight = circular_std_deg([100.0, 101.0, 99.0, 100.5])
        wide = circular_std_deg([100.0, 140.0, 60.0, 110.0])
        self.assertLess(tight, wide)


class TestLocalPlane(unittest.TestCase):
    def test_roundtrip(self):
        lat0, lon0 = 51.2631, 15.5672
        lat, lon = local_to_latlon(300.0, -450.0, lat0, lon0)
        east, north = latlon_to_local(lat, lon, lat0, lon0)
        self.assertAlmostEqual(east, 300.0, places=3)
        self.assertAlmostEqual(north, -450.0, places=3)

    def test_east_is_positive(self):
        lat0, lon0 = 51.0, 15.0
        east, north = latlon_to_local(lat0, lon0 + 0.01, lat0, lon0)
        self.assertGreater(east, 0.0)
        self.assertAlmostEqual(north, 0.0, places=3)


class TestTriangulation(unittest.TestCase):
    def test_perfect_intersection(self):
        # Two rays drawn exactly at a known point must recover that point.
        target_e, target_n = 500.0, 500.0
        ray1 = (0.0, 0.0, math.degrees(math.atan2(500.0, 500.0)) % 360.0)
        ray2 = (1000.0, 0.0, math.degrees(math.atan2(500.0, -500.0)) % 360.0)
        fix = triangulate([ray1, ray2])
        self.assertIsNotNone(fix)
        self.assertAlmostEqual(fix["east"], target_e, places=3)
        self.assertAlmostEqual(fix["north"], target_n, places=3)
        self.assertLess(fix["spread_m"], 1e-6)
        self.assertEqual(fix["n_rays"], 2)

    def test_three_rays_good_geometry(self):
        # Nodes arranged AROUND the target so the bearings genuinely spread. A far
        # target seen from nodes clustered on one side gives nearly parallel rays,
        # which is poor geometry no matter how many nodes there are.
        target_e, target_n = 0.0, 0.0
        nodes = ((0.0, -500.0), (433.0, 250.0), (-433.0, 250.0))
        rays = []
        for east, north in nodes:
            bearing = math.degrees(math.atan2(target_e - east, target_n - north)) % 360.0
            rays.append((east, north, bearing))
        fix = triangulate(rays)
        self.assertIsNotNone(fix)
        self.assertAlmostEqual(fix["east"], target_e, places=3)
        self.assertAlmostEqual(fix["north"], target_n, places=3)
        self.assertEqual(fix["n_rays"], 3)
        # Bearings spread ~120 degrees apart: near-ideal geometry.
        self.assertGreater(fix["quality"], 0.7)

    def test_clustered_nodes_around_a_distant_target_score_low(self):
        # This is the real-world trap: three nodes 600 m apart all looking at a
        # target 3 km away have almost identical bearings and localise poorly.
        target_e, target_n = -250.0, 3000.0
        nodes = ((0.0, 0.0), (600.0, 0.0), (300.0, -500.0))
        rays = []
        for east, north in nodes:
            bearing = math.degrees(math.atan2(target_e - east, target_n - north)) % 360.0
            rays.append((east, north, bearing))
        fix = triangulate(rays)
        self.assertIsNotNone(fix)
        self.assertLess(fix["quality"], 0.2)

    def test_parallel_rays_rejected(self):
        # All rays due east: they never intersect, so no fix may be invented.
        rays = [(0.0, 0.0, 90.0), (0.0, 100.0, 90.0), (0.0, 200.0, 90.0)]
        self.assertIsNone(triangulate(rays))

    def test_single_ray_rejected(self):
        self.assertIsNone(triangulate([(0.0, 0.0, 45.0)]))

    def test_noisy_rays_land_close(self):
        target_e, target_n = 400.0, -300.0
        rays = []
        for east, north, error in ((0.0, 0.0, 3.0), (800.0, 0.0, -3.0), (400.0, -600.0, 2.0)):
            bearing = (
                math.degrees(math.atan2(target_e - east, target_n - north)) + error
            ) % 360.0
            rays.append((east, north, bearing))
        fix = triangulate(rays)
        self.assertIsNotNone(fix)
        miss = math.hypot(fix["east"] - target_e, fix["north"] - target_n)
        # A few degrees of error must stay a short distance, not hundreds of metres.
        self.assertLess(miss, 60.0, f"miss was {miss:.1f} m")

    def test_quality_low_for_shallow_geometry(self):
        rays = [(0.0, 0.0, 45.0), (1000.0, 0.0, 46.0)]
        fix = triangulate(rays)
        self.assertIsNotNone(fix)
        self.assertLess(fix["quality"], 0.2)


if __name__ == "__main__":
    unittest.main()
