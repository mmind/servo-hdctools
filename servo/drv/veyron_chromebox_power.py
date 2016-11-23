# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import power_state
import time

class veyronChromeboxPower(power_state.PowerStateDriver):
  """Driver for power_state for the veyron chromebox boards.

  Chromebox(e.g. fievel) has no EC and thus uses a physical recovery button.

  """

  # Time in seconds to allow the firmware to detect the
  # 'rec_mode' signal after cold reset.
  _RECOVERY_DETECTION_DELAY = 2.5

  # Time in seconds to wait device off when cold_reset:on
  _POWER_OFF_DETECTION_DELAY= 1

  def _power_off(self):
    """Power off the DUT.

    Chromebox(without ec) can not be powered down via Servo.
    Instead, this implementation will leave cold_reset on
    indefinitely in order to simulate power off.

    """
    self._interface.set('cold_reset', 'on')

    # Holding to make sure the device can actually done, think about this:
    #   dut-control power_state:off power_state:on
    # It supposed to turn device off then on, but could fail without a delay.
    time.sleep(self._POWER_OFF_DETECTION_DELAY)

  def _power_on_rec(self):
    """Power on in recovery mode."""
    self._interface.set('rec_mode', self.REC_ON)
    self._reset_cycle()
    time.sleep(self._RECOVERY_DETECTION_DELAY)
    self._interface.set('rec_mode', self.REC_OFF)

  def _power_on_normal(self):
    """Power on in normal mode"""
    self._interface.set('rec_mode', self.REC_OFF)
    # Disable cold_reset in case it had been enabled by power_off.
    self._interface.set('cold_reset', 'off')
    # If DUT off by _power_off(), then we don't need a power_key event,
    # otherwise, it's need a power_key pressed.
    self._interface.power_key(0.7)

  def _power_on(self, rec_mode):
    """Power on the DUT.

    Args:
      rec_mode: Setting of recovery mode to be applied at power on.

    """
    if rec_mode == self.REC_ON:
      self._power_on_rec()
    else:
      self._power_on_normal()
