"""Script for analyzing timing of unit tests and fixtures."""

# pylint: disable=import-error
from collections import defaultdict
from itertools import groupby

import numpy as np
import pyperclip


TIME_LOWER_BOUND = 0.1


data = pyperclip.paste()
test_case_lines = []
fixture_lines = []
for line in data.split("\n"):
    if "[DEBUG]" not in line:
        continue
    if "AssertionError" in line:
        continue
    if "[fixture]" in line:
        fixture_lines.append(line)
    else:
        test_case_lines.append(line)

test_lookup = {}


def func(string):
    """Helper function for sorting and grouping test results."""
    return string.split("[DEBUG] ")[-1].split(" [")[0].split("[")[0].strip()


for _id, group in groupby(sorted(test_case_lines, key=func), key=func):
    phase_times = defaultdict(list)
    for item in group:
        item = item.split(" [")[-1]
        phase, time = item.split("]=")
        phase_times[phase].append(float(time))
    for key, value in phase_times.items():
        phase_times[key] = np.mean(value)
    test_lookup[_id] = dict(phase_times)


sorted_test_lookup = {
    phase: {
        key: value[phase]
        for key, value in sorted(
            test_lookup.items(),
            key=lambda x: x[1][phase],  # pylint: disable=cell-var-from-loop
            reverse=True,
        )
    }
    for phase in ["call", "setup", "teardown"]
}

for phase, times in sorted_test_lookup.items():
    print(phase)
    for test, time in times.items():
        if time < TIME_LOWER_BOUND:
            continue
        print(f"{test}: {time}")
    print()


fixture_times = {}


def func(string):  # pylint: disable=function-redefined
    """Helper function for sorting and grouping test results."""
    return string.split("[DEBUG] ")[-1].split(" [fixture]=")[0]


for _id, group in groupby(sorted(fixture_lines, key=func), key=func):
    group = [float(x.strip().split("[fixture]=")[-1]) for x in group]
    fixture_times[_id] = np.mean(group)


for fixture, time in dict(
    sorted(fixture_times.items(), key=lambda x: x[1], reverse=True)
).items():
    print(f"{fixture}: {time}")
print()
