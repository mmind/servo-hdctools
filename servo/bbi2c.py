# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Allows creation of i2c interface for beaglebone devices."""
# TODO (sbasi) crbug.com/187489 - Implement BBi2c.

class BBi2cError(Exception):
  """Class for exceptions of BBi2c."""
  def __init__(self, msg, value=0):
    """BBi2cError constructor.

    Args:
      msg: string, message describing error in detail
      value: integer, value of error when non-zero status returned.  Default=0
    """
    super(BBi2cError, self).__init__(msg, value)
    self.msg = msg
    self.value = value

class BBi2c(object):
  """Provide interface to i2c through beaglebone"""

  def open(self):
    """Opens access to FTDI interface as a i2c (MPSSE mode) interface.

    Raises:
      BBi2cError: If open fails
    """
    pass

  def close(self):
    """Close connection to i2c through beaglebone and cleanup.

    Raises:
      BBi2cError: If close fails
    """
    pass

  def setclock(self, speed=100000):
    """Sets i2c clock speed.

    Args:
      speed: clock speed in hertz.  Default is 100kHz
    """
    pass

  def wr_rd(self, slv, wlist, rcnt):
    """Write and/or read a slave i2c device.

    Args:
      slv: 7-bit address of the slave device
      wlist: list of bytes to write to the slave.  If list length is zero its
          just a read
      rcnt: number of bytes to read from the device.  If zero, its just a write

    Returns:
      list of c_ubyte's read from i2c device.
    """
    pass