# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests usage of i2c interface for beaglebone devices."""
import mox
import unittest

import bbi2c


DEFAULT_BUS_NUM = 3
SLAVE_ADDRESS = 0x20
DATA_ADDRESS = 0x0

class TestBBi2c(mox.MoxTestBase):


  def setUp(self):
    super(TestBBi2c, self).setUp()
    bbi2c.subprocess = self.mox.CreateMockAnything()
    bbi2c.bbmux_controller = self.mox.CreateMockAnything()
    bbi2c.bbmux_controller.use_omapmux().AndReturn(True)

  def readTestHelper(self, data, send_address=True):
    if send_address:
      self.singleWriteTestHelper([DATA_ADDRESS])
    args = ['i2cget','-y', '3', '0x20']
    if len(data) == 2:
      args.append('0x%02x' % DATA_ADDRESS)
      args.append('w')
    result = '0x' + ''.join('%02x' % byte for byte in reversed(data))
    bbi2c.subprocess.check_output(args).AndReturn(result)

  def singleWriteTestHelper(self, data):
    args = ['i2cset', '-y', '3', '0x20', '0x%02x' % data[0]]
    if data[1:]:
      reversed_data = reversed(data[1:])
      args.append('0x' + ''.join('%02x' % wbyte for wbyte in reversed_data))
      if len(data[1:]) == 2:
        args.append('w')
    bbi2c.subprocess.check_call(args)

  def testSingleByteRead(self):
    data = [0x10]
    self.readTestHelper(data)
    self.mox.ReplayAll()
    self.bbi2c = bbi2c.BBi2c({'bus_num': 2})
    result = self.bbi2c.wr_rd(SLAVE_ADDRESS, [DATA_ADDRESS], len(data))
    self.assertEquals(result, data)

  def testMultiByteRead(self):
    data = [0x10, 0x01]
    self.readTestHelper(data)
    self.mox.ReplayAll()
    self.bbi2c = bbi2c.BBi2c({'bus_num': 2})
    result = self.bbi2c.wr_rd(SLAVE_ADDRESS, [DATA_ADDRESS], len(data))
    self.assertEquals(result, data)

  def testSingleByteWrite(self):
    data = [0x7]
    self.singleWriteTestHelper(data)
    self.mox.ReplayAll()
    self.bbi2c = bbi2c.BBi2c({'bus_num': 2})
    self.bbi2c.wr_rd(SLAVE_ADDRESS, data, 0)

  def testTwoByteWrite(self):
    data = [0x7, 0x8]
    self.singleWriteTestHelper(data)
    self.mox.ReplayAll()
    self.bbi2c = bbi2c.BBi2c({'bus_num': 2})
    self.bbi2c.wr_rd(SLAVE_ADDRESS, data, 0)

  def testThreeByteWrite(self):
    data = [0x7, 0x8, 0x9]
    self.singleWriteTestHelper(data)
    self.mox.ReplayAll()
    self.bbi2c = bbi2c.BBi2c({'bus_num': 2})
    self.bbi2c.wr_rd(SLAVE_ADDRESS, data, 0)

  def testBlockWriteFailure(self):
    data = [0x7, 0x8, 0x9, 0x10, 0x11, 0x12, 0x13]
    self.mox.ReplayAll()
    self.bbi2c = bbi2c.BBi2c({'bus_num': 2})
    with self.assertRaises(bbi2c.BBi2cError):
      self.bbi2c.wr_rd(SLAVE_ADDRESS, data, 0)

  def testWriteAndRead(self):
    wr_data = [DATA_ADDRESS, 0x8, 0x9]
    rd_data = [0x10, 0x01]
    self.singleWriteTestHelper(wr_data)
    self.readTestHelper(rd_data, send_address=False)
    self.mox.ReplayAll()
    self.bbi2c = bbi2c.BBi2c({'bus_num': 2})
    result = self.bbi2c.wr_rd(SLAVE_ADDRESS, wr_data, len(rd_data))
    self.assertEquals(result, rd_data)


if __name__ == '__main__':
    unittest.main()