# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests usage of gpio interface for beaglebone devices."""

import mox
import os
import shutil
import tempfile
import unittest

import bbgpio


GPIO_ROOT = 'sys/class/gpio'
GPIO_FILE_PATH = 'sys/class/gpio/gpio57'
GPIO_VALUE_FILE_PATH = 'sys/class/gpio/gpio57/value'
GPIO_DIRECTION_FILE_PATH = 'sys/class/gpio/gpio57/direction'
OFFSET = 25
CHIP = '1'
WIDTH = 1

class TestBBgpio(mox.MoxTestBase):


  def setUp(self):
    super(TestBBgpio, self).setUp()
    self._tempfolder = tempfile.mkdtemp()
    # Redirect all the bbgpio os interactions to the tempfolder.
    bbgpio.GPIO_ROOT = os.path.join(self._tempfolder, GPIO_ROOT)
    bbgpio.EXPORT_FILE =  os.path.join(bbgpio.GPIO_ROOT, 'export')
    bbgpio.UNEXPORT_FILE = os.path.join(bbgpio.GPIO_ROOT, 'unexport')
    bbgpio.GPIO_PIN_PATTERN = os.path.join(bbgpio.GPIO_ROOT, 'gpio%d')
    # Create the fake directory structure.
    os.makedirs(bbgpio.GPIO_ROOT)
    self._gpio_folder = os.path.join(self._tempfolder, GPIO_FILE_PATH)
    os.mkdir(self._gpio_folder)
    # Create direction/value files.
    self._direction_file = os.path.join(self._tempfolder,
                                        GPIO_DIRECTION_FILE_PATH)
    open(self._direction_file, 'a').close()
    self._value_file = os.path.join(self._tempfolder,
                                    GPIO_VALUE_FILE_PATH)
    open(self._value_file, 'a').close()

  def tearDown(self):
    # Cleanup the fake directory structure.
    shutil.rmtree(self._tempfolder)

  def _mock_mux(self):
    """Mock the mux settings."""
    bbmux_controller = self.mox.CreateMockAnything()
    bbgpio.bbmux_controller = bbmux_controller
    bbgpio.bbmux_controller.use_omapmux().AndReturn(True)
    bbmux_controller.BBmuxController().AndReturn(bbmux_controller)
    bbgpio.bbmux_controller.set_pin_mode(mox.IgnoreArg(), mox.IgnoreArg())

  def testRead(self):
    self._mock_mux()
    self.mox.ReplayAll()
    gpio_controller = bbgpio.BBgpio()
    with open(self._value_file, 'w') as f:
      f.write('1')
    rd_value = gpio_controller.wr_rd(OFFSET, WIDTH, dir_val=0, chip=CHIP)
    self.assertEquals(rd_value, 1)
    with open(self._direction_file, 'r') as f:
      direction = f.read()
    self.assertEquals(direction, 'in')

  def testWrite(self):
    self._mock_mux()
    self.mox.ReplayAll()
    gpio_controller = bbgpio.BBgpio()
    gpio_controller.wr_rd(OFFSET, WIDTH, dir_val=1, wr_val=0, chip=CHIP)
    with open(self._direction_file, 'r') as f:
      direction = f.read()
    self.assertEquals(direction, 'out')
    with open(self._value_file, 'r') as f:
      value = f.read()
    self.assertEquals(value, '0')


if __name__ == '__main__':
    unittest.main()