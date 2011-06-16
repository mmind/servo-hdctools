# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of type=gpio.
"""
import logging


import drv.hw_driver


class gpioError(Exception):
  """Error class for gpio class."""


class gpio(drv.hw_driver.HwDriver):
  """Object to access type=gpio controls.

  Mandatory Params:
    offset: integer, shift amount (left) to align GPIO bit correctly

  Optional Params:
    width: integer, number of contiguous bits in GPIO control
  """

  def get(self):
    """Get value for gpio driver
    
    Returns:
      integer value from gpio

    Raises:
      gpioError: if no offset in param dict
    """
    self._logger.debug("")
    (offset, width) = self._get_common_params()

    if hasattr(self._interface, 'gpio_wr_rd'):
      return self._interface.gpio_wr_rd(offset, width)
    else:
      return self._interface.wr_rd(offset, width)

  def set(self, value):
    """Set value for gpio driver

    Args:
      value: integer value to write to gpio

    Raises:
      gpioError: if no offset in param dict
    """
    self._logger.debug("")
    (offset, width) = self._get_common_params()

    if hasattr(self._interface, 'gpio_wr_rd'):
      self._interface.gpio_wr_rd(offset, width, 1, value)
    else:
      self._interface.wr_rd(offset, width, 1, value)

  def _get_common_params(self):
    """Get common parameters for gpio control

    Returns:
      tuple (offset, width) where
        offset: integer, left shift amount for location of gpio
        width: integer, bit width of gpio

    Raises:
      gpioError: if integer conversion of offset or width fail
    """
    self._logger.debug("")
    if 'offset' not in self._params:
      raise gpioError("No offset in params for gpio")
    try:
      offset = int(self._params['offset'])
    except ValueError, error:
      raise gpioError(error)

    width_str = self._params.get('width', '1')
    try:
      width = int(width_str)
    except ValueError, error:
      raise gpioError(error)
    return (offset, width)
