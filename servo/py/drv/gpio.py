# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of type=gpio.
"""
import drv.hw_driver
import logging


class gpioError(Exception):
  """Error class for gpio class."""


class gpio(drv.hw_driver.HwDriver):
  """Object to access type=gpio controls."""

  def get(self):
    """Get value for gpio driver
    
    TODO(tbroch) Add support for width > 1

    Returns:
      integer value from gpio

    Raises:
      gpioError: if no offset in param dict
    """
    self._logger.debug("")
    (offset, mask) = self._get_offset_mask()
    if offset is None:
      raise gpioError("No offset for get")
    return self._interface.wr_rd(offset)

  def set(self, value):
    """Set value for gpio driver

    TODO(tbroch) Add support for width > 1

    Args:
      value: integer value to write to gpio

    Raises:
      gpioError: if no offset in param dict
    """
    self._logger.debug("")
    (offset, mask) = self._get_offset_mask()
    if offset is None:
      raise gpioError("No offset for set")
    self._interface.wr_rd(offset, 1, value)
