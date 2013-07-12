# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of type=arm_ec.

"""

import ec


class armEc(ec.ec):
  """Object to access drv=arm_ec controls.

  Note, instances of this object get dispatched via base class,
  HwDriver's get/set method. That method ultimately calls:
    "_[GS]et_%s" % params['subtype'] below.

  For example, a control to read rec_mode would be dispatched to
  call _Get_rec_mode.
  """

  # As defined in include/ec_commands.h in the ec repo.
  REC_MODE = 1 << (15 - 1)

  def _Set_rec_mode(self, value):
    """Setter of rec_mode.

    Sending the following EC commands via UART sets rec_mode on:

      hostevent set 0x4000

    and the following sets rec mode off

      hostevent clear 0x4000
      hostevent clearb 0x4000

    Args:
      value: 0: rec_mode off; 1: rec_mode on.
    """
    if value:
        self._issue_cmd("hostevent set 0x%x" % self.REC_MODE)
    else:
        self._issue_cmd("hostevent clear 0x%x" % self.REC_MODE)
        self._issue_cmd("hostevent clearb 0x%x" % self.REC_MODE)

  def _Get_rec_mode(self):
    """Getter of rec_mode.

    rec_mode is retrieved as bit 0x4000 of the host event vector

    Returns:
      0: rec_mode off;
      1: rec_mode on.

    Raises:
      ec.ecError: when failing to retrieve rec_mode setting
    """

    # The hostevent command returns something like
    #> hostevent
    #Events:    0x00002000
    #Events-B:  0x00002000
    #>
    try:
        result = self._issue_cmd_get_results(
            "hostevent", ['Events:\s+(0x\w+)', ])[0][1]
        value = int(result, 16)
    except (IndexError, ValueError):
        raise ec.ecError("Unexpected 'hostevent' output")
    return 1 if (value & self.REC_MODE) else 0
