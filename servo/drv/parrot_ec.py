# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of type=parrot_ec.

Provides the following EC controlled function:
  rec_mode
"""
import fdpexpect
import os
import pexpect

import hw_driver

class parrotEcError(Exception):
  """Exception class for parrot ec."""


class parrotEc(hw_driver.HwDriver):
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
    self._pty_path = self._interface.get_pty()

  def _open(self):
    """Open EC console and create pexpect interface."""
    self._fd = os.open(self._pty_path, os.O_RDWR | os.O_NONBLOCK)
    self._child = fdpexpect.fdspawn(self._fd)

  def _close(self):
    """Close EC console."""
    os.close(self._fd)
    self._fd = None
    self._child = None

  def _send(self, cmd):
    """Send command to EC.

    This function always flush EC console before sending, and is used as
    a wrapper function to make sure EC console is always flushed before
    sending commands.

    Args:
      cmd: The command string to send to EC.

    Raises:
      parrotEcError: Raised when writing to EC fails.
    """
    if self._child.send(cmd) != len(cmd):
      raise parrotEcError("Failed to send command.")

  def _issue_cmd(self, cmd):
    """Send command to EC and do not wait for response.

    Args:
      cmd: The command string to send to EC.
    """
    self._open()
    try:
      self._send(cmd)
      self._logger.debug("Sent cmd: %s" % cmd)
    finally:
      self._close()

  def _issue_cmd_get_results(self, cmd, regex_list):
    """Send command to EC and wait for response.

    This function waits for response message matching a regular
    expressions.

    Args:
      cmd: The command issued.
      regex_list: List of Regular expressions used to match response message.
        Note, list must be ordered.

    Returns:
      List of match objects of response message.

    Raises:
      parrotEcError: If timed out waiting for EC response
    """
    result_list = []
    self._open()
    try:
      self._send(cmd)
      self._logger.debug("Sending cmd: %s" % cmd)
      for regex in regex_list:
        self._child.expect(regex, timeout=0.3)
        result = self._child.match
        result_list.append(result)
        self._logger.debug("Result: %s" % str(result.groups()))
    except pexpect.TIMEOUT:
      raise parrotEcError("Timeout waiting for EC response.")
    finally:
      self._close()
    return result_list

  def _Set_rec_mode(self, value):
    """Setter of rec_mode.

    Sending the following EC commands via UART can set rec_mode on:
      fbf5=5a
      fbf6=a5

    Args:
      value: 0: rec_mode off; 1: rec_mode on.
    """
    if value == 1:
      self._issue_cmd("fbf5=5a\r")
      self._issue_cmd("fbf6=a5\r")
    else:
      self._issue_cmd("fbf5=00\r")
      self._issue_cmd("fbf6=00\r")

  def _Get_rec_mode(self):
    """Getter of rec_mode.

    rec_mode is on if the EC registers match the following conditions:
      fbf5==5a
      fbf6==a5

    Returns:
      0: rec_mode off;
      1: rec_mode on.
    """
    result1 = self._issue_cmd_get_results("fbf5\r", ["=(..),"])[0]
    result2 = self._issue_cmd_get_results("fbf6\r", ["=(..),"])[0]
    if result1.group(1).lower() == '5a' and result2.group(1).lower() == 'a5':
      return 1
    else:
      return 0
