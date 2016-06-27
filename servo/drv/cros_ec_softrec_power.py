# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import time

import cros_ec_power


class crosEcSoftrecPower(cros_ec_power.CrosECPower):

  """Driver for power_state that uses the EC to trigger recovery.

  A number of boards (generally, the ARM based boards and some x86
  based board) require using the EC to trigger recovery mode.
  """

  _HOSTEVENT_RECOVERY_CMD = dict(rec_on='hostevent set 0x4000',
                                 rec_off='hostevent clear 0x4000',
                                 rec_off_clearb='hostevent clearb 0x4000',
                                 fastboot='hostevent set 0x1000000')
  # Time in seconds to allow the EC to pick up the recovery
  # host event.
  _RECOVERY_DETECTION_DELAY = 1

  def _power_on_ap(self):
    """Power on the AP after initializing recovery state."""
    self._interface.power_short_press()

  def _power_on_bytype(self, rec_mode, rec_type='rec_on'):
    if rec_mode == self.REC_ON:
      # Hold warm reset so the AP doesn't boot when EC reboots.
      self._interface.set('warm_reset', 'on')
      # Reset the EC to force it back into RO code; this clears
      # the EC_IN_RW signal, so the system CPU will trust the
      # upcoming recovery mode request.
      self._cold_reset()
      # Restart the EC, but leave the system CPU off...
      self._interface.set('ec_uart_regexp', 'None')
      self._interface.set('ec_uart_cmd', 'reboot ap-off')
      time.sleep(self._reset_recovery_time)
      # Now the EC keeps the AP off. Release warm reset before powering
      # on the AP.
      self._interface.set('warm_reset', 'off')
    else:
      # Need to clear the flag in secondary (B) copy of the host events if
      # we're in non-recovery mode.
      self._interface.set('ec_uart_cmd',
                          self._HOSTEVENT_RECOVERY_CMD['rec_off_clearb'])

    # Tell the EC to tell the CPU we're in recovery mode or non-recovery mode.
    self._interface.set('ec_uart_cmd', self._HOSTEVENT_RECOVERY_CMD[rec_type])
    time.sleep(self._RECOVERY_DETECTION_DELAY)
    self._power_on_ap()

  def _power_on(self, rec_mode):
    if rec_mode == self.REC_ON:
      rec_type='rec_on'
    else:
      rec_type='rec_off'

    self._power_on_bytype(rec_mode, rec_type)

  def _power_on_fastboot(self):
    self._power_on_bytype(self.REC_ON, rec_type='fastboot')
