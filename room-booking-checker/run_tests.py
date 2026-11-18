"""Runs all tests and prints one PASSED/FAILED line per test."""

import os
import sys
import unittest


def _name(test):
    return test.id().replace("tests.", "", 1)


class NamedResult(unittest.TextTestResult):
    def addSuccess(self, test):
        super().addSuccess(test)
        self.stream.writeln("PASSED: " + _name(test))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.stream.writeln("FAILED: " + _name(test))

    def addError(self, test, err):
        super().addError(test, err)
        self.stream.writeln("FAILED: " + _name(test))


if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    suite = unittest.defaultTestLoader.discover(root, pattern="test*.py", top_level_dir=root)
    result = unittest.TextTestRunner(verbosity=0, resultclass=NamedResult).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
