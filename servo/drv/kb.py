# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for keyboard control servo feature.
"""

import hw_driver

class kbError(Exception):
  """Error class for kb class."""


class kb(hw_driver.HwDriver):
  """HwDriver wrapper around servod's keyboard functions."""

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: driver interface object; servod in this case.
      params: dictionary of params; ignored.
    """
    super(kb, self).__init__(interface, params.copy())
    self._servo = interface

  def set(self, key):
    """Press and release the specified key combo for 0.1s.

    Args:
      key: see keyboard.xml's kb_precanned map,
        d_key="0" ctrl_d="1" ctrl_u="2" ctrl_enter="3" enter_key="4"
        refresh_key="5" ctrl_refresh_key="6" sysrq_x="7"

    Raises:
      kbError: if key is not a member of kb_precanned map.
    """
    if key == 0:
      self._servo.d_key(.1)
    elif  key == 1:
      self._servo.ctrl_d(.1)
    elif  key == 2:
      self._servo.ctrl_u(.1)
    elif  key == 3:
      self._servo.ctrl_enter(.1)
    elif  key == 4:
      self._servo.enter_key(.1)
    elif  key == 5:
      self._servo.refresh_key(.1)
    elif  key == 6:
      self._servo.ctrl_refresh_key(.1)
    elif  key == 7:
      self._servo.sysrq_x(.1)
    else:
      raise kbError("Unknown key enum: %s", key)
