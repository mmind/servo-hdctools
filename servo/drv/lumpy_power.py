# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for power_state for lumpy boards.
"""
import alex_power


class lumpyPower(alex_power.alexPower):
  def _power_off(self):
    # The debug header for MP Lumpy's are missing a resistor to
    # support cold_reset.  Therefore to do a power off we simply
    # long hold the power button.  This should cover the most common
    # types of failures in the test lab.  However, this will fail if
    # the unit is already off.  In the test lab, there are two
    # possible outcomes:
    #   * If the unit stays on, a subsequent repair attempt should
    #     succeed.
    #   * If the unit powers itself off (e.g. because of some sort
    #     of OS bug), repair will never succeed.
    self._interface.power_long_press()
