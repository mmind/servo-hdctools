# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import ast
import contextlib
import errno
import os
import pexpect
from pexpect import fdpexpect
import re

import hw_driver
import servo.terminal_freezer


DEFAULT_UART_TIMEOUT = 3  # 3 seconds is plenty even for slow platforms

class ptyError(Exception):
  """Exception class for pty errors."""

UART_PARAMS = {'uart_cmd': None,
               'uart_multicmd': None,
               'uart_regexp': None,
               'uart_timeout': DEFAULT_UART_TIMEOUT
               }

class ptyDriver(hw_driver.HwDriver):
  """."""
  def __init__(self, interface, params):
    """."""
    super(ptyDriver, self).__init__(interface, params)
    self._child = None
    self._fd = None
    self._pty_path = self._interface.get_pty()
    self._dict = UART_PARAMS
    self._interface = interface

  @contextlib.contextmanager
  def _open(self):
    """Connect to serial device and create pexpect interface.

    Note that this should be called with the 'with-syntax' since it will handle
    freezing and thawing any other terminals that are using this PTY as well as
    closing the connection when finished.
    """
    # Freeze any terminals that are using this PTY, otherwise when we check
    # for the regex matches, it will fail with a 'resource temporarily
    # unavailable' error.
    with servo.terminal_freezer.TerminalFreezer(self._pty_path):
      self._logger.debug('opening %s', self._pty_path)
      self._fd = os.open(self._pty_path, os.O_RDWR | os.O_NONBLOCK)
      try:
        self._child = fdpexpect.fdspawn(self._fd)
        # pexpect dafaults to a 100ms delay before sending characters, to
        # work around race conditions in ssh. We don't need this feature
        # so we'll change delaybeforesend from 0.1 to 0.001 to speed things up.
        self._child.delaybeforesend = 0.001
        yield
      finally:
        self._close()

  def _close(self):
    """Close serial device connection."""
    os.close(self._fd)
    self._fd = None
    self._child = None

  def _flush(self):
    """Flush device output to prevent previous messages interfering."""
    if self._child.sendline("") != 1:
      raise ptyError("Failed to send newline.")
    while True:
      try:
        self._child.expect(".", timeout=0.01)
      except (pexpect.TIMEOUT, pexpect.EOF):
        break
      except OSError, e:
        # EAGAIN indicates no data available, maybe we didn't wait long enough
        if e.errno != errno.EAGAIN:
          raise
        self._logger.debug("pty read returned EAGAIN")
        break

  def _send(self, cmds):
    """Send command to EC.

    This function always flushes serial device before sending, and is used as
    a wrapper function to make sure the channel is always flushed before
    sending commands.

    Args:
      cmds: The commands to send to the device, either a list or a string.

    Raises:
      ptyError: Raised when writing to the device fails.
    """
    self._flush()
    if not isinstance(cmds, list):
      cmds = [cmds]
    for cmd in cmds:
      if self._child.sendline(cmd) != len(cmd) + 1:
        raise ptyError("Failed to send command.")

  def _issue_cmd(self, cmds):
    """Send command to the device and do not wait for response.

    Args:
      cmds: The commands to send to the device, either a list or a string.
    """
    self._issue_cmd_get_results(cmds, [])

  def _issue_cmd_get_results(self, cmds,
                             regex_list, timeout=DEFAULT_UART_TIMEOUT):
    """Send command to the device and wait for response.

    This function waits for response message matching a regular
    expressions.

    Args:
      cmds: The commands issued, either a list or a string.
      regex_list: List of Regular expressions used to match response message.
        Note1, list must be ordered.
        Note2, empty list sends and returns.

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
      ptyError: If timed out waiting for a response
    """
    result_list = []
    with self._open():
      try:
        self._send(cmds)
        self._logger.debug("Sent cmds: %s" % cmds)
        if regex_list:
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
        self._logger.debug("Before: ^%s^" % self._child.before)
        self._logger.debug("After: ^%s^" % self._child.after)
        raise ptyError("Timeout waiting for response.")
    return result_list

  def _issue_cmd_get_multi_results(self, cmd, regex):
    """Send command to the device and wait for multiple response.

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
    with self._open():
      self._send(cmd)
      self._logger.debug("Sending cmd: %s" % cmd)
      if regex:
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
    return result_list

  def _Set_uart_timeout(self, timeout):
    """Set timeout value for waiting for the device response.

    Args:
      timeout: Timeout value in second.
    """
    self._dict['uart_timeout'] = timeout

  def _Get_uart_timeout(self):
    """Get timeout value for waiting for the device response.

    Returns:
      Timeout value in second.
    """
    return self._dict['uart_timeout']

  def _Set_uart_regexp(self, regexp):
    """Set the list of regular expressions which matches the command response.

    Args:
      regexp: A string which contains a list of regular expressions.
    """
    if not isinstance(regexp, str):
      raise ecError('The argument regexp should be a string.')
    self._dict['uart_regexp'] = ast.literal_eval(regexp)

  def _Get_uart_regexp(self):
    """Get the list of regular expressions which matches the command response.

    Returns:
      A string which contains a list of regular expressions.
    """
    return str(self._dict['uart_regexp'])

  def _Set_uart_cmd(self, cmd):
    """Set the UART command and send it to the device.

    If ec_uart_regexp is 'None', the command is just sent and it doesn't care
    about its response.

    If ec_uart_regexp is not 'None', the command is send and its response,
    which matches the regular expression of ec_uart_regexp, will be kept.
    Use its getter to obtain this result. If no match after ec_uart_timeout
    seconds, a timeout error will be raised.

    Args:
      cmd: A string of UART command.
    """
    if self._dict['uart_regexp']:
      self._dict['uart_cmd'] = self._issue_cmd_get_results(
          cmd,
          self._dict['uart_regexp'],
          self._dict['uart_timeout'])
    else:
      self._dict['uart_cmd'] = None
      self._issue_cmd(cmd)

  def _Set_uart_multicmd(self, cmds):
    """Set multiple UART commands and send them to the device.

    Note that ec_uart_regexp is not supported to match the results.

    Args:
      cmds: A semicolon-separated string of UART commands.
    """
    self._issue_cmd(cmds.split(';'))

  def _Get_uart_cmd(self):
    """Get the result of the latest UART command.

    Returns:
      A string which contains a list of tuples, each of which contains the
      entire matched string and all the subgroups of the match. 'None' if
      the ec_uart_regexp is 'None'.
    """
    return str(self._dict['uart_cmd'])

  def _Set_uart_capture(self, cmd):
    """Set UART capture mode (on or off).

    Once capture is enabled, UART output could be collected periodically by
    invoking _Get_uart_stream() below.

    Args:
      cmd: an int, 1 of on, 0 for off
    """
    self._interface.set_capture_active(cmd)

  def _Get_uart_capture(self):
    """Get the UART capture mode (on or off)."""
    return self._interface.get_capture_active()

  def _Get_uart_stream(self):
    """Get uart stream generated since last time."""
    return self._interface.get_stream()
