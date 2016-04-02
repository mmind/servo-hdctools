# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Allows creation of an interface via stm32 usb."""

import logging
import usb


class SusbError(Exception):
  """Class for exceptions of Susb."""
  def __init__(self, msg, value=0):
    """SusbError constructor.

    Args:
      msg: string, message describing error in detail
      value: integer, value of error when non-zero status returned.  Default=0
    """
    super(SusbError, self).__init__(msg, value)
    self.msg = msg
    self.value = value


class Susb():
  """Provide stm32 USB functionality.

  Instance Variables:
  _logger: S.* tagged log output
  _dev: pyUSB device object
  _read_ep: pyUSB read endpoint for this interface
  _write_ep: pyUSB write endpoint for this interface
  """
  READ_ENDPOINT = 0x81
  WRITE_ENDPOINT = 0x1
  TIMEOUT_MS = 100

  def __init__(self, vendor=0x18d1,
               product=0x500f, interface=1, serialname=None, logger=None):
    """Susb constructor.

    Disconvers and connects to stm32 USB endpoints.

    Args:
      vendor    : usb vendor id of stm32 device
      product   : usb product id of stm32 device
      interface : interface number ( 1 - 4 ) of stm32 device to use
      serialname: string of device serialname. TODO(nsanders): implement this.

    Raises:
      SusbError: An error accessing Susb object
    """
    if not logger:
      raise SusbError("No logger defined")
    self._logger = logger
    self._logger.debug("")

    # Find the stm32.
    dev = usb.core.find(idVendor=vendor, idProduct=product)
    if dev is None:
      raise SusbError("USB device not found")

    self._logger.debug("Found stm32: %04x:%04x" % (vendor, product))
    dev.set_configuration()

    # Get an endpoint instance.
    cfg = dev.get_active_configuration()
    intf = usb.util.find_descriptor(cfg, bInterfaceNumber=interface)
    self._intf = intf

    # Detatch raiden.ko if it is loaded.
    if dev.is_kernel_driver_active(intf.bInterfaceNumber) is True:
            dev.detach_kernel_driver(intf.bInterfaceNumber)
    self._logger.debug("InterfaceNumber: %s" % intf.bInterfaceNumber)

    read_ep_number = intf.bInterfaceNumber + self.READ_ENDPOINT
    read_ep = usb.util.find_descriptor(intf, bEndpointAddress=read_ep_number)
    self._read_ep = read_ep
    self._logger.debug("Reader endpoint: 0x%x" % read_ep.bEndpointAddress)

    write_ep_number = intf.bInterfaceNumber + self.WRITE_ENDPOINT
    write_ep = usb.util.find_descriptor(intf, bEndpointAddress=write_ep_number)
    self._write_ep = write_ep
    self._logger.debug("Writer endpoint: 0x%x" % write_ep.bEndpointAddress)

    self._logger.debug("Set up stm32 usb")

  def __del__(self):
    """Sgpio destructor."""
    self._logger.debug("Close")
