# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for power_state for daisy.
"""
import time

import cros_ec_power_arm

class daisyPower(cros_ec_power_arm.crosEcPowerArm):
  """Driver for power_state for daisy and spring."""

  def _power_off(self):
    """Power off DUT.

    ec_uart_cmd power off does not work for daisy and spring. Try to power DUT
    off with cold reset and long press on power button.
    """
    self._cold_reset()
    self._interface.power_long_press()
