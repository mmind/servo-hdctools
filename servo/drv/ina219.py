# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Access to Texas Instruments INA219.

A zero-drift, bi-directional current/power monitor with I2C interface.
"""
import ina2xx


class ina219(ina2xx.ina2xx):
  """Object to access drv=ina219 controls."""

  # 800mA range, ~12.5uA/lsb for a 50mOhm rsense.  Note lsb is SBZ
  MAX_CALIB = 0xfffe
  MAX_REG_INDEX = 0x5 # REG_CALIB

  # millivolts per lsb of bus voltage register
  BUSV_MV_PER_LSB = 4
  # offset of 13-bit bus voltage measurement.
  # <2> reserved
  # <1> CNVR: conversion ready bit
  # <0> OVF: overflow bit
  BUSV_MV_OFFSET = 3
  BUSV_CNVR = 0x2
  BUSV_OVF = 0x1

  # bus voltage can measure up to 32V
  BUSV_MAX = 32000

  SHV_UV_PER_LSB = 10.0
  SHV_OFFSET = 0
  SHV_MASK = 0x7fff

  # coefficient for determining current per lsb.  See datasheet for details
  CUR_LSB_COEFFICIENT = 40.96

  # coefficient for determining power per lsb.  See datasheet for details
  PWR_LSB_COEFFICIENT = 20

  def _read_cnvr_ovf(self):
    """Read the bus voltage register and return its values.

    Conversion ready bit(<1>), CNVR, signifies that there is a new sample in the
    output registers. Per datasheet, page 15 (SBOS448C-AUGUST 2008-REVISED MARCH
    2009) this bit is cleared when:

      1. Writing config register (self.CFG_REG) except when power-down or off
      2. Reading status register (self.CFG_BUSV)
      3. Triggering with convert pin.  Not applicable to INA219 (only INA209)

    Overflow bit(<0>), OVF, has occurred during calculation of current or power
    and those output registers are meaningless.

    The bus voltage itself is stored in bits <15:3>.

    Returns:
      tuple (is_cnvr, is_ovf) where:
        is_cnvr: boolean True if conversion ready else False
        is_ovf: boolean True if math overflow occurred else False
    """
    busv_reg = self._read_reg('busv')
    is_cnvr = (self.BUSV_CNVR & busv_reg) != 0
    is_ovf = (self.BUSV_OVF & busv_reg) != 0
    return (is_cnvr, is_ovf)
