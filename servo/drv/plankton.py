# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of type=plankton.

Provides the following functionis:
  usbc_role
  usbc_mux
  usbc_polarity
"""
import logging

import pty_driver

USBC_STATE = [None, None, None]

class planktonError(Exception):
  """Exception class for plankton."""


class plankton(pty_driver.ptyDriver):
  """Object to access drv=plankton controls.

  Note, instances of this object get dispatched via base class,
  HwDriver's get/set method. That method ultimately calls:
    "_[GS]et_%s" % params['subtype'] below.

  For example, a control to read usbc_role would be dispatched to
  call _Get_usbc_role.
  """

  STATE_ID_ROLE = 0
  STATE_ID_MUX = 1
  STATE_ID_POLARITY = 2

  USBC_ROLE_SINK = 0
  USBC_ROLE_5V_SRC = 1
  USBC_ROLE_12V_SRC = 2
  USBC_ROLE_ACTION = ["dev", "5v", "12v"]

  USBC_MUX_USB = 0
  USBC_MUX_DP = 1
  USBC_MUX_ACTION = ["usb", "dp"]

  USBC_POLARITY_0 = 0
  USBC_POLARITY_1 = 1
  USBC_POLARITY_ACTION = ["pol0", "pol1"]

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
    super(plankton, self).__init__(interface, params)
    self._logger.debug("")
    self._state = USBC_STATE

  def _set_usbc_action(self, action):
    self._issue_cmd("usbc %s" % action)

  def _Set_usbc_role(self, value):
    if self._state[self.STATE_ID_ROLE] != value:
      self._set_usbc_action(self.USBC_ROLE_ACTION[value])
      self._state[self.STATE_ID_ROLE] = value

  def _Get_usbc_role(self):
    if self._state[self.STATE_ID_ROLE] is None:
      raise planktonError("usbc_role not initialized")
    return self._state[self.STATE_ID_ROLE]

  def _Set_usbc_mux(self, value):
    if self._state[self.STATE_ID_MUX] != value:
      self._set_usbc_action(self.USBC_MUX_ACTION[value])
      self._state[self.STATE_ID_MUX] = value

  def _Get_usbc_mux(self):
    if self._state[self.STATE_ID_MUX] is None:
      raise planktonError("usbc_mux not initialized")
    return self._state[self.STATE_ID_MUX]

  def _Set_usbc_polarity(self, value):
    if self._state[self.STATE_ID_POLARITY] != value:
      self._set_usbc_action(self.USBC_POLARITY_ACTION[value])
      self._state[self.STATE_ID_POLARITY] = value

  def _Get_usbc_polarity(self):
    if self._state[self.STATE_ID_POLARITY] is None:
      raise planktonError("usbc_polarity not initialized")
    return self._state[self.STATE_ID_POLARITY]
