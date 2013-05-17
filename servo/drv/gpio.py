# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of type=gpio.
"""
import logging


import hw_driver


class gpioError(Exception):
  """Error class for gpio class."""


class gpio(hw_driver.HwDriver):
  """Object to access type=gpio controls.

  Mandatory Params:
    offset: integer, shift amount (left) to align GPIO bit correctly

  Optional Params:
    chip: Beaglebone gpio chip id.
    width: integer, number of contiguous bits in GPIO control
  """

  def __init__(self, interface, params):
    super(gpio, self).__init__(interface, params)
    # TODO (sbasi/tbroch) crbug.com/241507 - Deprecate Chip param.
    self._chip = params.get('chip', None)

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
      return self._interface.wr_rd(offset, width, chip=self._chip)

  def set(self, value):
    """Set value for gpio driver

    Args:
      value: integer value to write to gpio

    Raises:
      gpioError: if no offset in param dict
    """
    self._logger.debug("")
    (offset, width) = self._get_common_params()

    is_output = 1
    if 'od' in self._params:
      if width > 1:
        raise gpioError("Open drain not implemented for widths != 1")
      open_drain = self._params['od'].upper()
      if open_drain != "PU":
        raise gpioError("Unrecognized open-drain %s" % open_drain)
      if value == 1:
        is_output = 0

    if hasattr(self._interface, 'gpio_wr_rd'):
      self._interface.gpio_wr_rd(offset, width, is_output, value)
    else:
      self._interface.wr_rd(offset, width, is_output, value, chip=self._chip)

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
