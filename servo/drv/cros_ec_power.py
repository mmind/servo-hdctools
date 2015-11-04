# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import time

import power_state


class CrosECPower(power_state.PowerStateDriver):
  """Driver for power_state for boards support EC command."""
  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: driver interface object
      params: dictionary of params
    """
    super(CrosECPower, self).__init__(interface, params)
    self._shutdown_ec_command = self._params.get('shutdown_ec_command',
                                                 'apshutdown')
    self._shutdown_delay = float(self._params.get('shutdown_delay', 0.5))

  def _power_off(self):
    self._interface.set('ec_uart_regexp', 'None')
    self._interface.set('ec_uart_cmd', self._shutdown_ec_command)
    time.sleep(self._shutdown_delay)
