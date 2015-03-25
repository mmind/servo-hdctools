# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import time

import cros_ec_softrec_power


class samusPower(cros_ec_softrec_power.crosEcSoftrecPower):

  """Driver for power_state for Samus."""

  def _cold_reset(self):
    """Apply cold reset to the DUT.

    This asserts, then de-asserts the 'cold_reset' signal and the
    'usbpd_reset' signal. Samus varies from the generic implementation
    in that the extra 'usbpd_reset' signal must be asserted to reset
    the PD MCU.

    """
    self._interface.set('cold_reset', 'on')
    self._interface.set('usbpd_reset', 'on')

    time.sleep(self._reset_hold_time)

    self._interface.set('cold_reset', 'off')
    self._interface.set('usbpd_reset', 'off')
    # After the reset, give the EC the time it needs to
    # re-initialize.
    time.sleep(self._reset_recovery_time)
