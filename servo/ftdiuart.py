# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Allow creation of uart interface via libftdiuart library for FTDI devices."""
import ctypes
import logging
import errno
import os
import sys
import termios
import threading
import time
import tty

import ftdi_utils
import ftdi_common


# TODO(tbroch) need some way to xref these to values in ftdiuart.h
FUART_NAME_SIZE = 128
FUART_BUF_SIZE = 128
FUART_USEC_SLEEP = 1000
FUART_MAX_BUFFER_SIZE = 20000 # Do not keep more than this number of bytes
                              # when capturing.

class FuartError(Exception):
  """Class for exceptions of Fuart."""
  def __init__(self, msg, value=0):
    """FuartError constructor.

    Args:
      msg: string, message describing error in detail
      value: integer, value of error when non-zero status returned.  Default=0
    """
    super(FuartError, self).__init__(msg, value)
    self.msg = msg
    self.value = value


class UartCfg(ctypes.Structure):
  """Defines uart configuration values.

  These values are supplied to the libftdi API:
    ftdi_set_line_property
    ftdi_set_baudrate

  Declared in ftdi_common.h and named uart_cfg.
  """
  _fields_ = [("baudrate", ctypes.c_uint),
              ("bits", ctypes.c_uint),
              ("parity", ctypes.c_uint),
              ("sbits", ctypes.c_uint)]


class FuartContext(ctypes.Structure):
  """Defines primary context structure for libftdiuart.

  Declared in ftdiuart.h and named fuart_context
  """
  _fields_ = [("fc", ctypes.POINTER(ftdi_common.FtdiContext)),
              ("gpio", ftdi_common.Gpio),
              ("name", ctypes.c_char * FUART_NAME_SIZE),
              ("cfg", UartCfg),
              ("is_open", ctypes.c_int),
              ("usecs_to_sleep", ctypes.c_int),
              ("fd", ctypes.c_int),
              ("buf",  ctypes.c_ubyte * FUART_BUF_SIZE),
              ("error", ctypes.c_int),
              ("lock", ctypes.POINTER(ctypes.c_int))]


class Fuart(object):
  """Provide interface to libftdiuart c-library via python ctypes module."""
  def __init__(self, vendor=ftdi_common.DEFAULT_VID,
               product=ftdi_common.DEFAULT_PID, interface=3,
               serialname=None,
               ftdi_context=None):
    """Fuart contstructor.

    Loads libraries for libftdi, libftdiuart.  Creates instance objects
    (Structures), FuartContext, FtdiContext and Gpio to iteract with the library
    and intializes them.

    Args:
      vendor: usb vendor id of FTDI device
      product: usb product id of FTDI device
      interface: interface number of FTDI device to use
      serialname: string of device serialname/number as defined in FTDI eeprom.
      ftdi_context: ftdi context created previously or None if one should be
        allocated here.  This shared context functionality is seen in miniservo
        which has a uart + 4 gpios

    Raises:
      FuartError: If either ftdi or fuart inits fail
    """
    self._logger = logging.getLogger("Fuart")
    self._logger.debug("")
    (self._flib, self._lib) = ftdi_utils.load_libs(ftdi_common.FTDI_LIB_NAME,
                                                   "ftdiuart")
    self._fargs = ftdi_common.FtdiCommonArgs(vendor_id=vendor,
                                             product_id=product,
                                             interface=interface,
                                             serialname=serialname,
                                             speed=115200,
                                             bits=8, # BITS_8 in ftdi.h
                                             partity=0, # NONE in ftdi.h
                                             sbits=0 # STOP_BIT_1 in ftdi.h
                                             )
    self._is_closed = True
    self._fuartc = FuartContext()

    self._capture_active = 0
    self._capture_buffer = []
    self._capture_thread = None
    self._capture_lock = threading.Lock()
    # Remember parent thread to be able to find out if it is still running.
    self._parent_thread = threading.current_thread()

    if ftdi_context:
      self._fc = ftdi_context
    else:
      self._fc = ftdi_common.FtdiContext()
      err = self._flib.ftdi_init(ctypes.byref(self._fc))
      if err:
        raise FuartError("doing ftdi_init", err)

    err = self._lib.fuart_init(ctypes.byref(self._fuartc),
                               ctypes.byref(self._fc))
    if err:
      raise FuartError("doing fuart_init", err)

  def __del__(self):
    """Fuart destructor."""
    self._logger.debug("")
    if not self._is_closed:
      self.close()

  def _capture_function(self):
    """Capture uart output and store it in the buffer.

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

    uart_fd = os.open(self._fuartc.name,
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
      if len(self._capture_buffer) < FUART_MAX_BUFFER_SIZE:
        buffer_overflow = False
        self._capture_buffer.append(data)
      else:
        if not buffer_overflow:
          self._capture_buffer.append(
            '\n\n........capture buffer overflow........\n\n')
          buffer_overflow = True
      self._capture_lock.release()
    termios.tcsetattr(uart_fd, termios.TCSANOW, saved_conf)
    os.close(uart_fd)
    self._logger.debug('quitting capture')

  def open(self):
    """Opens access to FTDI uart interface.

    Raises:
      FuartError: If open fails
    """
    self._logger.debug("")
    err = self._lib.fuart_open(ctypes.byref(self._fuartc),
                               ctypes.byref(self._fargs))
    if err:
      raise FuartError("doing fuart_open", err)
    self._is_closed = False

  def close(self):
    """Closes connection to FTDI uart interface.

    Raises:
      FuartError: If close fails
    """
    self._logger.debug("")
    err = self._lib.fuart_close(ctypes.byref(self._fuartc))
    if err:
      raise FuartError("doing fuart_close", err)
    self._is_closed = True

  def run(self):
    """Creates a pthread to poll FTDI & PTY for data.

    Raises:
      FuartError: If thread creation fails
    """
    self._logger.debug("")
    if self._is_closed:
      self.open()

    err = self._lib.fuart_run(ctypes.byref(self._fuartc), FUART_USEC_SLEEP)
    if err:
      raise FuartError("Failure with fuart_run", err)

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
    self._logger.debug("")
    return {'baudrate': self._fuartc.cfg.baudrate,
            'bits': self._fuartc.cfg.bits,
            'parity': self._fuartc.cfg.parity,
            'sbits': self._fuartc.cfg.sbits}

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
      FuartError: If failed to set line properties
    """
    self._logger.debug("")
    if line_props['bits'] not in (5,6,7,8):
      raise FuartError("Data bits must be 5|6|7|8")
    if line_props['sbits'] not in (0,1,2):
      raise FuartError("Stop bits must be 0|1|2.  Where 0==1bit," + \
                         "1==1.5bits 2==2bits")
    if line_props['parity'] not in (0,1,2):
      raise FuartError("Parity must be 0|1|2.  Where 0==none, 1==odd, 2==even")

    cfg = UartCfg()
    cfg.baudrate = line_props['baudrate']
    cfg.bits = line_props['bits']
    cfg.parity = line_props['parity']
    cfg.sbits = line_props['sbits']

    if self._lib.fuart_stty(ctypes.byref(self._fuartc), ctypes.byref(cfg)):
      raise FuartError("Failed to set line properties requested")

  def get_pty(self):
    """Gets path to pty for communication to/from uart.

    Returns:
      String path to the pty connected to the uart
    """
    self._logger.debug("")
    return self._fuartc.name

  def get_capture_active(self):
    """Return state of the 'capture_active' control for this interface.

    Returns:
      Current capture mode expressed as an integer (0 or 1)
    """
    self._logger.debug("")
    return self._capture_active

  def set_capture_active(self, activate):
    """Enable/disable the capture mode on this interface.

    Args:
      activate: a Boolean, indicating whether capture should be activated or
                deactivated
    """
    self._logger.debug("")
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
    """Return UART stream accumulated since last time"""
    self._logger.debug("")
    self._capture_lock.acquire()
    rv = repr(''.join(self._capture_buffer))
    self._capture_buffer = []
    self._capture_lock.release()
    return rv

def test():
  (options, args) = ftdi_utils.parse_common_args(interface=3)

  format="%(asctime)s - %(name)s - %(levelname)s"
  loglevel = logging.INFO
  if options.debug:
    loglevel = logging.DEBUG
    format += " - %(filename)s:%(lineno)d:%(funcName)s"
  format += " - %(message)s"
  logging.basicConfig(level=loglevel, format=format)
  logger = logging.getLogger(os.path.basename(sys.argv[0]))
  logger.info("Start")

  fobj = Fuart(options.vendor, options.product, options.interface)
  fobj.run()
  logging.info("%s" % fobj.get_pty())

  # run() is a thread so just busy wait to mimic server
  while True:
    # ours sleeps to eleven!
    time.sleep(11)

if __name__ == "__main__":
  try:
    test()
  except KeyboardInterrupt:
    sys.exit(0)
