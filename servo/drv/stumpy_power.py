# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for power_state for stumpy boards.
"""
import alex_power


class stumpyPower(alex_power.alexPower):
  def _power_off(self):
    # In test images in the lab, the 'autoreboot' upstart job will
    # commonly configure the unit so that it reboots after cold
    # reset.  Since we mustn't rely on the OS, we can't know for
    # sure whether the unit will be on or off after cold reset.
    #
    # Fortunately, the autoreboot setting only applies through one
    # reset.  So, after one reset, the unit may be on or off, but
    # autoreboot is disabled.  We can be sure to be off after a
    # second cold reset so long as it happens before the unit has a
    # chance to boot the OS and run the autoreboot job.
    self._cold_reset()
    self._cold_reset()
