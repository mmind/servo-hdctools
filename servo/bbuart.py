# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# TODO (sbasi) crbug.com/187492 - Implement BBuart.
"""Allow creation of uart interface for beaglebone devices."""

class BBuartError(Exception):
  """Class for exceptions of Buart."""
  def __init__(self, msg, value=0):
    """BBuartError constructor.

    Args:
      msg: string, message describing error in detail
      value: integer, value of error when non-zero status returned.  Default=0
    """
    super(BBuartError, self).__init__(msg, value)
    self.msg = msg
    self.value = value

class BBuart(object):

  def open(self):
    """Opens access to beaglebone uart interface.

    Raises:
      BBuartError: If open fails
    """
    pass

  def close(self):
    """Closes connection to beaglebone uart interface.

    Raises:
      BBuartError: If close fails
    """
    pass

  def run(self):
    """Creates a pthread to poll beaglebone & PTY for data.

    Raises:
      BBuartError: If thread creation fails
    """
    pass

  def get_uart_props(self):
    """Get the uart's properties.

    Returns:
      dict where:
        baudrate: integer of uarts baudrate
        bits: integer, number of bits of data Can be 5|6|7|8 inclusive
        parity: integer, parity of 0-2 inclusive where:
          0: no parity
          1: odd parity
          2: even parity
        sbits: integer, number of stop bits.  Can be 0|1|2 inclusive where:
          0: 1 stop bit
          1: 1.5 stop bits
          2: 2 stop bits
    """
    pass

  def set_uart_props(self, line_props):
    """Set the uart's properties.

    Args:
      line_props: dict where:
        baudrate: integer of uarts baudrate
        bits: integer, number of bits of data ( prior to stop bit)
        parity: integer, parity of 0-2 inclusive where
          0: no parity
          1: odd parity
          2: even parity
        sbits: integer, number of stop bits.  Can be 0|1|2 inclusive where:
          0: 1 stop bit
          1: 1.5 stop bits
          2: 2 stop bits

    Raises:
      BBuartError: If failed to set line properties
    """
    pass

  def get_pty(self):
    """Gets path to pty for communication to/from uart.

    Returns:
      String path to the pty connected to the uart
    """
    pass

  def get_capture_active(self):
    """Return state of the 'capture_active' control for this interface.

    Returns:
      Current capture mode expressed as an integer (0 or 1)
    """
    pass

  def set_capture_active(self, activate):
    """Enable/disable the capture mode on this interface.

    Args:
      activate: a Boolean, indicating whether capture should be activated or
                deactivated
    """
    pass

  def get_stream(self):
    """Return UART stream accumulated since last time"""
    pass