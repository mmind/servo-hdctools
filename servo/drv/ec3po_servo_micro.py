# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for servo micro specific controls through ec3po.

Provides the following console controlled function subtypes:
  usbpd_console
"""

import logging

import pty_driver
import servo


# EC console mask for enabling only command channel
COMMAND_CHANNEL_MASK = 0x1


# Controls to set in batch operations.
# [off, samus, glados]
usbpd_uart_config = {
  "UART3_RX_JTAG_BUFFER_TO_SERVO_TDO": ("IN", "ALT", "ALT"),
  "UART3_TX_SERVO_JTAG_TCK": ("IN", "ALT", "ALT"),
  "SPI1_MUX_SEL": ("1", "0", "1"),
  "SPI1_BUF_EN_L": ("1", "0", "1"),
  "SPI1_VREF_18": ("0", "1", "0"),
  "SPI1_VREF_33": ("0", "0", "0"),
  "JTAG_BUFIN_EN_L": ("1", "1", "0"),
  "SERVO_JTAG_TDO_BUFFER_EN": ("0", "0", "1"),
  "SERVO_JTAG_TDO_SEL": ("0", "0", "1"),
}

class ec3poServoMicroError(Exception):
  """Exception class for ec."""


class ec3poServoMicro(pty_driver.ptyDriver):
  """Object to access drv=ec3po_servo_micro controls.

  Note, instances of this object get dispatched via base class,
  HwDriver's get/set method. That method ultimately calls:
    "_[GS]et_%s" % params['subtype'] below.

  For example, a control to read kbd_en would be dispatched to
  call _Get_kbd_en.
  """

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: ec3po interface object to handle low-level communication to
        control
      params: dictionary of params needed
    Raises:
      ec3poServoMicroError: on init failure
    """
    super(ec3poServoMicro, self).__init__(interface, params)

    if "console" in params:
      if params["console"] == "enhanced" and \
          type(interface) is servo.ec3po_interface.EC3PO:
        interface._console.oobm_queue.put('interrogate never enhanced')
      else:
        raise ec3poServoMicroError("Enhanced console must be ec3po!")

    self._logger.debug("")


  def batch_set(self, batch, index):
    """Set a batch of values on servo micro.

    Args:
      batch: dict of GPIO names, and on/off value
      index: index of batch preset
    """
    if index not in [0, 1, 2]:
      raise ec3poServoMicroError("Index (%s) must be 0, 1, or 2" % index)

    for name, values in batch.items():
      cmd = "gpioset %s %s\r" % (name, values[index])
      self._issue_cmd(cmd)


  def _Set_usbpd_console(self, value):
    """Set or unset PD console routing

    Args:
      value: An integer value, 0: none, 1:samus, 2:glados
    """
    self.batch_set(usbpd_uart_config, value)
