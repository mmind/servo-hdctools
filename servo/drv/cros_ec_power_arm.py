# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import time

import cros_ec_power

HOSTEVENT_KEYBOARD_RECOVERY = 0x00004000


class crosEcPowerArm(cros_ec_power.CrosECPower):
  """Driver for power_state for arm boards, e.g., daisy."""

  # Time in seconds to allow the BIOS and EC to detect the
  # 'rec_mode' signal after cold reset.
  _RECOVERY_DETECTION_DELAY = 0.4

  def _power_on(self, rec_mode):
    if rec_mode == self.REC_ON:
      # Reset the EC to force it back into RO code; this clears
      # the EC_IN_RW signal, so the system CPU will trust the
      # upcoming recovery mode request.
      self._cold_reset()
      # Restart the EC, but leave the system CPU off...
      self._interface.set('ec_uart_cmd', 'reboot ap-off')
      time.sleep(self._RECOVERY_DETECTION_DELAY)
      # ... and tell the EC to tell the CPU we're in recovery mode.
      self._interface.set('ec_uart_cmd',
                          'hostevent set %#x' % HOSTEVENT_KEYBOARD_RECOVERY)
    self._interface.power_short_press()
