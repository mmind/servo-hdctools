# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests control of OMAP Muxes for beaglebone devices."""

import __builtin__
import mox
import os
import unittest

import bbmux_controller


FAKE_MUX_FILE = 'mux_file'
FAKE_MUX_FILE_PATH = '/sys/kernel/debug/omap_mux/mux_file'
FAKE_MUX_FILE_CONTENTS = ('signals: gpmc_a9 | mii2_rxd2 | rgmii2_rd2 | '
                          'mmc2_dat7 | NA | NA | mcasp0_fsx | gpio1_25')
MUX_MODE = '0x37'
EXPECTED_PIN_NAME_MAP = {'signals:'   : 'mux_file',
                         'gpmc_a9'    : 'mux_file',
                         'mii2_rxd2'  : 'mux_file',
                         'rgmii2_rd2' : 'mux_file',
                         'mmc2_dat7'  : 'mux_file',
                         'NA'         : 'mux_file',
                         'mcasp0_fsx' : 'mux_file',
                         'gpio1_25'   : 'mux_file'}

EXPECTED_PIN_MODE_MAP = {'signals:'   : -1,
                         'gpmc_a9'    : 0,
                         'mii2_rxd2'  : 1,
                         'rgmii2_rd2' : 2,
                         'mmc2_dat7'  : 3,
                         'NA'         : 5,
                         'mcasp0_fsx' : 6,
                         'gpio1_25'   : 7}


class TestBBmuxController(mox.MoxTestBase):


  def setUp(self):
    super(TestBBmuxController, self).setUp()
    self.mox.StubOutWithMock(__builtin__, 'open')

  def testInitialization(self):
    bbmux_controller.os = self.mox.CreateMockAnything()
    bbmux_controller.os.path = self.mox.CreateMockAnything()
    bbmux_controller.os.listdir(bbmux_controller.MUX_ROOT).AndReturn(
        [FAKE_MUX_FILE])
    bbmux_controller.os.path.join(bbmux_controller.MUX_ROOT,
                                  FAKE_MUX_FILE).MultipleTimes().AndReturn(
                                  FAKE_MUX_FILE_PATH)
    bbmux_controller.os.path.isdir(mox.IgnoreArg()).MultipleTimes().AndReturn(
        False)
    mux_file = self.mox.CreateMockAnything()
    mux_file.__enter__().AndReturn([FAKE_MUX_FILE_CONTENTS])
    mux_file.__exit__(mox.IgnoreArg(), mox.IgnoreArg(), mox.IgnoreArg())
    open(FAKE_MUX_FILE_PATH, 'r').AndReturn(mux_file)
    self.mox.ReplayAll()
    mux_controller = bbmux_controller.BBmuxController()
    self.assertEquals(EXPECTED_PIN_NAME_MAP, mux_controller._pin_name_map)
    self.assertEquals(EXPECTED_PIN_MODE_MAP, mux_controller._pin_mode_map)

  def _writeToMuxFileHelper(self):
    mux_file = self.mox.CreateMockAnything()
    open(FAKE_MUX_FILE_PATH, 'w').AndReturn(mux_file)
    mux_file.__enter__().AndReturn(mux_file)
    mux_file.write(MUX_MODE)
    mux_file.__exit__(mox.IgnoreArg(), mox.IgnoreArg(), mox.IgnoreArg())

  def testSetPinMode(self):
    """Test Selecting and setting a pin."""
    self._writeToMuxFileHelper()
    self.mox.ReplayAll()
    # Since testInitialization ran first, BBmuxController should not initialize
    # its pin maps as they are class variables.
    mux_controller = bbmux_controller.BBmuxController()
    mux_controller.set_pin_mode('gpio1_25', 0x3)

  def testSetMuxFile(self):
    """Test Selecting and setting a pin."""
    self._writeToMuxFileHelper()
    self.mox.ReplayAll()
    # Since testInitialization ran first, BBmuxController should not initialize
    # its pin maps as they are class variables.
    mux_controller = bbmux_controller.BBmuxController()
    mux_controller.set_muxfile(FAKE_MUX_FILE, 0x3, 0x7)

if __name__ == '__main__':
    unittest.main()