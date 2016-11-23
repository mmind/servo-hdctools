# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of drv=cr50.

Provides the following Cr50 controlled function:
  cold_reset
  warm_reset
  pwr_button
  ccd_ec_uart_en
"""

import pty_driver


class cr50Error(Exception):
  """Exception class for Cr50."""


class cr50(pty_driver.ptyDriver):
  """Object to access drv=cr50 controls.

  Note, instances of this object get dispatched via base class,
  HwDriver's get/set method. That method ultimately calls:
    "_[GS]et_%s" % params['subtype'] below.

  For example, a control to read kbd_en would be dispatched to
  call _Get_kbd_en.
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
    super(cr50, self).__init__(interface, params)
    self._logger.debug("")

  def _Get_cold_reset(self):
    """Getter of cold_reset.

    Returns:
      0: cold_reset off.
      1: cold_reset on.
    """
    result = self._issue_cmd_get_results(
        "ecrst", ["EC_RST_L is (asserted|deasserted)"])[0]
    if result is None:
      raise cr50Error("Cannot retrieve ecrst result on cr50 console.")
    return 1 if result[1] == "asserted" else 0

  def _Set_cold_reset(self, value):
    """Setter of cold_reset.

    Args:
      value: 0=off, 1=on.
    """
    if value == 0:
      self._issue_cmd("ecrst off")
    else:
      self._issue_cmd("ecrst on")

  def _Get_warm_reset(self):
    """Getter of warm_reset.

    Returns:
      0: warm_reset off.
      1: warm_reset on.
    """
    result = self._issue_cmd_get_results(
        "sysrst", ["SYS_RST_L is (asserted|deasserted)"])[0]
    if result is None:
      raise cr50Error("Cannot retrieve sysrst result on cr50 console.")
    return 1 if result[1] == "asserted" else 0

  def _Set_warm_reset(self, value):
    """Setter of warm_reset.

    Args:
      value: 0=off, 1=on.
    """
    if value == 0:
      self._issue_cmd("sysrst off")
    else:
      self._issue_cmd("sysrst on")

  def _Get_pwr_button(self):
    """Getter of pwr_button.

    Returns:
      0: power button press.
      1: power button release.
    """
    result = self._issue_cmd_get_results(
        "powerbtn", ["powerbtn: (forced press|pressed|released)"])[0]
    if result is None:
      raise cr50Error("Cannot retrieve power button result on cr50 console.")
    return 1 if result[1] == "released" else 0

  def _Set_pwr_button(self, value):
    """Setter of pwr_button.

    Args:
      value: 0=press, 1=release.
    """
    if value == 0:
      self._issue_cmd("powerbtn press")
    else:
      self._issue_cmd("powerbtn release")

  def _Get_ccd_ec_uart_en(self):
    """Getter of ccd_ec_uart_en.

    Returns:
      0: EC UART disabled.
      1: EC UART enabled.
    """
    # Check the EC UART result as the AP's and Cr50's UART are always on.
    result = self._issue_cmd_get_results(
        "ccd", ["EC UART:\s*(enabled|disabled)"])[0]
    if result is None:
      raise cr50Error("Cannot retrieve ccd uart result on cr50 console.")
    return 1 if result[1] == "enabled" else 0

  def _Set_ccd_ec_uart_en(self, value):
    """Setter of ccd_ec_uart_en.

    Args:
      value: 0=off, 1=on.
    """
    if value == 0:
      self._issue_cmd("ccd uart off")
    else:
      self._issue_cmd("ccd uart on")
