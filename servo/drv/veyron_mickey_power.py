# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for power_state for veyron_mickey board.
"""
import power_state
import time

class veyronMickeyPower(power_state.PowerStateDriver):

  """
  Mickey has no EC and thus uses a physical recovery button. It's similar
  to Chromeboxes but with some different hold time requirements.
  """

  # Time in seconds to allow the firmware to detect the
  # 'rec_mode' signal after cold reset.
  _RECOVERY_DETECTION_DELAY = 2.5

  def _reset_cycle(self):
    """Force a power cycle using cold reset."""
    self._cold_reset()
    # AP isn't powered on after cold reset, so power it on.
    self._interface.power_key(0.7)

  def _power_off(self):
    self._cold_reset()

  def _power_on_rec(self):
    """Power on in recovery mode."""
    self._interface.set('rec_mode', self.REC_ON)
    self._reset_cycle()
    time.sleep(self._RECOVERY_DETECTION_DELAY)
    self._interface.set('rec_mode', self.REC_OFF)

  def _power_on_normal(self):
    """Power on in normal mode, i.e., no recovery."""
    self._interface.set('rec_mode', self.REC_OFF)
    self._interface.power_key(0.7)

  def _power_on(self, rec_mode):
    if rec_mode == self.REC_ON:
      self._power_on_rec()
    else:
      self._power_on_normal()
