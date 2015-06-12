# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Access to Texas Instruments INA3221.
Triple-Channel, High-Side Measurement, Shunt and Bus Voltage Monitor
with i2c Interface.
"""
import ina2xx


class ina3221(ina2xx.ina2xx):
  """Object to access drv=ina3221 controls.
  """
  MAX_CHANNEL = 3
  REG_IDX = dict(cfg=0, shv=1, busv=2, msken=15)
  MAX_REG_INDEX = 0x11 # Power valid lower limit.  Ignoring Manuf/Die ID

  MSKEN_CNVR = 0x1

  BUSV_MV_PER_LSB = 8
  BUSV_MV_OFFSET = 3
  BUSV_MAX = 26000

  def _read_cnvr_ovf(self):
    """Read mask/enable register and return needed values.

    Returns:
      tuple (is_cnvr, is_ovf, voltage) where:
        is_cnvr: boolean True if conversion ready else False
        is_ovf: boolean True if math overflow occurred else False
    """
    msken_reg = self._read_reg(self.REG_MSKEN)
    is_cnvr = (self.MSKEN_CNVR & msken_reg) != 0
    return (is_cnvr, 0)
