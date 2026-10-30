"""Objective tests using fabricated pairs and no solver calls."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch

import numpy as np


def load_objective_helpers():
    """Load core with backend imports blocked."""
    package = ModuleType("benchmark")
    dataset = ModuleType("benchmark.dataset")
    methods = ModuleType("benchmark.methods")
    for name in ("solve_scipy", "solve_lap", "solve_lapjv", "solve_lapsolver", "solve_laprust"):
        setattr(methods, name, Mock(side_effect=AssertionError("A regression test must not call a solver")))
    dataset.experimental_cost = Mock(side_effect=AssertionError("No random benchmark input is needed"))
    dataset.uniform_cost = Mock(side_effect=AssertionError("No random benchmark input is needed"))
    package.dataset = dataset
    package.methods = methods
    spec = importlib.util.spec_from_file_location("objective_helpers", Path(__file__).with_name("core.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    imports = {"benchmark": package, "benchmark.dataset": dataset, "benchmark.methods": methods}
    with patch.dict(sys.modules, imports):
        spec.loader.exec_module(module)
    return module


class SoftObjectiveTests(unittest.TestCase):
    """Check unmatched-endpoint penalties."""

    @classmethod
    def setUpClass(cls):
        cls.core = load_objective_helpers()

    def test_rejection_beats_a_link_above_the_threshold(self):
        matrix = np.array([[0.75]])
        rejected = np.empty((0, 2), dtype=np.int64)
        linked = np.array([[0, 0]])
        self.assertEqual(self.core.soft_objective(matrix, rejected, 0.5), 0.5)
        self.assertEqual(self.core.soft_objective(matrix, linked, 0.5), 0.75)
        self.assertLess(
            self.core.soft_objective(matrix, rejected, 0.5), self.core.soft_objective(matrix, linked, 0.5)
        )

    def test_rectangular_unmatched_endpoints_and_transpose(self):
        matrix = np.array([[0.125, 0.5, 1.0], [0.25, 0.75, 2.0]])
        links = np.array([[0, 0]])
        # One unmatched row and two unmatched columns each cost 0.25.
        self.assertEqual(self.core.soft_objective(matrix, links, 0.5), 0.875)
        self.assertEqual(self.core.soft_objective(matrix.T, links[:, ::-1], 0.5), 0.875)

    def test_link_at_the_threshold_ties_rejection(self):
        matrix = np.array([[0.5]])
        self.assertEqual(
            self.core.soft_objective(matrix, np.array([[0, 0]]), 0.5),
            self.core.soft_objective(matrix, np.empty((0, 2), dtype=np.int64), 0.5),
        )

    def test_empty_side_still_pays_for_its_unmatched_endpoints(self):
        links = np.empty((0, 2), dtype=np.int64)
        self.assertEqual(self.core.soft_objective(np.empty((0, 3)), links, 0.5), 0.75)
        self.assertEqual(self.core.soft_objective(np.empty((0, 0)), links, 0.5), 0.0)


if __name__ == "__main__":
    unittest.main()
