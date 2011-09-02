# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Access to Linear Technologies LTC1663 DAC.

10-Bit Rail-to-Rail Micropower DAC with 2-Wire Interface

The LTC1663 is a 10-bit voltage output DAC with true buffered rail-to-rail
output voltage capability. It operates from a single supply with a range
of 2.7V to 5.5V. The reference for the DAC is selectable between the
supply voltage or an internal bandgap reference. Selecting the internal
bandgap reference will set the full-scale output voltage range to
2.5V. Selecting the supply as the reference sets the output voltage range
to the supply voltage.
"""
import drv.hw_driver


# TODO(tbroch)
# Evaluate implementing the sync address functionality via the quick command
# to force all LTC1663 DAC's on bus to load in parallel.  As we use the LTC1663
# to simulate load this would cause simultaneous current draw that might be more
# valuable for testing.

# These are really commands to the LTC1663.  See datasheet for details
REG_CMD_0 = 0

CMD_MASK = 0x7    # 3bit command data
DATA_MASK = 0x3ff # 10-bit DAC data

class Ltc1663Error(Exception):
  """Error class for LTC1663"""


class ltc1663(drv.hw_driver.HwDriver):
  """Object to access drv=ltc1663 controls."""
  def __init__(self, interface, params):
    """Constructor.

    Note, LTC1663 I2C transaction is ONLY to set the DAC via:
      <slave address> + <cmd> + <lsb byte> + <msb byte>

    Args:
      interface: interface object to handle low-level communication to control
      params: dictionary of params needed to perform operations on ltc1663
          devices.

    Mandatory Params:
      slave: integer, 7-bit i2c slave address
      i2c_obj: I2cReg object
    """
    super(ltc1663, self).__init__(interface, params)
    self._logger.debug("")
    self._slave = int(self._params['slv'], 0)
    self._i2c_obj = drv.i2c_reg.I2cReg.get_device(
      self._interface, self._slave, addr_len=1, reg_len=2, msb_first=False,
      no_read=True, use_reg_cache=False)

  def set(self, value):
    """Set 10-bit DAC value of LTC1663.

    Args:
      value: 10-bit unsigned integer to set DAC's output value

    Raises:
      Ltc1663Error: if value is out of bounds
    """
    self._logger.debug("value = %s" % str(value))
    if value & ~DATA_MASK:
      raise Ltc1663Error("DAC value %x can't be greater than %x" %
                         (value, DATA_MASK))
    self._i2c_obj._write_reg(REG_CMD_0, value)
