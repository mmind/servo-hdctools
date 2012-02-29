# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of type=uart.
"""
import logging


import drv.hw_driver


class uartError(Exception):
  """Error class for uart class."""


class uart(drv.hw_driver.HwDriver):
  """Object to access type=uart controls.

  Note, instances of this object get dispatched via base class,
  HwDriver's get/set method.  That method ulitimately calls:
    "_[GS]et_%s" % params['subtype'] below.

  For example, a control to read pty attached to the uart device would
  be dispatched to call _Get_pty.
  """

  def _Get_pty(self):
    """Get pty device attached to uart.

    Retuns:
      Path to pty attached to the uart.
    """
    return self._interface.get_pty()
