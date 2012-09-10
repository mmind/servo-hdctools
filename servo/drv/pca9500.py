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
  writes:
   - page write: slave wr + byte addr byte + 1-4 bytes to write
  reads:
   - byte N read: slave wr + byte addr byte to set addr
                  slave rd + read N bytes

  Note, EEPROM has an active low write control (WC#) which must be
  asserted to write the device.
"""
import logging


import hw_driver


REG_CTRL_LEN = 1
EEPROM_BYTES = 256
PAGE_BYTES = 4

class pca9500Error(Exception):
  """Error class for pca9500 class."""


class pca9500(hw_driver.HwDriver):
  """Object to access type=pca9500 controls."""

  _byte_addr = 0

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

  def _write_byte_addr(self, byte_addr):
    """Write EEPROM byte address.

    Byte address will be used by the next EEPROM operation providing its not
    altered by a write operation.

    Args:
      byte_addr: integer, byte address to be set in EEPROM
    """
    self._interface.wr_rd(self._slave, [byte_addr], 0)

  def _Set_byte_addr(self, byte_addr):
    """Write the EEPROM's byte address.

    Args:
      byte_addr: integer, byte address to be set in EEPROM

    Raises:
      pca9500Error: if byte_addr > EEPROM_BYTES

    """
    self._logger.debug('')
    if byte_addr > EEPROM_BYTES:
      raise pca9500Error, 'Byte address not valid'
    pca9500._byte_addr = byte_addr

  def _Set_eeprom(self, value):
    """Write the EEPROM.

    Accepts a string of space-delimited bytes that can be up to EEPROM_BYTES
    long.  These bytes are split into page writes starting at byte_addr.

    For example the following string with byte_addr == 0x10
      '0x00 0x01 0x02 0x03 0x04 0x05'

    would turn into I2C page writes of:
      <slv> 0x10 0x00 0x01 0x02 0x03
      <slv> 0x14 0x04 0x05

    Note, as this operation upsets the EEPROM byte address it must be restored
    at the completion of writing.

    Args:
      value: space-delimited list of bytes to be written to EEPROM at
        the EEPROM byte address

    Raises:
      pca9500Error: if number of bytes to write is more than EEPROM_BYTES
      pca9500Error: if I2c write failed to complete successfully

    """
    self._logger.debug('')
    byte_list = [int(byte_str, 0) for byte_str in value.split()]
    self._write_byte_addr(pca9500._byte_addr)

    if (len(byte_list) + pca9500._byte_addr) > EEPROM_BYTES:
      raise pca9500Error, 'Writing %d Bytes from addr %d will be > %d' % \
          (len(byte_list), pca9500._byte_addr, EEPROM_BYTES)
    page_list = [byte_list[i:(i + PAGE_BYTES)]
                 for i in xrange(0, len(byte_list), PAGE_BYTES)]
    # insert idx for writing
    for i, page in enumerate(page_list):
      page.insert(0, pca9500._byte_addr + (i * PAGE_BYTES))
      try:
        self._interface.wr_rd(self._slave, page, 0)
      except Fi2cError:
        self._logger.error("page write of %i:%s", i, page)
        raise pca9500Error, 'Setting PCA9500 EEPROM'


  def _Get_eeprom(self):
    """Read the EEPROM.

    Reads and returns a space-delimited string of EEPROM_BYTES bytes.  Note, as
    this operation upsets the EEPROM byte address it must be restored.

    TODO(tbroch): May want to provide facility to read less than entire device.

    Returns:
      string, space-delimited of current bytes in EEPROM.

        id_eeprom:
          0x00 0x01 0x02 0x03 0x04 0x05 0x06 0x07 0x08 0x09 0x0a 0x0b 0x0c ...
          .
          .
          .
          0xf0 0xf1 0xf2 0xf3 0xf4 0xf5 0xf6 0xf7 0xf8 0xf9 0xfa 0xfb 0xfc ...

    Raises:
      pca9500Error: if I2c read failed to complete successfully
    """
    self._logger.debug('')
    error = False
    self._write_byte_addr(0)
    try:
      byte_list = self._interface.wr_rd(self._slave, [], EEPROM_BYTES)
    except Fi2cError:
      self._logger.error("eeprom read")
      raise pca9500Error, 'Getting PCA9500 EEPROM'

    lines = []
    for i in xrange(0, len(byte_list), 16):
      line = ' '.join('0x%02x' % byte for byte in byte_list[i:i+16])
      lines.append(line)

    return '\n%s' % '\n'.join(lines)
