# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Allows creation of i2c interface via libftdii2c (C) library for FTDI devices.
"""
import ctypes
import logging

import ftdi_common
import ftdi_utils


class Fi2cError(Exception):
  """Class for exceptions of Fi2c."""
  def __init__(self, msg, value=0):
    """Fi2cError constructor.

    Args:
      msg: string, message describing error in detail
      value: integer, value of error when non-zero status returned.  Default=0
    """
    super(Fi2cError, self).__init__(msg, value)
    self.msg = msg
    self.value = value


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
               product=ftdi_common.DEFAULT_PID, interface=2, serialname=None):
    """Fi2c constructor.

    Loads libraries for libftdi, libftdii2c.  Creates instance objects
    (Structures), Fi2cContext, FtdiContext and Gpio to iteract with the library
    and intializes them.

    Args:
      vendor: usb vendor id of FTDI device
      product: usb product id of FTDI device
      interface: interface number of FTDI device to use
      serialname: string of device serialname/number as defined in FTDI eeprom.

    Raises:
      Fi2cError: If either ftdi or fi2c inits fail
    """
    self._logger = logging.getLogger("Fi2c")
    self._logger.debug("")

    (self._flib, self._lib, self._gpiolib) = \
        ftdi_utils.load_libs("ftdi", "ftdii2c",  "ftdigpio")
    self._fargs = ftdi_common.FtdiCommonArgs(vendor_id=vendor,
                                             product_id=product,
                                             interface=interface,
                                             serialname=serialname)
    self._fc = ftdi_common.FtdiContext()
    self._fic = Fi2cContext()
    self._gpio = ftdi_common.Gpio()
    self._is_closed = True
    err = self._flib.ftdi_init(ctypes.byref(self._fc))
    if err:
      raise Fi2cError("ftdi_init", err)

    err = self._lib.fi2c_init(ctypes.byref(self._fic), ctypes.byref(self._fc))
    if err:
      raise Fi2cError("fi2c_init", err)

    self._i2c_mask = ~self._fic.gpio.mask

  def __del__(self):
    """Fi2c destructor.

    Calls close to release device
    """
    if not self._is_closed:
      self.close()

  def open(self):
    """Opens access to FTDI interface as a i2c (MPSSE mode) interface.

    Raises:
      Fi2cError: If open fails
    """
    err = self._lib.fi2c_open(ctypes.byref(self._fic),
                                ctypes.byref(self._fargs))
    if err:
      raise Fi2cError("fi2c_open", err)
    self._is_closed = False

  def close(self):
    """Close connection to FTDI device and cleanup.

    Raises:
      Fi2cError: If close fails
    """
    err = self._lib.fi2c_close(ctypes.byref(self._fic))
    if err:
      raise Fi2cError("fi2c_close", err)
    self._is_closed = True

  def setclock(self, speed=100000):
    """Sets i2c clock speed.

    Args:
      speed: clock speed in hertz.  Default is 100kHz
    """
    if self._lib.fi2c_setclock(ctypes.byref(self._fic), speed):
      raise Fi2cError("fi2c_setclock")

  def wr_rd(self, slv, wlist, rcnt):
    """Write and/or read a slave i2c device.

    Args:
      slv: 7-bit address of the slave device
      wlist: list of bytes to write to the slave.  If list length is zero its
          just a read
      rcnt: number of bytes to read from the device.  If zero, its just a write

    Returns:
      list of c_ubyte's read from i2c device.
    """
    self._logger.debug("")
    self._fic.slv = slv
    wcnt = len(wlist)
    wbuf_type = ctypes.c_ubyte * wcnt
    wbuf = wbuf_type()
    for i in xrange(wcnt):
      wbuf[i] = wlist[i]

    rbuf_type = ctypes.c_ubyte * rcnt
    rbuf = rbuf_type()
    for i, wval in enumerate(wbuf):
      self._logger.debug("wbuf[%i] = 0x%02x" % (i, wval))

    err = self._lib.fi2c_wr_rd(ctypes.byref(self._fic), ctypes.byref(wbuf),
                               wcnt, ctypes.byref(rbuf), rcnt)
    if err:
      raise Fi2cError("fi2c_wr_rd", err)

    for i, rval in enumerate(rbuf):
      self._logger.debug("rbuf[%i] = 0x%02x" % (i, rval))
    return list(rbuf)

  def gpio_wr_rd(self, offset, width, dir_val=None, wr_val=None):
    """Write and/or read GPIO controls

    I2C interface on FTDI's MPSSE engine requires 3 bits.  One for SCL and two
    for SDA ( bi-directional ).  The remaining 5 bits of the byte interface can
    be used as spare GPIO's providing the interface is left in the native (I2C)
    mode.  This routine facilitates those GPIO's by calling the same GPIO
    library as a native GPIO interface but with the interface type set to
    'INTERFACE_TYPE_I2C'.

    Args:
      offset  : bit offset of the gpio to read or write
      width   : integer, number of contiguous bits in gpio to read or write
      dir_val : direction value of the gpio.  dir_val is interpretted as:
                  None : read the pins via libftdi's ftdi_read_pins
                  0    : configure as input
                  1    : configure as output
      wr_val  : value to write to the GPIO.  Note wr_val is irrelevant if
                dir_val = 0

    Returns:
      integer value from reading the gpio value ( masked & aligned )

    Raises:
      Fi2cError: if gpio's mask would interfere with i2c's bits
    """
    rd_val = ctypes.c_ubyte()
    self._gpio.mask = (pow(2, width) - 1) << offset
    if self._gpio.mask & self._i2c_mask:
      raise Fi2cError("gpio mask violates i2c mask")
    if wr_val is not None and dir_val is not None:
      self._gpio.direction = self._gpio.mask
      self._gpio.value = wr_val << offset
      self._gpiolib.fgpio_wr_rd(ctypes.byref(self._fic),
                                ctypes.byref(self._gpio),
                                ctypes.byref(rd_val),
                                ftdi_common.INTERFACE_TYPE_I2C)
    else:
      self._gpiolib.fgpio_wr_rd(ctypes.byref(self._fic), 0,
                                ctypes.byref(rd_val),
                                ftdi_common.INTERFACE_TYPE_I2C)
    self._logger.debug("mask:0x%x val:%s returned %d" %
                       (self._gpio.mask, str(wr_val), rd_val.value))
    return (rd_val.value & self._gpio.mask) >> offset


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
  rbuf = fobj.wr_rd(slv, wbuf, 1)
  logging.info("first: i2c read of slv=0x%02x reg=0x%02x == 0x%02x" %
               (slv, wbuf[0], rbuf[0]))
  errcnt = 0
  for cnt in xrange(1000):
    try:
      rbuf = fobj.wr_rd(slv, [], 1)
    except:
      errcnt += 1
      logging.error("errs = %d cnt = %d" % (errcnt, cnt))

  logging.info("last: i2c read of slv=0x%02x reg=0x%02x == 0x%02x" %
               (slv, wbuf[0], rbuf[0]))
  fobj.close()

if __name__ == "__main__":
  test()
