# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import time

import cros_ec_power_x86


class linkPower(cros_ec_power_x86.crosEcPowerX86):
  """Driver for power_state for link."""

  def _power_on_normal(self):
    self._cold_reset()
