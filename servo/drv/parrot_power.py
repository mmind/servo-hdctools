# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for power_state for parrot boards.
"""
import time

import power_state


class parrotPower(power_state.PowerStateDriver):
  """Power-state driver for Parrot.

  On Parrot, uncontrolled assertion of `cold_reset` sometimes
  leaves the DUT unresponsive.  The `_cold_reset()` method
  implemented in this class is the only known, reliable way to
  assert the `cold_reset` signal on Parrot.

  Also, the `rec_mode` signal on Parrot is finicky.  These are the
  rules:
   1. You can't read or write the signal unless the DUT is on.
   2. The setting of the signal is only sampled during a cold
      reset.  The sampled setting applies to every boot until the
      next cold reset.
   3. After cold reset, the signal is turned off.
  N.B.  Rule 3 is subtle.  Although `rec_mode` is off after reset,
  because of rule 2, the DUT will continue to boot with the prior
  recovery mode setting until the next cold reset.

  """

  # _PWR_BUTTON_READY_TIME: This represents the time after cold
  #   reset until the EC will be able to see a power button press.
  #   Used in _power_off().
  _PWR_BUTTON_READY_TIME = 4

  # _REC_MODE_READY_TIME: This represents the time after power on
  #   until the EC will be able to see changes to rec_mode.  Used
  #   in _power_on().
  _REC_MODE_READY_TIME = 0.75

  def _cold_reset(self):
    # The sequence here leaves the DUT powered on, similar to
    # Chrome EC devices.
    self._interface.set('pwr_button', 'press')
    super(parrotPower, self)._cold_reset()
    self._interface.set('pwr_button', 'release')

  def _warm_reset(self):
    # Parrot warm reset is broken. Use a cold reset instead.
    self._cold_reset()

  def _power_off(self):
    self._cold_reset()
    time.sleep(self._PWR_BUTTON_READY_TIME)
    self._interface.power_short_press()

  def _power_on(self, rec_mode):
    self._interface.power_short_press()
    time.sleep(self._REC_MODE_READY_TIME)
    self._interface.set('rec_mode', rec_mode)
    self._cold_reset()
