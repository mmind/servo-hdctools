# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Allow creation of uart/console interface via stm32 usb endpoint."""
import errno
import exceptions
import logging
import os
import pty
import select
import sys
import termios
import threading
import time
import tty
import usb

import stm32usb
import uart


class SuartError(Exception):
  """Class for exceptions of Suart."""
  def __init__(self, msg, value=0):
    """SuartError constructor.

    Args:
      msg: string, message describing error in detail
      value: integer, value of error when non-zero status returned.  Default=0
    """
    super(SuartError, self).__init__(msg, value)
    self.msg = msg
    self.value = value


class Suart(uart.Uart):
  """Provide interface to stm32 serial usb endpoint."""
  def __init__(self, vendor=0x18d1, product=0x501a, interface=0,
               serialname=None, ftdi_context=None):
    """Suart contstructor.

    Initializes stm32 USB stream interface.

    Args:
      vendor: usb vendor id of stm32 device
      product: usb product id of stm32 device
      interface: interface number of stm32 device to use
      serialname: n/a. Defaults to None.
      ftdi_context: n/a. Defaults to None.

    Raises:
      SuartError: If init fails
    """
    super(Suart, self).__init__()
    self._logger = logging.getLogger('Suart')
    self._logger.debug('')
    self._logger.debug('Suart opening %04x:%04x, intf %d, sn: %s' % (
        vendor, product, interface, serialname))

    self._susb = stm32usb.Susb(vendor=vendor, product=product,
        interface=interface, serialname=serialname, logger=self._logger)

    self._logger.debug("Set up stm32 uart")

  def __del__(self):
    """Suart destructor."""
    self._logger.debug('')

  def run_rx_thread(self):
    self._logger.debug('rx thread started on %s' % self.get_pty())

    ep = select.epoll()
    ep.register(self._ptym, select.EPOLLHUP)
    while True:
      events = ep.poll(0)
      # Check if the pty is connected to anything, or hungup.
      if not events:
        try:
          r = self._susb._read_ep.read(64, self._susb.TIMEOUT_MS)
          if r:
            os.write(self._ptym, r)

        except Exception as e:
          # If we miss some characters on pty disconnect, that's fine.
          # ep.read() also throws USBError on timeout, which we discard.
          if type(e) not in [exceptions.OSError, usb.core.USBError]:
            self._logger.debug("rx %s: %s" % (self.get_pty(), e))
      else:
        time.sleep(.1)

  def run_tx_thread(self):
    self._logger.debug("tx thread started on %s" % self.get_pty())

    ep = select.epoll()
    ep.register(self._ptym, select.EPOLLHUP)
    while True:
      events = ep.poll(0)
      # Check if the pty is connected to anything, or hungup.
      if not events:
        try:
          r = os.read(self._ptym, 64)
          if r:
            self._susb._write_ep.write(r, self._susb.TIMEOUT_MS)

        except Exception as e:
          self._logger.debug("tx %s: %s" % (self.get_pty(), e))
      else:
        time.sleep(.1)


  def run(self):
    """Creates pthreads to poll stm32 & PTY for data.
    """
    self._logger.debug('')

    m, s = os.openpty()
    self._ptyname = os.ttyname(s)
    self._logger.debug("PTY name: %s" % self._ptyname)

    self._ptym = m
    self._ptys = s

    os.fchmod(s, 0o660)

    # Change the owner and group of the PTY to the user who started servod.
    try:
      uid = int(os.environ.get('SUDO_UID', -1))
    except TypeError:
      uid = -1

    try:
      gid = int(os.environ.get('SUDO_GID', -1))
    except TypeError:
      gid = -1
    os.fchown(s, uid, gid)

    tty.setraw(self._ptym, termios.TCSADRAIN)

    # Generate a HUP flag on pty slave fd.
    os.fdopen(s).close()

    self._logger.debug('stm32 uart pty is %s' % self.get_pty())

    self._rx_thread = threading.Thread(target=self.run_rx_thread, args=[])
    self._rx_thread.daemon = True
    self._rx_thread.start()

    self._tx_thread = threading.Thread(target=self.run_tx_thread, args=[])
    self._tx_thread.daemon = True
    self._tx_thread.start()

    self._logger.debug('stm32 rx and tx threads started.')


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
    self._logger.debug('')
    return {'baudrate': 115200,
            'bits': 8,
            'parity': 0,
            'sbits': 1}


  def set_uart_props(self, line_props):
    """Set the uart's properties. Note that Suart cannot set properties
    and will fail if the properties are not the default 115200,8n1.

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
      SuartError: If requested line properties are not the default.
    """
    self._logger.debug('')
    curr_props = self.get_uart_props()
    for prop in line_props:
      if line_props[prop] != curr_props[prop]:
        raise SuartError("Line property %s cannot be set from %s to %s" % (
            prop, curr_props[prop], line_props[prop]))
    return True


  def get_pty(self):
    """Gets path to pty for communication to/from uart.

    Returns:
      String path to the pty connected to the uart
    """
    self._logger.debug('')
    return self._ptyname


def test():
  format='%(asctime)s - %(name)s - %(levelname)s'
  loglevel = logging.INFO
  if True:
    loglevel = logging.DEBUG
    format += ' - %(filename)s:%(lineno)d:%(funcName)s'
  format += ' - %(message)s'
  logging.basicConfig(level=loglevel, format=format)
  logger = logging.getLogger(os.path.basename(sys.argv[0]))
  logger.info('Start')

  sobj = Suart()
  sobj.run()
  logging.info('%s' % sobj.get_pty())

  # run() is a thread so just busy wait to mimic server
  while True:
    # ours sleeps to eleven!
    time.sleep(11)

if __name__ == '__main__':
  try:
    test()
  except KeyboardInterrupt:
    sys.exit(0)
