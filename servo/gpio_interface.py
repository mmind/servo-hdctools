# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

class GpioInterface(object):
  """Abstract class to be used by GPIO interface implementations."""

  def open(self):
    """Opens access to GPIO's."""
    raise NotImplementedError('open not yet implemented.')

  def close(self):
    """Close access to GPIO's."""
    raise NotImplementedError('close not yet implemented.')

  def wr_rd(self, offset, width, dir_val=None, wr_val=None, chip=None,
            muxfile=None):
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
      chip    : beaglebone gpio chip number. [IF REQUIRED]
      muxfile : used to specify the correct omap_mux muxfile to select this
                gpio. [IF REQUIRED]

    Returns:
      integer value from reading the gpio value ( masked & aligned )
    """
    raise NotImplementedError('wr_rd not yet implemented.')