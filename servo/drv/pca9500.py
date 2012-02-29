# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Access to NXP's PCA9500.

8-bit I2C-bus and SMBus I/O port with 2-kbit EEPROM.

Accessed via controls with params of,
  1. type=pca9500 subtype=gpio offset='<num>'
  2. type=pca9500 subtype=eeprom

GPIO:
- Functions as an open-drain style GPIO's
  - Writing a '1' to the control register effectively makes the device an input
    with a pull-up.
  - Writing a '0' to the control register makes it a true output.
  - Reading the control register returns the current value of the pin.

EEPROM:
  TODO(tbroch) Implement EEPROM functionality
"""
import logging


import drv.hw_driver


REG_CTRL_LEN = 1


class pca9500Error(Exception):
  """Error class for pca9500 class."""


class pca9500(drv.hw_driver.HwDriver):
  """Object to access type=pca9500 controls."""

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: FTDI interface object to handle low-level communication to
       control
      params: dict of params needed to perform operations on pca9500 devices.
       All items are strings initially but should be cast to types detailed
       below.

    Mandatory Params:
      slv: integer, 7-bit i2c slave address

    Optional Params:
      offset: integer, left shift amount for location of gpio
      width: integer, bit width of gpio

    Attributes:
      _slave: integer value of the 7-bit i2c slave address.
    """
    super(pca9500, self).__init__(interface, params)
    if 'slv' not in self._params:
      raise pca9500Error("getting slave address")
    self._slave = int(self._params['slv'], 0)

  def _Set_gpio(self, value):
    """Set pca9500 GPIO to value.

    The pca9500 GPIO expander has a single control register (not typical
    direction and value register).  The driver must take care to maintain
    previous state of all bits.

    Args:
      value: integer value to write to gpio
    """
    self._logger.debug("value = %d", value)
    (_, mask) = self._get_offset_mask()
    cur_value = self._read_control_reg()
    if value:
      hw_value = cur_value | mask
    else:
      hw_value = cur_value & ~mask
    self._logger.debug("new(0x%02x) cur(0x%02x) mask(0x%02x)", hw_value,
                       cur_value, mask)
    self._interface.wr_rd(self._slave, [hw_value], 0)

  def _Get_gpio(self):
    """Get pca9500 GPIO value and return.

    Returns:
      integer value from gpio
    """
    self._logger.debug("")
    return self._create_logical_value(self._read_control_reg())

  def _read_control_reg(self):
    """Read the pca9500 control register.

    pca9500 has one register for its 8bit GPIO expander functionality.  This
    control register can be read by peforming a 1 byte read to the slave
    address.  See datasheet for more detail.

    Returns:
      integer value (8bit) of control register.
    """
    return self._interface.wr_rd(self._slave, [], REG_CTRL_LEN)[0]

  def _Set_eeprom(self):
    """Write the pca9500 EEPROM.

    TODO(tbroch): implement this.  Need to define format for the
    eeprom.  Likely candidate some form of TLV.  In all likelihood
    we'll simply store key=value strings in here where they consist
    of information that will uniquely identify the DUT where connected
    to.
    """
    raise NotImplementedError("pca9500 eeprom write not implemented.")

  def _Get_eeprom(self):
    """Read the pca9500 EEPROM.

    TODO(tbroch): implement this
    """
    raise NotImplementedError("pca9500 eeprom read not implemented.")
