#!/usr/bin/env python
# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
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

setup(
  name = "usbkm232",
  version = "0.0.1",
  package_dir = {'' : 'build'},
  py_modules=['usbkm232.ctrld', 'usbkm232.ctrlu', 'usbkm232.enter',
              'usbkm232.space'],
  packages=['usbkm232'],
  url = "http://www.chromium.org",
  maintainer='chromium os',
  maintainer_email='chromium-os-dev@chromium.org',
  license = "Chromium",
  description = "Communicate and control usbkm232 USB keyboard device.",
  long_description = "Communicate and control usbkm232 USB keyboard device.",
  entry_points={
    'console_scripts': [
      'usbkm232-ctrld = usbkm232.ctrld:main',
      'usbkm232-ctrlu = usbkm232.ctrlu:main',
      'usbkm232-enter = usbkm232.enter:main',
      'usbkm232-space = usbkm232.space:main',
      'usbkm232-test = usbkm232.usbkm232:main',
    ]
  }
)
