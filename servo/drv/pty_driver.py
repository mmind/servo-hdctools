# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import fdpexpect
import os
import pexpect

import hw_driver

class ptyError(Exception):
  """Exception class for ec."""


class ptyDriver(hw_driver.HwDriver):
  """."""
  def __init__(self, interface, params):
    """."""
    super(ptyDriver, self).__init__(interface, params)
    self._child = None
    self._fd = None
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

  def _flush(self):
    """Flush EC console output to prevent previous messages interfering."""
    self._child.sendline("")
    while True:
      try:
        self._child.expect(".", timeout=0.01)
      except pexpect.TIMEOUT:
        break

  def _send(self, cmd):
    """Send command to EC.

    This function always flush EC console before sending, and is used as
    a wrapper function to make sure EC console is always flushed before
    sending commands.

    Args:
      cmd: The command string to send to EC.

    Raises:
      ptyError: Raised when writing to EC fails.
    """
    self._flush()
    if self._child.sendline(cmd) != len(cmd) + 1:
      raise ptyError("Failed to send command.")

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

  def _issue_cmd_get_results(self, cmd, regex_list, timeout=0.3):
    """Send command to EC and wait for response.

    This function waits for response message matching a regular
    expressions.

    Args:
      cmd: The command issued.
      regex_list: List of Regular expressions used to match response message.
        Note, list must be ordered.
      timeout: Timeout value for waiting UART response.

    Returns:
      List of tuples, each of which contains the entire matched string and
      all the subgroups of the match. None if not matched.
      For example:
        response of the given command:
          High temp: 37.2
          Low temp: 36.4
        regex_list:
          ['High temp: (\d+)\.(\d+)', 'Low temp: (\d+)\.(\d+)']
        returns:
          [('High temp: 37.2', '37', '2'), ('Low temp: 36.4', '36', '4')]

    Raises:
      ptyError: If timed out waiting for EC response
    """
    #import pdb; pdb.set_trace()
    result_list = []
    self._open()
    try:
      self._send(cmd)
      self._logger.debug("Sending cmd: %s" % cmd)
      for regex in regex_list:
        self._child.expect(regex, timeout)
        match = self._child.match
        lastindex = match.lastindex if match and match.lastindex else 0
        # Create a tuple which contains the entire matched string and all
        # the subgroups of the match.
        result = match.group(*range(lastindex + 1)) if match else None
        result_list.append(result)
        self._logger.debug("Result: %s" % str(result))
    except pexpect.TIMEOUT:
      raise ptyError("Timeout waiting for EC response.")
    finally:
      self._close()
    return result_list

  def _issue_cmd_get_multi_results(self, cmd, regex):
    """Send command to EC and wait for multiple response.

    This function waits for arbitary number of response message
    matching a regular expression.

    Args:
      cmd: The command issued.
      regex: Regular expression used to match response message.

    Returns:
      List of tuples, each of which contains the entire matched string and
      all the subgroups of the match. None if not matched.
    """
    result_list = []
    self._open()
    try:
      self._send(cmd)
      self._logger.debug("Sending cmd: %s" % cmd)
      while True:
        try:
          self._child.expect(regex, timeout=0.1)
          match = self._child.match
          lastindex = match.lastindex if match and match.lastindex else 0
          # Create a tuple which contains the entire matched string and all
          # the subgroups of the match.
          result = match.group(*range(lastindex + 1)) if match else None
          result_list.append(result)
          self._logger.debug("Got result: %s" % str(result))
        except pexpect.TIMEOUT:
          break
    finally:
      self._close()
    return result_list
