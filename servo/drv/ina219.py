# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Access to Texas Instruments INA219.

A zero-drift, bi-directional current/power monitor with I2C interface.
"""
import ina2xx


class Ina219Error(Exception):
  """Error occurred accessing ina219."""


class ina219(ina2xx.ina2xx):
  """Object to access drv=ina219 controls."""
