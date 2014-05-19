# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Access to Texas Instruments INA231.

High- or Low-side Measurement, Bidirectional current/power monitor with 1.8v i2c
"""
import ina2xx


class Ina231Error(Exception):
  """Error occurred accessing ina231."""


class ina231(ina2xx.ina2xx):
  """Object to access drv=ina231 controls.

  Device is largely similar to the ina219 in function but with various register
  subfields shifted around.
  TODO(tbroch, crosbug.com/p/28588)
  1. Implement necessary changes to base class to provide access to milliamps &
     milliwatts for ina231.  This will require a bit more surgery as the INA219
     provided CNVR & OVF bits inside the BUSV registers while the INA231 has
     moved them to the REG_MSKEN register.
  """
  REG_MSKEN = 6
  REG_ALRT = 7

  BUSV_MV_PER_LSB = 1.25
  BUSV_MV_OFFSET = 0
  BUSV_MAX = 28000

  def _Get_milliamps(self):
    raise NotImplementedError('_Get_milliamps not implemented')

  def _Get_milliwatts(self):
    raise NotImplementedError('_Get_milliwatts not implemented')
