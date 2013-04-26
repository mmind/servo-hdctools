# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of type=parrot_ec.

Provides the following EC controlled function:
  rec_mode
"""
import os
import pty_driver
import time

class parrotEcError(Exception):
  """Exception class for parrot ec."""


class parrotEc(pty_driver.ptyDriver):
  """Object to access drv=parrot_ec controls.

  Note, instances of this object get dispatched via base class,
  HwDriver's get/set method. That method ultimately calls:
    "_[GS]et_%s" % params['subtype'] below.

  For example, a control to read rec_mode would be dispatched to
  call _Get_rec_mode.
  """

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: FTDI interface object to handle low-level communication to
        control
      params: dictionary of params needed to perform operations on
        devices. The only params used now is 'subtype', which is used
        by get/set method of base class to decide how to dispatch
        request.
    """
    super(parrotEc, self).__init__(interface, params)
    self._logger.debug("")
    os.linesep = '\r'

  def _Set_rec_mode(self, value):
    """Setter of rec_mode.

    Sending the following EC commands via UART can set rec_mode on:
      fbf5=5a
      fbf6=a5

    Args:
      value: 0: rec_mode off; 1: rec_mode on.
    """
    if value == 1:
      self._issue_cmd("fbf5=5a")
      self._issue_cmd("fbf6=a5")
    else:
      self._issue_cmd("fbf5=00")
      self._issue_cmd("fbf6=00")

    # Giving Parrot a little bit of time to process the commands
    time.sleep(0.1)

  def _Get_rec_mode(self):
    """Getter of rec_mode.

    rec_mode is on if the EC registers match the following conditions:
      fbf5==5a
      fbf6==a5

    Returns:
      0: rec_mode off;
      1: rec_mode on.
    """
    result1 = self._issue_cmd_get_results("fbf5", ["=(..),"])[0]
    result2 = self._issue_cmd_get_results("fbf6", ["=(..),"])[0]
    if result1[1].lower() == '5a' and result2[1].lower() == 'a5':
      return 1
    else:
      return 0
