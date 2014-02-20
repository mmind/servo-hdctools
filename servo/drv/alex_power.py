# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for power_state for x86-alex boards, and derivatives.
"""
import time

import power_state


class alexPower(power_state.PowerStateDriver):
  # Time in seconds to allow the firmware to initialize itself and
  # present the "INSERT" screen in recovery mode before actually
  # inserting a USB stick to boot from.
  _RECOVERY_INSERT_DELAY = 10.0

  def _power_off(self):
    self._cold_reset()

  def _power_on(self, rec_mode):
    self._interface.set('rec_mode', rec_mode)
    self._interface.power_short_press()
    if rec_mode == self.REC_ON:
      time.sleep(self._RECOVERY_INSERT_DELAY)
      self._interface.set('rec_mode', self.REC_OFF)
