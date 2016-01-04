# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import array
import logging
import usb

import stm32usb


"""Accesses I2C buses through stm32 usb endpoint."""

class Si2cError(Exception):
  """Class for exceptions of Si2c."""
  def __init__(self, msg, value=0):
    """Si2cError constructor.

    Args:
      msg: string, message describing error in detail
      value: integer, value of error when non-zero status returned.  Default=0
    """
    super(Si2cError, self).__init__(msg, value)
    self.msg = msg
    self.value = value


class Si2cBus(object):
  """I2C bus class to access devices on the bus.

  Usage:
    bus = Si2cBus()
    # read 1 byte from slave(0x48) register(0x16)
    bus.wr_rd(0x48, [0x16], 1)
    # write 2 bytes to slave(0x48) register(0x20)
    bus.wr_rd(0x48, [0x20, 0x01, 0x02])

  Instance Variables:
    _logger: Si2c tagged log output
    _port: stm32 i2c controller index
    _susb: stm32 usb class
  """
  def __init__(self, vendor=0x18d1, product=0x501a,
      interface=1, port=0, serialname=None):
    self._logger = logging.getLogger("Si2c")
    self._logger.debug("")

    self._port = port

    self._susb = stm32usb.Susb(vendor=vendor, product=product,
        interface=interface, serialname=serialname, logger=self._logger)

    self._logger.debug("Set up stm32 i2c")

  def __del__(self):
    """Si2c destructor."""
    self._logger.debug("Close")

  def wr_rd(self, slave_address, write_list, read_count=None):
    """Implements hdctools wr_rd() interface.

    This function writes byte values list to I2C device, then reads
    byte values from the same device.

    Args:
      slave_address: 7 bit I2C slave address.
      write_list: list of output byte values [0~255].
      read_count: number of byte values to read from device.

    Interface:
      write: [addr, write_count, read_count, data ... ]
      read: [data .. ]

    Returns:
      Bytes read from i2c.

    Raises:
      Si2cError on transaction failure.
    """
    self._logger.debug("Si2c.wr_rd("
        "slave_address=0x%x, write_list=%s, read_count=%s)" % (
          slave_address, write_list, read_count))

    # Clean up args from python style to correct types.
    if not write_list:
      write_list = []
    write_length = len(write_list)
    read_count = max(0, read_count)

    # Send wr_rd command to stm32.
    cmd = [self._port, slave_address, write_length, read_count] + write_list
    ret = self._susb._write_ep.write(cmd, self._susb.TIMEOUT_MS)

    # Read back response if necessary.
    bytes = self._susb._read_ep.read(read_count + 4, self._susb.TIMEOUT_MS)
    if len(bytes) < (read_count + 4):
      raise Si2cError("Read status failed.")

    if bytes[0] != 0 or bytes[1] != 0:
      raise Si2cError("Read status failed: 0x%02x%02x" % (bytes[1], bytes[0]))

    self._logger.debug("Si2c.wr_rd result 0x%02x%02x, read %s" % (bytes[1], bytes[0], bytes[4:]))
    return bytes[4:]
