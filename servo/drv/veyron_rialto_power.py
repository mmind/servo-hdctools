# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import power_state
import time

class veyronRialtoPower(power_state.PowerStateDriver):
  """Driver for power_state for the veyron_rialto board.

  Rialto has no EC and thus uses a physical recovery button. It's similar
  to Chromeboxes but with some different hold time requirements.

  """

  # Time in seconds to allow the firmware to detect the
  # 'rec_mode' signal after cold reset.
  _RECOVERY_DETECTION_DELAY = 2.5

  def _power_off(self):
    """Power off the DUT.

    Rialto can not be powered down via Servo.  Instead, this implementation
    will leave cold_reset on indefinitely in order to simulate power off.

    """
    self._interface.set('cold_reset', 'on')

  def _power_on_rec(self):
    """Power on in recovery mode."""
    self._interface.set('rec_mode', self.REC_ON)
    self._reset_cycle()
    time.sleep(self._RECOVERY_DETECTION_DELAY)
    self._interface.set('rec_mode', self.REC_OFF)

  def _power_on_normal(self):
    """Power on in normal mode, i.e., no recovery."""
    self._interface.set('rec_mode', self.REC_OFF)
    # Disable cold_reset if it had been enabled by power_off.
    self._interface.set('cold_reset', 'off')

  def _power_on(self, rec_mode):
    """Power on the DUT.

    Args:
      rec_mode: Setting of recovery mode to be applied at power on.

    """
    if rec_mode == self.REC_ON:
      self._power_on_rec()
    else:
      self._power_on_normal()
