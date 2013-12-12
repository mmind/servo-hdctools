# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# TODO (sbasi) crbug.com/187492 - Implement BBuart.
"""Allow creation of uart interface for beaglebone devices."""
import logging
import re
import subprocess

import bbmux_controller
import uart


BITS_RE = 'cs(?P<value>[5-8])'
PARITY_RE = '\-?parodd'
SBITS_RE = '(?P<value>\-?cstopb)'
SPEED_RE = 'speed (?P<value>[0-9]*) baud'
PARITY_MAP = {0 : '-parenb',
              1 : 'parodd',
              2 : '-parodd'}
SBITS_MAP = {0 : '-cstopb',
             1 : '-cstopb',
             2 : 'cstopb'}

# Map of interfaces to tty.
TTY_MAP = {1 : '/dev/ttyO1', # Uart1/ec_uart
           2 : '/dev/ttyO2', # Uart2/cpu_uart
           5 : '/dev/ttyO5'} # Uart3/legacy_uart- Uart3 is connected to
                             # Beaglebone Uart5.

DEFAULT_UART_SETTINGS = {'baudrate' : 115200,
                         'bits' : 8,
                         'parity' : 0,
                         'sbits' : 0}

STTY_EXTRA_ARGS = ['-ignbrk', '-brkint', '-ignpar', '-parmrk', '-inpck',
                   '-istrip', '-inlcr', '-igncr', '-icrnl', '-ixon', '-ixoff',
                   '-iuclc', '-ixany', '-imaxbel', '-iutf8', '-opost',
                   '-olcuc', '-ocrnl', 'onlcr', '-onocr', '-onlret', '-ofill',
                   '-ofdel', 'nl0', 'cr0', 'tab0', 'bs0', 'vt0', 'ff0',
                   '-isig', '-icanon', '-iexten', '-echo', '-echoe', '-echok',
                   '-echonl', '-noflsh', '-xcase', '-tostop', '-echoprt',
                   '-echoctl', '-echoke']

# Uart Signal Names
TXD_PATTERN = 'uart%d_txd'
TXD_MODE = 0x0
RXD_PATTERN = 'uart%d_rxd'
RXD_MODE = 0X2


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

class BBuart(uart.Uart):
  """Provides interface to a beaglebone's UART interfaces.

  Instance Variables:
    _interface: interface dictionary for this interface.
    _uart_num: UART port number for this controller.
    _pty: pseudo terminal for this UART interface.
    _bbmux_controller: controller to select and setup signals on the
                        beaglebone's pins.
  """

  def __init__(self, interface):
    super(BBuart, self).__init__()
    self._interface = interface
    self._uart_num = interface['uart_num']
    self._pty = TTY_MAP[self._uart_num]
    if bbmux_controller.use_omapmux():
      self._bbmux_controller = bbmux_controller.BBmuxController()
      self.open()
    self._logger = logging.getLogger('bbuart')
    self._logger.debug('Initialized BBuart for interface %s with tty:%s',
                       interface, self._pty)
    # Beaglebone defaults to a baudrate of 9600, set it to what servo expects.
    self.set_uart_props(DEFAULT_UART_SETTINGS)

  def _open_pin(self, params, pattern, mode):
    """Selects a Uart signal (TX or RX) through the OMAP Muxes.

    Most of the uart signals are labelled properly in the mux files; however,
    uart 5 is not. Therefore any interfaces with specifically labelled
    transmit or receive signals can provide the mux file name and which select
    value to use via the params arg.

    Args:
      params: can be None. If not a list of muxfile name and and the select
              value to open this signal.
      pattern: if params is not supplied, the signal pattern to use to select
               this signal.
      mode: mode value to set the pull of the pin.
    """
    if params:
      self._bbmux_controller.set_muxfile(params[0], mode, params[1])
    else:
      # Have the bbmux controller determine the correct mux file and select
      # value.
      self._bbmux_controller.set_pin_mode(pattern % self._uart_num,
                                          mode)

  def open(self):
    """Opens access to beaglebone uart interface.

    Only necessary on Beaglebone kernel 3.2
    """
    self._open_pin(self._interface.get('txd', None), TXD_PATTERN, TXD_MODE)
    self._open_pin(self._interface.get('rxd', None), RXD_PATTERN, RXD_MODE)

  def close(self):
    """Closes connection to beaglebone uart interface.

    Raises:
      BBuartError: If close fails
    """
    pass

  def _get_value(self, output, regex):
    """Parses output supplied from stty to retrieve an Uart attribute.

    Args:
      output: output supplied from stty.
      regex: regex to retrieve a value from output. Note this regex requires
             a group named 'value'

    Raises:
      BBuartError: If regex is invalid or failed to retrieve 'value' from the
                   output.
    """
    if 'value' not in regex:
      # Invalid regex passed in.
      raise BBuartError('Improper regex passed in: %s.' % regex)
    value = re.search(regex, output)
    if not value:
      raise BBuartError('Failed to retrieve a value for %s with output: %s'
                        ' using regex: %s' % (self._pty, output, regex))
    return value.group('value')

  def _get_sbits(self, output):
    """Parses stty output to retrieve Uart sbits.

    Args:
      output: output supplied from stty.

    Returns:
      integer, number of stop bits. Can be 0|1|2 inclusive where:
          0: 1 stop bit
          2: 2 stop bits
    """
    # stty only returns 1 or 2 stop bits.
    value = self._get_value(output, SBITS_RE)
    if '-' in value:
      return 0
    else:
      return 2

  def _get_parity(self, output):
    """Parses stty output to retrieve Uart parity.

    Args:
      output: output supplied from stty.

    Returns:
      parity of 0-2 inclusive where:
          0: no parity
          1: odd parity
          2: even parity
    """
    if '-parenb' in output:
      # Parity is disabled.
      parity = 0
    else:
      par_mode = re.search(PARITY_RE, output)
      if par_mode.group(0) is '-parodd':
        parity = 2
      else:
        parity = 1
    return parity

  def get_uart_props(self):
    """Gets the uart's properties.

    Calls stty and parses it's output. Example (shortened) output:

    speed 115200 baud; rows 0; columns 0; line = 0;
    intr = ^C; quit = ^\; erase = ^?; kill = ^U; eof = ^D; eol = <undef>;
    -parenb -parodd cs8 hupcl -cstopb cread clocal -crtscts

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

    Raises:
      BBuartError: Unable to properly parse stty output.
    """
    self._logger.debug('Getting uart properties for interface: %s.',
                       self._interface)
    line_props = {}
    stty_args = ['stty', '-F', self._pty, '-a']
    self._logger.debug('Calling %s', ' '.join(stty_args))
    try:
      output = subprocess.check_output(stty_args)
    except subprocess.CalledProcessError as e:
      raise BBuartError('Failed to get uart properites for %s with error: %s.' %
                        (self._pty, e))

    line_props['baudrate'] = int(self._get_value(output, SPEED_RE), 0)
    line_props['parity'] = self._get_parity(output)
    line_props['bits'] = int(self._get_value(output, BITS_RE), 0)
    line_props['sbits'] = self._get_sbits(output)

    return line_props

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

    Raises:
      BBuartError: If failed to set line properties
    """
    self._logger.debug('Setting line props to: %s', line_props)
    self._uart_props_validation(line_props, exception_type=BBuartError)

    bits = 'cs%d' % line_props['bits']
    # According to the web, a UART set to 1 stop bit can receive 1.5 fine.
    sbits = SBITS_MAP[line_props['sbits']]
    parity = PARITY_MAP[line_props['parity']]

    stty_args = ['stty', '-F', self._pty, '%d' % line_props['baudrate'], bits,
                 sbits, parity]
    stty_args.extend(STTY_EXTRA_ARGS)
    try:
      subprocess.check_output(stty_args)
    except subprocess.CalledProcessError as e:
      raise BBuartError('Failed to set uart properites for %s with output: %s.'
                        ' Error: %s.'
                        % (self._pty, e.output, e))

  def get_pty(self):
    """Gets path to pty for communication to/from uart.

    Returns:
      String path to the pty connected to the uart
    """
    return self._pty
