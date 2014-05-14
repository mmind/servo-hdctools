# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for TI TCS3414 color sensor.

The driver returns HSV color coordinates so that the sensed color can be
recognized in natural way. We can check a range of Hue (H) and lower bound of
Saturation (S) and Lightness (V) to detect external lighting.

Under different environment, we can adjust the ADC gain or integration timing to
improve the quality of reading.

"""

# standard python libs
import colorsys
import time

# servo libs
import hw_driver


# I/O registers
REG_COMMAND_BIT = 0x80
REG_WORD_BIT = 0x20

REG_CONTROL = 0x00
REG_TIMING = 0x01
REG_GAIN = 0x07
REG_GREEN_CHANNEL = 0x10
REG_RED_CHANNEL = 0x12
REG_BLUE_CHANNEL = 0x14
REG_CLEAR_CHANNEL = 0x16

# bits 0-1 of control register (ADC_EN + POWER)
CONTROL_POWERON = 0x03
CONTROL_POWEROFF = 0x00

# bits 4-5 of timing register (Integ Mode)
TIMING_FREE_RUNNING = 0x00

# allowed integration time (in milliseconds)
TIMING_12MS = 12
TIMING_100MS = 100
TIMING_400MS = 400

# bits 0-3 of timing register (Integration Time)
TIMING_TIME_BITS = {
  TIMING_12MS: 0x00,  # default value
  TIMING_100MS: 0x01,
  TIMING_400MS: 0x02
}

# bits 0-2 of gain register (Prescaler)
GAIN_PRESCALER_DIVIDE_BY_1 = 0x00

# allowed ADC analog gain
GAIN_1X = 1
GAIN_4X = 4
GAIN_16X = 16
GAIN_64X = 64

# bits 4-5 of gain register (Analog Gain Control)
GAIN_ANALOG_BITS = {
  GAIN_1X: 0x00,
  GAIN_4X: 0x10,
  GAIN_16X: 0x20,
  GAIN_64X: 0x30
}

# millisecond
MSEC = 1e-3

# Linux kernel is not real-time, sleep some more time.
SLEEP_MORE_TIME = 5 * MSEC


# Devices shared among driver objects:
#   (interface instance, slv) => Tcs3414Device instance
tcs3414_devices = {}


class Tcs3414Error(Exception):
  """Error occurred accessing TCS3414."""
  pass


class Tcs3414Device(object):
  """Define a TCS3414 device shared among many tcs3414 drivers.

  Note: public members are directly accessible by tcs3414 class.
  """
  def __init__(self):
    self.integ_time = TIMING_12MS
    self.analog_gain = GAIN_1X


class tcs3414(hw_driver.HwDriver):
  """Provides drv=tcs3414 control.

  Note: The public interfaces of the object are of the form _Get_X() / _Set_X(),
  where X is params['subtype']. Instances of this object get dispatched via
  get/set methods of the base class, HwDriver.

  For example, to call _Get_HSV():

    params['subtype'] = 'HSV'
    drv = tcs3414(interface, params)
    hsv = drv.get()
  """

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: interface object to handle low-level communication.
      params: dictionary of params needed to perform operations on the device.
          All items are strings initially but should be cast to types detailed
          below.

    Mandatory Params:
      slv: integer, 7-bit i2c slave address

    Optional Params:
      N/A
    """
    super(tcs3414, self).__init__(interface, params)

    device_key = (interface, self._get_slave())
    if device_key not in tcs3414_devices:
      tcs3414_devices[device_key] = Tcs3414Device()

    self._device = tcs3414_devices[device_key]

    self._logger.debug('Initialized %d TCS3414 devices' % len(tcs3414_devices))

  def _convert_HSV(self, r, g, b, i):
    """Converts RGB to HSV coordinate.

    http://en.wikipedia.org/wiki/HSL_and_HSV

    Args:
      r: 16-bit red value.
      g: 16-bit green value.
      b: 16-bit blue value.
      i: 16-bit intensity value.

    Returns:
      [H, S, V]: the coordinates are all between 0 and 1.
    """
    def w2f(b):
      return float(b) / 65535.0

    h, s, _ = colorsys.rgb_to_hsv(w2f(r), w2f(g), w2f(b))

    return [h, s, w2f(i)]

  def _check_8bit(self, v):
    if v & 0xFF != v:
      raise Tcs3414Error("0x%x is not 8-bit" % v)

  def _get_slave(self):
    """Checks and return needed params to call driver.

    Returns:
      slave: 7-bit i2c address
    """
    if 'slv' not in self._params:
      raise Tcs3414Error('Missing slave address "slv"')
    slave = int(self._params['slv'], 0)
    return slave

  def _write_byte(self, reg, data):
    """Writes one byte to register.

    Args:
      reg: Register address.
      data: One byte.

    Returns:
      None
    """
    self._check_8bit(reg)
    self._check_8bit(data)

    self._interface.wr_rd(self._get_slave(), [reg, data], 0)

  def _read_word(self, reg):
    """Reads a word by giving a register address.

    Args:
      reg: Register address.

    Returns:
      16-bit value.
    """
    self._check_8bit(reg)

    values = self._interface.wr_rd(self._get_slave(), [reg], 2)
    return values[0] + (values[1] << 8)

  def _power_on(self):
    self._write_byte(REG_COMMAND_BIT | REG_CONTROL, CONTROL_POWERON)

  def _power_off(self):
    self._write_byte(REG_COMMAND_BIT | REG_CONTROL, CONTROL_POWEROFF)

  def _Set_gain(self, value):
    """Sets ADC gain.

    Args:
      value: analog gain multiplier
    """
    if value not in GAIN_ANALOG_BITS:
      raise Tcs3414Error('Analog gain %d is unsupported' % value)
    self._device.analog_gain = value

    byte = GAIN_ANALOG_BITS[value] | GAIN_PRESCALER_DIVIDE_BY_1
    self._write_byte(REG_COMMAND_BIT | REG_GAIN, byte)

  def _Set_timing(self, value):
    """Sets integration time for each read.

    Args:
      value: integration time in milliseconds.
    """
    if value not in TIMING_TIME_BITS:
      raise Tcs3414Error('Integration time of %d ms is unsupported' % value)
    self._device.integ_time = value

    byte = TIMING_TIME_BITS[value] | TIMING_FREE_RUNNING
    self._write_byte(REG_COMMAND_BIT | REG_TIMING, byte)

  def _Get_HSV(self):
    """Gets reading in HSV colorspace.

    Note: if V == 1.0, it means the integration is digitally saturated. You
    should lower gain or integration time.

    Returns:
      [H, S, V]

    """
    self._power_on()

    time.sleep(self._device.integ_time * MSEC + SLEEP_MORE_TIME)

    color_r = self._read_word(REG_COMMAND_BIT | REG_WORD_BIT | REG_RED_CHANNEL)
    color_g = self._read_word(REG_COMMAND_BIT | REG_WORD_BIT |
                              REG_GREEN_CHANNEL)
    color_b = self._read_word(REG_COMMAND_BIT | REG_WORD_BIT | REG_BLUE_CHANNEL)
    intensity = self._read_word(REG_COMMAND_BIT | REG_WORD_BIT |
                                REG_CLEAR_CHANNEL)

    self._power_off()  # Save power

    self._logger.debug('Read RGBI values (%d, %d, %d, %d)',
                       color_r, color_g, color_b, intensity)
    return self._convert_HSV(color_r, color_g, color_b, intensity)
