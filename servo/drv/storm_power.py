# Copyright 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import time

import power_state


class stormPower(power_state.PowerStateDriver):
  """Driver for power_state for storm-derived boards."""

  # Time in seconds to allow the firmware to detect the 'rec_mode' signal
  # after cold reset. How long holding the recovery button has different
  # meanings:
  #   > 8 seconds, < 16 seconds: power wash
  #   > 16 seconds: enter recovery mode
  _RECOVERY_DETECTION_DELAY = 20

  def _power_on_rec(self):
    """Power on in recovery mode."""
    self._interface.set('rec_mode', self.REC_ON)
    self._reset_cycle()
    time.sleep(self._RECOVERY_DETECTION_DELAY)
    self._interface.set('rec_mode', self.REC_OFF)

  def _power_on_normal(self):
    """Power on in normal mode, i.e., no recovery."""
    self._interface.set('rec_mode', self.REC_OFF)
    time.sleep(self._RECOVERY_DETECTION_DELAY)
    self._reset_cycle()

  def _power_on(self, rec_mode):
    if rec_mode == self.REC_ON:
      self._power_on_rec()
    else:
      self._power_on_normal()

  def _power_off(self):
    # There is no way turn off power on storm, so we hold cold_reset to on
    # so the host acts as if it's off.
    self._interface.set('cold_reset', 'on')
