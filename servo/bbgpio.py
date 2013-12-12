# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import atexit
import logging
import os

import bbmux_controller
import gpio_interface


GPIO_ROOT = '/sys/class/gpio'
EXPORT_FILE =  os.path.join(GPIO_ROOT, 'export')
UNEXPORT_FILE = os.path.join(GPIO_ROOT, 'unexport')
GPIO_PIN_PATTERN = os.path.join(GPIO_ROOT, 'gpio%d')
GPIO_MODE_VALUE = 0x3
GPIO_SELECT_VALUE = 7
DIR_IN = 0
DIR_OUT = 1
DIR_VAL_MAP = {DIR_IN  : 'in',
               DIR_OUT : 'out'}


class BBgpioError(Exception):
  """Class for exceptions of Bgpio."""
  def __init__(self, msg, value=0):
    """BBgpioError constructor.

    Args:
      msg: string, message describing error in detail
      value: integer, value of error when non-zero status returned.  Default=0
    """
    super(BBgpioError, self).__init__(msg, value)
    self.msg = msg
    self.value = value

class BBgpio(gpio_interface.GpioInterface):
  """Provides interface to a beaglebone's GPIO.

  Instance Variables:
    _exported_gpios : list of gpios exported on the gpio. At exit time they
                      will all be unexported.
    _bbmux_controller : controller to select and setup signals on the
                        beaglebone's pins.
  """

  def __init__(self):
    self._logger = logging.getLogger('BBGpio')
    self._logger.debug('')
    self._exported_gpios = []
    self._bbmux_controller = None
    if bbmux_controller.use_omapmux():
      self._bbmux_controller = bbmux_controller.BBmuxController()
    # Ensure we release the system resources at exit time.
    atexit.register(self.close)

  def open(self):
    """Opens access to Beaglebone interface as a GPIO (bitbang).

    Raises:
      BBgpioError: If open fails
    """
    pass

  def close(self):
    """Close access to beaglebone interface as a GPIO (bitbang).

    Raises:
      BBgpioError: If close fails
    """
    for opened_gpio in self._exported_gpios:
      if os.path.exists(GPIO_PIN_PATTERN % opened_gpio):
        with open(UNEXPORT_FILE, 'w') as f:
          self._logger.debug('writing %d to %s', opened_gpio, UNEXPORT_FILE)
          f.write('%d' % opened_gpio)

  def _export_gpio(self, gpio_index):
    """Exports a GPIO system resource.

    Args:
      gpio_index: GPIO number we want to export.
    """
    if not os.path.exists(GPIO_PIN_PATTERN % gpio_index):
      try:
        with open(EXPORT_FILE, 'w') as f:
          self._logger.debug('writing %d to %s', gpio_index, EXPORT_FILE)
          f.write('%d' % gpio_index)
      except IOError:
        self._logger.warn('GPIO: %s was already exported.', gpio_index)
      if gpio_index not in self._exported_gpios:
        self._exported_gpios.append(gpio_index)

  def _set_direction(self, gpio_path, dir_val):
    """Set gpio direction.

    Args:
      gpio_path : path to the GPIO control directory we care about.
      dir_val   : direction value of the gpio.  dir_val is interpretted as:
                  0    : configure as input
                  1    : configure as output
    """
    with open(os.path.join(gpio_path, 'direction'), 'w') as f:
      self._logger.debug('Writing %s to %s/direction', DIR_VAL_MAP[dir_val],
                         gpio_path)
      f.write(DIR_VAL_MAP[dir_val])

  def _set_pinmux(self, gpio_name, muxfile=None):
    """Set pinmux to route this pin as a GPIO

    Args:
      gpio_name: gpio naming convention for the pinmux-es.
      muxfile : used to specify the correct omap_mux muxfile to select this
                gpio.
    """
    if muxfile:
      self._bbmux_controller.set_muxfile(muxfile, GPIO_MODE_VALUE,
                                         GPIO_SELECT_VALUE)
    else:
      self._bbmux_controller.set_pin_mode(gpio_name, GPIO_MODE_VALUE)

  def wr_rd(self, offset, width, dir_val=None, wr_val=None, chip=None,
            muxfile=None):
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
      chip    : beaglebone gpio chip number.
      muxfile : used to specify the correct omap_mux muxfile to select this
                gpio.


    Returns:
      integer value from reading the gpio value ( masked & aligned )
    """
    self._logger.debug('offset: %s, width:%s, dir_val: %s, wr_val: %s, '
                       'chip: %s, muxfile: %s', offset, width, dir_val, wr_val,
                       chip, muxfile)
    if not chip:
      raise BBgpioError('BBgpio requires chip id for writes and reads.')
    rd_val = 0

    gpio_name = 'gpio%s_%s' % (chip, offset)
    gpio_index = 32 * int(chip, 0) + offset

    if self._bbmux_controller:
      self._set_pinmux(gpio_name, muxfile)

    self._export_gpio(gpio_index)
    gpio_path = GPIO_PIN_PATTERN % gpio_index

    if dir_val is None and wr_val is not None:
      dir_val = DIR_OUT

    if dir_val is not None:
      self._set_direction(gpio_path, dir_val)

    if dir_val:
      # This is a write.
      with open(os.path.join(gpio_path, 'value'), 'w') as f:
        self._logger.debug('Writing %d to %s/value', wr_val, gpio_path)
        f.write('%d' % wr_val)
    else:
      # This is a read.
      with open(os.path.join(gpio_path, 'value'), 'r') as f:
        self._logger.debug('Reading from %s/value', gpio_path)
        rd_val = int(f.read(), 0)
        self._logger.debug('Read value: %d.', rd_val)
        return rd_val
