# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for gpio controls through ec3po.

Provides the following console controlled function:
  _Get_single, _Set_single, _Get_multi, _Set_multi
"""

import logging

import pty_driver
import servo


# EC console mask for enabling only command channel
COMMAND_CHANNEL_MASK = 0x1

# servod numeric translation for GPIO state.
GPIO_STATE = {
  0: '0',
  1: '1',
  2: 'IN',
  3: 'A',
  4: 'ALT'
}


class ec3poGpioError(Exception):
  """Exception class for ec."""


class ec3poGpio(pty_driver.ptyDriver):
  """Object to access drv=ec3po_gpio controls.

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
      params: dictionary of params needed to perform operations on
        devices. Must contain name:"GPIO_NAME" or names:"GPIO_b0,GPIO_b1"
        Must contain subtype=single or multi.
    Raises:
      ec3poGpioError: on init failure
    """
    super(ec3poGpio, self).__init__(interface, params)

    if "name" in params:
      self._gpio_name = params["name"]
    elif "names" in params:
      self._gpio_names = []
      for name in params["names"].split(','):
        self._gpio_names.insert(0, name.strip())
    else:
      raise ec3poGpioError("No GPIO name specified")

    if "console" in params:
      if params["console"] == "enhanced" and \
          type(interface) is servo.ec3po_interface.EC3PO:
        interface._console.oobm_queue.put('interrogate never enhanced')
      else:
        raise ec3poGpioError("Enhanced console must be ec3po!")

    self._logger.debug("")

  def set_gpio(self, name, value):
    """Set the named GPIO to the specified value.

    Uses the console gpioset command.

    Args:
      name: name of the GPIO to modify
      value: the state to set into the GPIO
    """
    cmd = "gpioset %s %s\r" % (name, GPIO_STATE[value])
    self._issue_cmd(cmd)

  def get_gpio(self, name):
    """Get gpio logical value.

    Args:
      name: name of the GPIO to query
    Returns:
      0 or 1
    """
    cmd = "gpioget %s\r" % name
    regex = "  ([01])[ *] .*%s" % name

    results = self._issue_cmd_get_results(cmd, [regex])[0]
    res_value = int(results[1])
    return res_value

  def _Set_single(self, value):
    """Set GPIO through gpioset console command.

    Args:
      value: the state to set into the GPIO
    """
    self.set_gpio(self._gpio_name, value)

  def _Get_single(self):
    """Get gpio logical value.

    Returns:
      0 or 1
    """
    value = self.get_gpio(self._gpio_name)
    return value

  def _Set_multi(self, value):
    """Set several GPIOs according to a mask

    Assigns the GPIOs specified in "names" to the bit values
    specified in value.

    Args:
      value: An integer value, where each bit will be assigned to a GPIO.
    """
    if value >> len(self._gpio_names):
      raise ec3poGpioError("Extra bits left over in v:%d on %s" % (
          value, self._gpio_names))
    offset = len(self._gpio_names) - 1
    for gpio in self._gpio_names:
      bit = (value >> offset) & 0x1
      self.set_gpio(gpio, bit)
      offset -= 1

  def _Get_multi(self):
    """Get each listed gpio and provide a bit array of values.

    Returns:
      an integer with each bit set according to the state of its GPIO.
    """
    value = 0
    for gpio in self._gpio_names:
      bit = self.get_gpio(gpio)
      value = value << 1
      value = value | (bit & 0x1)
    return value
