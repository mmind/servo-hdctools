# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for power_state for lumpy boards.
"""
import alex_power


class lumpyPower(alex_power.alexPower):
  # In the lab, the debug header for MP Lumpy's are missing a
  # resistor to support cold_reset.  This has two awkward effects:
  #  1) We can't implement _power_off() reliably.
  #  2) We can't implement _reset_cycle() at all.
  #
  # For power off, we make a best effort with a long press of the
  # power button.  This should cover the most common types of
  # failures in the test lab.  However, this will fail if the unit
  # was already off.  For repair in the test lab, there are two
  # possible outcomes:
  #   * If the unit stays on, a subsequent repair attempt should
  #     succeed.  The lab regularly retries, so this should
  #     eventually work.
  #   * If the unit powers itself off (e.g. because of some sort
  #     of OS bug), repair will never succeed.

  def _power_off(self):
    self._interface.power_long_press()

  def _reset_cycle(self):
    raise NotImplementedError('lumpy reset_cycle can\'t work')
