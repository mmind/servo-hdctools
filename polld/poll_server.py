# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Polld Server."""

import logging
import os
import SimpleXMLRPCServer

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
      gpio_port: GPIO port
      edge: value in GPIO_EDGE_LIST[]
    """
    try:
      PollGpio.get_instance(port, edge).poll()
    except PollGpioError as e:
      raise PolldError('poll_gpio fail: %s' % e)
