# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Access to Texas Instruments INA231.

High- or Low-side Measurement, Bidirectional current/power monitor with 1.8v i2c
"""
import ina2xx


class ina231(ina2xx.ina2xx):
  """Object to access drv=ina231 controls.

  Device is largely similar to the ina219 in function but with various register
  sub-fields shifted around.  Most notably the overflow(OVF) and
  conversion-ready(CNVR) status bits have moved from the BUSV register on INA219
  to a separate mask/enable register(REG_MSKEN) on INA231.

  Beyond that the coefficients for calculating current & power LSBs are slightly
  different.
  """
  MAX_CALIB = 0xffff
  MAX_REG_INDEX = 0x7 # REG_ALRT

  MSKEN_CNVR = 0x8
  MSKEN_OVF = 0x4

  BUSV_MV_PER_LSB = 1.25
  BUSV_MV_OFFSET = 0
  BUSV_MAX = 28000

  CUR_LSB_COEFFICIENT = 5.12
  PWR_LSB_COEFFICIENT = 25

  def _read_cnvr_ovf(self):
    """Read mask/enable register and return needed values.

    Returns:
      tuple (is_cnvr, is_ovf, voltage) where:
        is_cnvr: boolean True if conversion ready else False
        is_ovf: boolean True if math overflow occurred else False
    """
    msken_reg = self._read_reg(self.REG_MSKEN)
    is_cnvr = (self.MSKEN_CNVR & msken_reg) != 0
    is_ovf = (self.MSKEN_OVF & msken_reg) != 0
    return (is_cnvr, is_ovf)
