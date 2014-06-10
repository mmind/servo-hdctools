# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import time

import cros_ec_power


class crosEcHardrecPower(cros_ec_power.CrosECPower):

  """Driver for power_state that uses the rec_mode signal.

  A number of boards (generally x86-based systems) support triggering
  recovery with the hardware `rec_mode` signal.
  """

  # Time in seconds to allow the BIOS and EC to detect the
  # 'rec_mode' signal after cold reset.
  _RECOVERY_DETECTION_DELAY = 2.5

  def _power_on_rec(self):
    """Power on with recovery mode."""
    self._interface.set('rec_mode', self.REC_ON)
    time.sleep(self._RECOVERY_DETECTION_DELAY)
    self._cold_reset()
    time.sleep(self._RECOVERY_DETECTION_DELAY)
    self._interface.set('rec_mode', self.REC_OFF)

  def _power_on_normal(self):
    """Power on with in normal mode, i.e., no recovery."""
    self._interface.power_short_press()

  def _power_on(self, rec_mode):
    if rec_mode == self.REC_ON:
      self._power_on_rec()
    else:
      self._power_on_normal()
