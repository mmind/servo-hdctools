# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# TODO (sbasi) crbug.com/187488 - Implement BBgpio.

class BBgpioError(Exception):
  """Class for exceptions of Bgpio."""
  def __init__(self, msg, value=0):
    """BBgpioError constructor.

    Args:
      msg: string, message describing error in detail
      value: integer, value of error when non-zero status returned.  Default=0
    """
    super(BBgpioError, self).__init__(msg, value)
    self.msg = msg
    self.value = value

class BBgpio(object):
  """Provides interface to a beaglebone's GPIO."""

  def open(self):
    """Opens access to Beaglebone interface as a GPIO (bitbang).

    Raises:
      BBgpioError: If open fails
    """
    pass

  def close(self):
    """Close access to beaglebone interface as a GPIO (bitbang).

    Raises:
      BBgpioError: If close fails
    """
    pass

  def wr_rd(self, offset, width, dir_val=None, wr_val=None):
    """Write and/or read GPIO bit.

    Args:
      offset  : bit offset of the gpio to read or write
      width   : integer, number of contiguous bits in gpio to read or write
      dir_val : direction value of the gpio.  dir_val is interpretted as:
                  None : read the pins via libftdi's ftdi_read_pins
                  0    : configure as input
                  1    : configure as output
      wr_val  : value to write to the GPIO.  Note wr_val is irrelevant if
                dir_val = 0

    Returns:
      integer value from reading the gpio value ( masked & aligned )
    """
    pass