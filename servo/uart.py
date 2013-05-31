# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Common Functionality required by Servo Uart Interfaces."""
import errno
import logging
import os
import termios
import threading
import time
import tty

MAX_BUFFER_SIZE = 20000 # Do not keep more than this number of bytes
                        # when capturing.

class Uart(object):
  """Base Class for UART interface implementations.

  Most the common functionality involves capturing the UART stream as this is
  not implementation dependent.

  Instance Variables:
  _capture_active: boolean indicating if we are currently capturing.
  _capture_buffer: buffer of values read off the UART port.
  _capture_thread: thread currently polling and reading values off the UART
                   port.
  _capture_lock: lock used to protect the _capture_buffer.
  """

  def __init__(self):
    self._logger = logging.getLogger('Uart')
    self._capture_active = False
    self._capture_buffer = []
    self._capture_thread = None
    self._capture_lock = threading.Lock()
    # Remember parent thread to be able to find out if it is still running.
    self._parent_thread = threading.current_thread()

  def _capture_function(self):
    """Captures uart output and store it in the buffer.

    This function runs on a separate thread.

    Open the uart interface in non-blocking mode and start polling it for
    data, adding data to _capture_buffer until it overflows (in which case add
    an overflow indication and start dropping data on the floor).

    Adding stuff to _capture_buffer is protected by _capture_lock. The client
    is supposed to be reading data, each read attempt copying _capture_buffer
    contents to the client and emptying the buffer.

    Finish when the client requests to stop capturing or when the parent
    thread terminates for whatever reason.

    Raises:
      OSError in case attempt to read fails for an unexpected reason.
    """
    self._logger.debug('starting capture')

    uart_fd = os.open(self.get_pty(),
                      os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY)
    saved_conf = termios.tcgetattr(uart_fd)
    tty.setraw(uart_fd)

    buffer_overflow = False

    while self._capture_active and self._parent_thread.is_alive():
      try:
        data = os.read(uart_fd, 100)
      except OSError, e:
        if e.errno == errno.EWOULDBLOCK: # Data unavailable
          time.sleep(.1)
          continue
        os.close(uart_fd)
        raise
      self._capture_lock.acquire()
      if len(self._capture_buffer) < MAX_BUFFER_SIZE:
        buffer_overflow = False
        self._capture_buffer.append(data)
      elif buffer_overflow:
        self._capture_buffer.append(
            '\n\n........capture buffer overflow........\n\n')
        buffer_overflow = True
      self._capture_lock.release()
    termios.tcsetattr(uart_fd, termios.TCSANOW, saved_conf)
    os.close(uart_fd)
    self._logger.debug('quitting capture')

  def open(self):
    """Opens access to uart interface."""
    raise NotImplementedError('open not yet implemented.')

  def close(self):
    """Closes connection to FTDI uart interface."""
    raise NotImplementedError('close not yet implemented.')

  def run(self):
    """Creates a pthread to poll PTY for data."""
    raise NotImplementedError('run not yet implemented.')

  def get_uart_props(self):
    """Gets the uart's properties.

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
    raise NotImplementedError('get_uart_props not yet implemented.')

  def _uart_props_validation(self, line_props, exception_type=Exception):
    """Validate the line_props.

    If they are invalid raise an exception of type exception_type.

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
      exception_type: type of exception to throw if line_props are invalid.

    Raises:
      exception_type: If line_props are invalid.
    """
    if line_props['bits'] not in [5, 6, 7, 8]:
      raise exception_type('Data bits must be 5|6|7|8')
    if line_props['sbits'] not in [0, 1, 2]:
      raise exception_type('Stop bits must be 0|1|2.  Where 0==1bit, '
                           '1==1.5bits, 2==2bits')
    if line_props['parity'] not in [0, 1, 2]:
      raise exception_type('Parity must be 0|1|2.  Where 0==none, 1==odd, '
                           '2==even')

  def set_uart_props(self, line_props):
    """Sets the uart's properties.

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
    """
    raise NotImplementedError('set_uart_props not yet implemented.')

  def get_pty(self):
    """Gets path to pty for communication to/from uart.

    Returns:
      String path to the pty connected to the uart
    """
    raise NotImplementedError('get_pty not yet implemented.')

  def get_capture_active(self):
    """Returns state of the 'capture_active' control for this interface.

    Returns:
      Current capture mode expressed as an integer (0 or 1)
    """
    self._logger.debug('')
    return self._capture_active

  def set_capture_active(self, activate):
    """Enable/disable the capture mode on this interface.

    Args:
      activate: a Boolean, indicating whether capture should be activated or
                deactivated
    """
    self._logger.debug('')
    if activate and not self._capture_active:
      # Need to start capturing
      self._capture_buffer = []
      self._capture_thread = threading.Thread(target=self._capture_function)
      self._capture_active = activate
      self._capture_thread.start()
      return

    if not activate and self._capture_active:
      # Need to stop capturing
      self._capture_active = activate
      self._capture_thread.join()
      self._capture_thread = None

  def get_stream(self):
    """Return UART stream accumulated since last time."""
    self._logger.debug('')
    self._capture_lock.acquire()
    rv = repr(''.join(self._capture_buffer))
    self._capture_buffer = []
    self._capture_lock.release()
    return rv
