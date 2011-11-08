#!/usr/bin/env python
#
# Based on suggestions in http://guide.python-distribute.org/creation.html
# ...with a mix of bits from pymox.

import os
from setuptools import setup

setup(
  name = "servo",
  version = "0.0.1",
  package_dir = {'' : 'build'},
  py_modules=['servo.servod', 'servo.dut_control'],
  packages=['servo', 'servo.data', 'servo.drv'],
  package_data={'servo.data': ['*.xml']},
  url = "http://www.chromium.org",
  maintainer='chromium os',
  maintainer_email='chromium-os-dev@chromium.org',
  license = "Chromium",
  description = "Server to communicate and control servo debug board.",
  long_description = "Server to communicate and control servo debug board.",
  entry_points={
    'console_scripts': [
      'servod = servo.servod:main',
      'dut-control = servo.dut_control:main',
    ]
  }
)
