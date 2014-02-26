# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for power_state for daisy boards.
"""
import time

import power_state

HOSTEVENT_KEYBOARD_RECOVERY = 0x00004000

class daisyPower(power_state.PowerStateDriver):
  _EC_CONSOLE_DELAY = 0.4

  def _power_off(self):
    self._cold_reset()
    time.sleep(self._EC_CONSOLE_DELAY)
    self._interface.power_long_press()

  def _power_on(self, rec_mode):
    if rec_mode == self.REC_ON:
      # Reset the EC to force it back into RO code; this clears
      # the EC_IN_RW signal, so the system CPU will trust the
      # upcoming recovery mode request.
      self._cold_reset()
      # Restart the EC, but leave the system CPU off...
      self._interface.set('ec_uart_cmd', 'reboot ap-off')
      time.sleep(self._EC_CONSOLE_DELAY)
      # ... and tell the EC to tell the CPU we're in recovery mode.
      self._interface.set('ec_uart_cmd',
                          'hostevent set %#x' % HOSTEVENT_KEYBOARD_RECOVERY)
    self._interface.power_short_press()