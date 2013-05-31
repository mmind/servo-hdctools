# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests control of UART busses for beaglebone devices."""

import mox
import os
import subprocess
import unittest

import bbuart


SET_PROP_EXPECTED_ARGS = ['stty', '-F', '/dev/ttyO1', '115200', 'cs8',
                          '-cstopb','-parenb']
SET_PROP_EXPECTED_ARGS.extend(bbuart.STTY_EXTRA_ARGS)
TXD_MUXFILE = 'lcd_data8'
RXD_MUXFILE = 'lcd_data9'
MUX_SELVAL = 0x4

GET_PROPS_ARGS = ['stty', '-F', '/dev/ttyO1', '-a']
STTY_GET_ATTRIBUTES_OUTPUT = (
    'speed 115200 baud; rows 0; columns 0; line = 0;\n'
    'intr = ^C; quit = ^\; erase = ^?; kill = ^U; eof = ^D; eol = <undef>;'
    ' eol2 = <undef>; swtch = <undef>;\n'
    'start = ^Q; stop = ^S; susp = ^Z; rprnt = ^R; werase = ^W; lnext = ^V;'
    'flush = ^O; min = 1; time = 0;\n'
    '-parenb -parodd cs8 hupcl -cstopb cread clocal -crtscts\n'
    '-ignbrk -brkint -ignpar -parmrk -inpck -istrip -inlcr -igncr -icrnl -ixon'
    ' -ixoff -iuclc -ixany\n'
    '-imaxbel -iutf8\n'
    '-opost -olcuc -ocrnl onlcr -onocr -onlret -ofill -ofdel nl0 cr0 tab0 bs0'
    ' vt0 ff0\n'
    '-isig -icanon -iexten -echo -echoe -echok -echonl -noflsh -xcase -tostop'
    ' -echoprt -echoctl -echoke\n'
    )
GET_UART_PROPS_EXPECTED_RESULTS = {'parity': 0,
                                   'baudrate': 115200,
                                   'bits': 8,
                                   'sbits': 0}
BAD_UART_SETTINGS = {'baudrate': 115200,
                     'bits': 12,
                     'parity': 0,
                     'sbits': 0}



class TestBBuart(mox.MoxTestBase):


  def setUp(self):
    super(TestBBuart, self).setUp()
    bbuart.bbmux_controller = self.mox.CreateMockAnything()
    self._bbmux_controller = self.mox.CreateMockAnything()
    bbuart.bbmux_controller.BBmuxController().AndReturn(self._bbmux_controller)
    bbuart.subprocess = self.mox.CreateMockAnything()

  def _initializeBBuartDefault(self):
    """Helper to initalize BBuart with default options.

    I.E. the muxfile is not specified.
    """
    self._interface = {'name': 'bb_uart', 'uart_num': 1}
    self._bbmux_controller.set_pin_mode(
        bbuart.TXD_PATTERN % self._interface['uart_num'], bbuart.TXD_MODE)
    self._bbmux_controller.set_pin_mode(
        bbuart.RXD_PATTERN % self._interface['uart_num'], bbuart.RXD_MODE)
    bbuart.subprocess.check_output(SET_PROP_EXPECTED_ARGS)

  def _initializeBBuartWithParems(self):
    """Helper to initalize BBuart with specified parameters.

    I.E. the muxfile is not specified.
    """
    self._interface = {'name': 'bb_uart',
                       'uart_num': 1,
                       'txd': [TXD_MUXFILE, MUX_SELVAL],
                       'rxd': [RXD_MUXFILE, MUX_SELVAL]}
    self._bbmux_controller.set_muxfile(TXD_MUXFILE, bbuart.TXD_MODE,
                                       MUX_SELVAL)
    self._bbmux_controller.set_muxfile(RXD_MUXFILE, bbuart.RXD_MODE,
                                       MUX_SELVAL)
    bbuart.subprocess.check_output(SET_PROP_EXPECTED_ARGS)

  def testInitDefault(self):
    """Initialize and ensure that initializing with default args works."""
    self._initializeBBuartDefault()
    self.mox.ReplayAll()
    uart = bbuart.BBuart(self._interface)
    self.mox.VerifyAll()

  def testInitParems(self):
    """Initialize and ensure that initializing with parameters works."""
    self._initializeBBuartWithParems()
    self.mox.ReplayAll()
    uart = bbuart.BBuart(self._interface)
    self.mox.VerifyAll()

  def testGetUartProps(self):
    """Test get_uart_props."""
    self._initializeBBuartDefault()
    bbuart.subprocess.check_output(GET_PROPS_ARGS).AndReturn(
        STTY_GET_ATTRIBUTES_OUTPUT)
    self.mox.ReplayAll()
    uart = bbuart.BBuart(self._interface)
    self.assertEquals(GET_UART_PROPS_EXPECTED_RESULTS, uart.get_uart_props())

  def testGetUartPropsFailure(self):
    """Test get_uart_props failure case.

    This can occur when stty returns bad output.
    """
    self._initializeBBuartDefault()
    bbuart.subprocess.check_output(GET_PROPS_ARGS).AndReturn('')
    self.mox.ReplayAll()
    uart = bbuart.BBuart(self._interface)
    self.assertRaises(bbuart.BBuartError, uart.get_uart_props)

  def testSetUartPropsFailure(self):
    """Test when set_uart_props fails due to bad line_prop."""
    self._initializeBBuartDefault()
    self.mox.ReplayAll()
    uart = bbuart.BBuart(self._interface)
    self.assertRaises(bbuart.BBuartError, uart.set_uart_props,
                      BAD_UART_SETTINGS)

  def testGetValue(self):
    """Test the _get_value helper function."""
    self._initializeBBuartDefault()
    self.mox.ReplayAll()
    uart = bbuart.BBuart(self._interface)
    uart_speed = uart._get_value(STTY_GET_ATTRIBUTES_OUTPUT, bbuart.SPEED_RE)
    self.assertEquals(int(uart_speed, 0), 115200)

  def testGetValueFailByBadOutput(self):
    """Test the _get_value helper function.

    Fail due to bad output.
    """
    self._initializeBBuartDefault()
    self.mox.ReplayAll()
    uart = bbuart.BBuart(self._interface)
    self.assertRaises(bbuart.BBuartError, uart._get_value, '', bbuart.SPEED_RE)

  def testGetValueFailByBadRegex(self):
    """Test the _get_value helper function.

    Fail due to bad regex.
    """
    self._initializeBBuartDefault()
    self.mox.ReplayAll()
    uart = bbuart.BBuart(self._interface)
    self.assertRaises(bbuart.BBuartError, uart._get_value,
                      STTY_GET_ATTRIBUTES_OUTPUT, 'bad_regex')

  def testGetParity(self):
    """Test the _get_parity helper function."""
    self._initializeBBuartDefault()
    self.mox.ReplayAll()
    uart = bbuart.BBuart(self._interface)
    # Test no parity.
    self.assertEquals(0, uart._get_parity('speed 115200 baud; -parenb'))
    # Test odd parity.
    self.assertEquals(1, uart._get_parity('speed 115200 baud; parodd'))
    # Test even parity.
    self.assertEquals(1, uart._get_parity('speed 115200 baud; -parodd'))

if __name__ == '__main__':
    unittest.main()
