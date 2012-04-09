# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Allows creation of gpio interface via libftdigpio c library for FTDI
devices."""
import logging
import ctypes

import ftdi_utils
import ftdi_common


class FgpioError(Exception):
  """Class for exceptions of Fgpio."""
  def __init__(self, msg, value=0):
    """FgpioError constructor.

    Args:
      msg: string, message describing error in detail
      value: integer, value of error when non-zero status returned.  Default=0
    """
    super(FgpioError, self).__init__(msg, value)
    self.msg = msg
    self.value = value


class FgpioContext(ctypes.Structure):
  """Defines primary context structure for libftdigpio.

  Declared in ftdigpio.h and named fgpio_context.
  """
  _fields_ = [("fc", ctypes.POINTER(ftdi_common.FtdiContext)),
              ("gpio", ftdi_common.Gpio)]


class Fgpio(object):
  """Provide interface to libftdigpio c-library via python ctypes module."""
  def __init__(self, vendor=ftdi_common.DEFAULT_VID,
               product=ftdi_common.DEFAULT_PID, interface=4, serialname=None):
    """Fgpio constructor.

    Loads libraries for libftdi, libftdigpio.  Creates instance objects
    (Structures), FgpioContext, FtdiContext and Gpio to iteract with the library
    and intializes them.

    Args:
      vendor    : usb vendor id of FTDI device
      product   : usb product id of FTDI device
      interface : interface number ( 1 - 4 ) of FTDI device to use
      serialname: string of device serialname/number as defined in FTDI eeprom.

    Raises:
      FgpioError: An error accessing Fgpio object
    """
    self._logger = logging.getLogger("Fgpio")
    self._logger.debug("")

    (self._flib, self._lib) = ftdi_utils.load_libs("ftdi", "ftdigpio")
    self._fargs = ftdi_common.FtdiCommonArgs(vendor_id=vendor,
                                             product_id=product,
                                             interface=interface,
                                             serialname=serialname)
    self._is_closed = True
    self._gpio = ftdi_common.Gpio()
    self._fc = ftdi_common.FtdiContext()
    self._fgc = FgpioContext()
    # initialize
    if self._flib.ftdi_init(ctypes.byref(self._fc)):
      raise FgpioError("doing ftdi_init")
    if self._lib.fgpio_init(ctypes.byref(self._fgc), ctypes.byref(self._fc)):
      raise FgpioError("doing fgpio_init")

  def __del__(self):
    """Fgpio destructor."""
    self._logger.debug("")
    if not self._is_closed:
      self.close()

  def open(self):
    """Opens access to FTDI interface as a GPIO (bitbang).

    Raises:
      FgpioError: If open fails
    """
    err = self._lib.fgpio_open(ctypes.byref(self._fgc),
                               ctypes.byref(self._fargs))
    if err:
      raise FgpioError("doing fgpio_open", err)
    self._is_closed = False

  def close(self):
    """Close access to FTDI interface as a GPIO (bitbang).

    Raises:
      FgpioError: If close fails
    """
    err = self._lib.fgpio_close(ctypes.byref(self._fgc))
    if err:
      raise FgpioError("doing fgpio_close", err)
    self._is_closed = True

  def wr_rd(self, offset, width, dir_val=None, wr_val=None):
    """Write and/or read GPIO bit.

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
    """
    rd_val = ctypes.c_ubyte()
    self._gpio.mask = (pow(2, width) - 1) << offset
    if wr_val is not None and dir_val is not None:
      self._gpio.direction = self._gpio.mask
      self._gpio.value = wr_val << offset
      self._lib.fgpio_wr_rd(ctypes.byref(self._fgc), ctypes.byref(self._gpio),
                            ctypes.byref(rd_val),
                            ftdi_common.INTERFACE_TYPE_GPIO)
    else:
      self._lib.fgpio_wr_rd(ctypes.byref(self._fgc), 0, ctypes.byref(rd_val),
                            ftdi_common.INTERFACE_TYPE_GPIO)
    self._logger.debug("dir:%s val:%s returned %d" %
                       (str(dir_val), str(wr_val), rd_val.value))
    return (rd_val.value & self._gpio.mask) >> offset


def test():
  """Test code.

  (TODO) tbroch: enhance and make Googley & pythonic from a unittest
  perspective.
  """
  (options, args) = ftdi_utils.parse_common_args()
  loglevel=logging.INFO
  if options.debug:
    loglevel = logging.DEBUG
  logging.basicConfig(level=loglevel,
                      format="%(asctime)s - %(name)s - " +
                      "%(levelname)s - %(message)s")
  for i in range(1, 5):
    fobj = Fgpio(options.vendor, options.product, i)
    fobj.open()
    rd_val = fobj.wr_rd(6,1,0)
    logging.debug("rd_val = %d after <6> -> 0" % (rd_val))
    if rd_val != 0:
      logging.error("rd_val = %d != 0" % (rd_val))

    rd_val = fobj.wr_rd(6,1,1)
    logging.debug("rd_val = %d after <6> -> 1" % (rd_val))
    if rd_val != 1:
      logging.error("rd_val = %d != 1" % (rd_val))

    rd_val = fobj.wr_rd(6,1,0)
    logging.debug("rd_val = %d after <6> -> 0" % (rd_val))
    if rd_val != 0:
      logging.error("rd_val = %d != 0" % (rd_val))

    # release as output
    rd_val = fobj.wr_rd(6,0,0)
    logging.debug("rd_val = %d after <6> dir released" % (rd_val))
    logging.info("rd_val = %d should match pu/pd" % (rd_val))
    fobj.close()

if __name__ == "__main__":
  test()
