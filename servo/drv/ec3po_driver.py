# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""EC-3PO Servo Driver."""

import logging

import hw_driver


class ec3poDriver(hw_driver.HwDriver):
  def __init__(self, interface, params):
    """Creates the driver for EC-3PO console interpreter.

    Args:
      interface: An EC3PO instance which is the interface to the console
        interpreter.
      params: A dictionary of params passed to HwDriver's init.
    """
    super(ec3poDriver, self).__init__(interface, params)
    self._logger = logging.getLogger('EC3PO Driver')
    self._interface = interface

  def _Set_interp_connect(self, state):
    """Set the interpreter's connection state to the UART.

    Args:
      state: A boolean indicating whether to connect or disconnect the
        intepreter from the UART.
    """
    self._interface.set_interp_connect(state)

  def _Get_interp_connect(self):
    """Get the state of the interpreter connection to the UART."""
    return self._interface.get_interp_connect()
