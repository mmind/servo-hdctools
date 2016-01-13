# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import time

import cros_ec_softrec_power


class veyronPower(cros_ec_softrec_power.crosEcSoftrecPower):
  """Driver for power_state for veyron-based laptops.

  This handles the veyron laptop models, which rely on a cros EC
  for their power_state implementation.

  Because of a bug (feature?) in the veyron EC, after powering off a
  veyron laptop with power_state:off twice in a row, the power
  button won't work reliably.  So, for veyron, we use the EC
  'power on' command to implement power_state:on.
  """

  def _power_on_ap(self):
    """Power on the AP after initializing recovery state."""
    self._interface.set('ec_uart_regexp', 'None')
    self._interface.set('ec_uart_cmd', 'power on')
