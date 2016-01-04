# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Allows creation of gpio interface via stm32 usb."""

import array
import logging
import struct
import usb

import gpio_interface
import stm32usb


class SgpioError(Exception):
  """Class for exceptions of Sgpio."""
  def __init__(self, msg, value=0):
    """SgpioError constructor.

    Args:
      msg: string, message describing error in detail
      value: integer, value of error when non-zero status returned.  Default=0
    """
    super(SgpioError, self).__init__(msg, value)
    self.msg = msg
    self.value = value


class Sgpio(gpio_interface.GpioInterface):
  """Provide interface to stm32 gpio USB endpoint.

  Instance Variables:
  _logger: Sgpio tagged log output
  _susb: stm32 usb object
  """

  def __init__(self, vendor=0x18d1,
               product=0x500f, interface=1, serialname=None):
    """Sgpio constructor.

    Loads libraries for libusb.  Creates instance objects
    and Gpio to iteract with the library and intializes them.

    Args:
      vendor    : usb vendor id of stm32 device
      product   : usb product id of stm32 device
      interface : interface number ( 1 - 4 ) of stm32 device to use
      serialname: string of device serialname/number TODO: is this a thing?

    Raises:
      SgpioError: An error accessing Sgpio object
    """
    self._logger = logging.getLogger("Sgpio")
    self._logger.debug("")

    self._susb = stm32usb.Susb(vendor=vendor, product=product,
        interface=interface, serialname=serialname, logger=self._logger)

    self._logger.debug("Set up stm32 gpio")

  def __del__(self):
    """Sgpio destructor."""
    self._logger.debug("Close")

  def wr_rd(self, offset, width=1, dir_val=None, wr_val=None, chip=None,
            muxfile=None):
    """Write and/or read GPIO bit.

    Args:
      offset  : bit offset of the gpio to read or write
      width   : integer, number of contiguous bits in gpio to read or write
      dir_val : Not used. defaulted to None.
      wr_val  : value to write to the GPIO. If unset, skips the write.
      chip    : Not used. defaulted to None.
      muxfile : Not used. defaulted to None.

    Returns:
      integer value from reading the gpio value ( masked & aligned )
    """
    self._logger.debug("Sgpio.wr_rd(offset="
        "%s, width=%s, dir_val=%s, wr_val=%s)" % (
        offset, width, dir_val, wr_val))
    # Read preexisting values for debug output.
    ret = self._susb._read_ep.read(4, self._susb.TIMEOUT_MS)
    read_mask = struct.unpack("<I", ret)[0]
    self._logger.debug("Read mask: 0x%08x" % read_mask)

    width_mask = (1 << width) - 1
    set_mask = 0
    clear_mask = 0

    if wr_val != None:
      set_mask = (wr_val & width_mask) << offset;
      clear_mask = (~wr_val & width_mask) << offset;

    byte_str = struct.pack("<II", set_mask, clear_mask)
    ret = self._susb._write_ep.write(byte_str, self._susb.TIMEOUT_MS)
    if (ret != len(byte_str)):
      raise SgpioError("Wrote %d bytes, expected %d" % (ret, len(byte_str)))

    # GPIO cached values update on read,
    ret = self._susb._read_ep.read(4, self._susb.TIMEOUT_MS)
    ret = self._susb._read_ep.read(4, self._susb.TIMEOUT_MS)
    if len(ret) != 4:
      raise SgpioError(
          "Read error: expected 4 bytes, got %d [%s]" % (len(ret), ret))

    read_mask = struct.unpack("<I", ret)[0]
    self._logger.debug("Read mask: 0x%08x" % read_mask)

    readvalue = (read_mask >> offset) & width_mask
    self._logger.debug("Read value: 0x%x" % readvalue)
    return readvalue


def test():
  """Test code.
  """
  loglevel = logging.DEBUG
  logging.basicConfig(level=loglevel,
                      format="%(asctime)s - %(name)s - " +
                      "%(levelname)s - %(message)s")

  logging.debug("Starting")
  sobj = Sgpio()
  for i in range(1, 2):
    rd_val = sobj.wr_rd(2,wr_val=0)
    logging.debug("rd_val = %d after <2> -> 0" % (rd_val))
    if rd_val != 0:
      logging.error("rd_val = %d != 0" % (rd_val))

    rd_val = sobj.wr_rd(2,wr_val=1)
    logging.debug("rd_val = %d after <2> -> 1" % (rd_val))
    if rd_val != 1:
      logging.error("rd_val = %d != 1" % (rd_val))

    rd_val = sobj.wr_rd(2,1,wr_val=0)
    logging.debug("rd_val = %d after <2> -> 0" % (rd_val))
    if rd_val != 0:
      logging.error("rd_val = %d != 0" % (rd_val))

    # release as output
    rd_val = sobj.wr_rd(2)
    logging.debug("rd_val = %d after <2> dir released" % (rd_val))
    logging.info("rd_val = %d should match pu/pd" % (rd_val))
  logging.debug("Finished")

if __name__ == "__main__":
  test()
