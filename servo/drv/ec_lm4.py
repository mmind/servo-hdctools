# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of type=ec_lm4.

Provides lm4-specific lid_open controls for backward compatibility on boards
where 'lidstate' console function does not exist.
"""
import ec

# The memory address storing lid switch state on lm4 ECs
LID_STATUS_ADDR = "0x40080730"
LID_STATUS_MASK = 0x1


class ecLm4(ec.ec):
  """Object to access drv=ec_lm4 controls.

  Note, instances of this object get dispatched via base class,
  HwDriver's get/set method. That method ultimately calls:
    "_[GS]et_%s" % params['subtype'] below.

  For example, a control to read lid_open would be dispatched to
  call _Get_lid_open.
  """

  def _Get_lid_open(self):
    """Getter of lid_open.

    Returns:
      0: Lid closed.
      1: Lid opened.
    """
    self._limit_channel()
    result = self._issue_cmd_get_results("rw %s" % LID_STATUS_ADDR,
        ["read %s = 0x.......(.)" % LID_STATUS_ADDR])[0]
    self._restore_channel()
    res_code = int(result[1], 16)
    return res_code & LID_STATUS_MASK
