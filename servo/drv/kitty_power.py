# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for power_state for kitty board.
"""
import cros_ec_hardrec_power

class kittyPower(cros_ec_hardrec_power.crosEcHardrecPower):

  """
  kitty uses 'rec_mode' signal (recovery button) to enter RECOVERY mode.
  Also, the driver uses long-press of power_button to turn off power.
  """

  # _PWR_BUTTON_SHUTDOWN_TIME: This represents the long-press time of power
  # button.  Used in _power_off().
  _PWR_BUTTON_SHUTDOWN_TIME = 10

  def _power_off(self):
    self._interface.power_key(self._PWR_BUTTON_SHUTDOWN_TIME)
