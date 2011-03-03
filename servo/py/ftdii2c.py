# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Allows creation of i2c interface via libftdii2c (C) library for FTDI devices.
"""
import ctypes
import logging
import sys

import ftdi_common
import ftdi_utils


class Fi2cError(Exception):
  """Class for exceptions of Fi2c.
  """
  pass


class Fi2cContext(ctypes.Structure):
  """Defines primary context structure for libftdii2c.

  Declared in ftdii2c.h and named fi2c_context.
  """
  _fields_ = [("fc", ctypes.POINTER(ftdi_common.FtdiContext)),
              ("gpio", ftdi_common.Gpio),
              ("clk", ctypes.c_uint),
              ("error", ctypes.c_int),
              ("slv", ctypes.c_ubyte),
              ("buf", ctypes.POINTER(ctypes.c_ubyte)),
              ("bufcnt", ctypes.c_int),
              ("bufsize", ctypes.c_int)]


class Fi2c(object):
  """Provide interface to libftdii2c c-library via python ctypes module.
  """

  def __init__(self, vendor=ftdi_common.DEFAULT_VID,
               product=ftdi_common.DEFAULT_PID, interface=2):
    """Fi2c contructor.

    Loads libraries for libftdi, libftdii2c.  Creates instance objects
    (Structures), Fi2cContext, FtdiContext and Gpio to iteract with the library
    and intializes them.

    Args:
      vendor    : usb vendor id of FTDI device
      product   : usb product id of FTDI device
      interface : interface number ( 1 - 4 ) of FTDI device to use

    Raises:
      Fi2cError: An error accessing Fi2c object
    """
    self._logger = logging.getLogger("Fi2c")
    self._logger.debug("__init__")

    (self._flib, self._lib) = ftdi_utils.load_libs("ftdi", "ftdii2c")
    self._fargs = ftdi_common.FtdiCommonArgs(vendor_id=vendor,
                                             product_id=product,
                                             interface=interface)
    self._fc = ftdi_common.FtdiContext()
    self._fic = Fi2cContext()
    if self._flib.ftdi_init(ctypes.byref(self._fc)):
      raise Fi2cError("doing ftdi_init")
    if self._lib.fi2c_init(ctypes.byref(self._fic), ctypes.byref(self._fc)):
      raise Fi2cError("doing fi2c_init")

  def open(self):
    """Opens access to FTDI interface as a i2c (MPSSE mode) interface.
    """
    if self._lib.fi2c_open(ctypes.byref(self._fic), ctypes.byref(self._fargs)):
      raise Fi2cError("doing fi2c_open")

  def setclock(self, speed=100000):
    """Sets i2c clock speed.

    Args:
      speed : clock speed in hertz.  Default is 100kHz
    """
    if self._lib.fi2c_setclock(ctypes.byref(self._fic), speed):
      raise Fi2cError("doing fi2c_setclock")

  def wr_rd(self, slv, wlist, rcnt):
    """Write and/or read a slave i2c device.

    slv   : 7-bit address of the slave device
    wlist : list of bytes to write to the slave.  If list length is zero its
            just a read
    rcnt  : number of bytes to read from the device.  If zero, its just a write
    """
    self._fic.slv = slv
    wcnt = len(wlist)
    wbuf_type = ctypes.c_ubyte * wcnt
    wbuf = wbuf_type()
    for i in range(0, wcnt):
      wbuf[i] = wlist[i]

    rbuf_type = ctypes.c_ubyte * rcnt
    rbuf = rbuf_type()
    if self._lib.fi2c_wr_rd(ctypes.byref(self._fic), ctypes.byref(wbuf), wcnt,
                            ctypes.byref(rbuf), rcnt):
      raise Fi2cError("doing fi2c_wr_rd")
    cnt = 0
    for i in rbuf:
      self._logger.debug("rbuf[%i] = 0x%02x" % (cnt, i))
      cnt += 1
    return rbuf

  def close(self):
    """Close connection to FTDI device and cleanup
    """
    if self._lib.fi2c_close(ctypes.byref(self._fic)):
      raise Fi2cError("doing fi2c_close")


def test():
  """Test code.

  (TODO) tbroch: enhance and make Googley & pythonic from a unittest perspective
  """
  (options, args) = ftdi_utils.parse_common_args(interface=2)

  loglevel=logging.INFO
  if options.debug:
    loglevel = logging.DEBUG
  logging.basicConfig(level=loglevel,
                      format="%(asctime)s - %(name)s - " +
                      "%(levelname)s - %(message)s")
  fobj = Fi2c(options.vendor, options.product, options.interface)
  fobj.open()
  fobj.setclock(100000)

  wbuf = [0]
  slv = 0x21
  rbuf = fobj.wr_rd(slv, wbuf, 2)
  logging.info("001: i2c read of slv=0x%02x reg=0x%02x == 0x%02x%02x" %
               (slv, wbuf[0], rbuf[0], rbuf[1]))
  cnt = 1
  while cnt < 100:
    try:
      rbuf = fobj.wr_rd(slv, [], 2)
    except:
      pass
    cnt+=1
  logging.info("100: i2c read of slv=0x%02x reg=0x%02x == 0x%02x%02x" %
               (slv, wbuf[0], rbuf[0], rbuf[1]))
  fobj.close()

if __name__ == "__main__":
  test()
