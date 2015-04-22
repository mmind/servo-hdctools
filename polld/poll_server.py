# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Polld Server."""

import logging

import poll_common
from poll_gpio import PollGpio, PollGpioError


class PolldError(Exception):
  """Exception class for polld."""
  pass


class Polld(object):
  """Main class for polld daemon."""

  def __init__(self):
    """Polld constructor."""
    self._logger = logging.getLogger('Polld')

  def poll_gpio(self, port, edge):
    """Long-polls a GPIO port.

    Args:
      port: GPIO port
      edge: value in GPIO_EDGE_LIST[]
    """
    try:
      PollGpio.get_instance(port, edge).poll(edge)
    except PollGpioError as e:
      raise PolldError('poll_gpio fail: %s' % e)

  def read_gpio(self, port):
    """Reads current value of a GPIO port.

    Args:
      port: GPIO port

    Returns:
      (int) 1 for GPIO high, 0 for low.
    """
    try:
      return PollGpio.get_instance(port).read()
    except PollGpioError as e:
      raise PolldError('poll_gpio fail: %s' % e)

  def write_gpio(self, port, value):
    """Writes value to a GPIO port.

    Be aware that GPIO direction will be set to output mode.

    Args:
      port: GPIO port
      value: GPIO value, regard as 1(GPIO high) for any non-zero value.
    """
    try:
      PollGpio.get_instance(port).write(1 if value else 0)
    except PollGpioError as e:
      raise PolldError('poll_gpio fail: %s' % e)
