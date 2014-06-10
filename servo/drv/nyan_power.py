# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cros_ec_softrec_power


class nyanPower(cros_ec_softrec_power.crosEcSoftrecPower):
  """Driver for power_state for nyan boards, e.g., nyan, big, blaze."""

  def _reset_cycle(self):
    """Force a power cycle using cold reset with warm_reset set to on.

    After the call, the DUT will be powered on in normal (not
    recovery) mode; the call is guaranteed to work regardless of
    the state of the DUT prior to the call.  This call must use
    cold_reset to guarantee that the EC also restarts.
    warm_reset is set to on while calling cold_reset. This behavior
    is specific to nyan boards.

    """
    # cold_reset will set DUT to recovery screen.
    self._cold_reset()

    # TODO(http://code.google.com/p/chrome-os-partner/issues/detail?id=29333):
    # After that bug is fixed, this override of _reset_cycle can be removed.
    # Do a warm_reset to boot up the DUT.
    self._warm_reset()
