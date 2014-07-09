# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Text-based LCD module driver for LCM2004."""

# servo libs
import hw_driver


# commands
LCD_CLEAR_DISPLAY = 0x01
LCD_RETURN_HOME = 0x02
LCD_ENTRY_MODE_SET = 0x04
LCD_DISPLAY_CONTROL = 0x08
LCD_CURSOR_SHIFT = 0x10
LCD_FUNCTION_SET = 0x20
LCD_SET_CGRAM_ADDR = 0x40
LCD_SET_DDRAM_ADDR = 0x80

# entry mode
LCD_ENTRY_RIGHT = 0x00
LCD_ENTRY_LEFT = 0x02
LCD_ENTRY_SHIFT_INCREMENT = 0x01
LCD_ENTRY_SHIFT_DECREMENT = 0x00

# on/off control
LCD_DISPLAY_ON = 0x04
LCD_DISPLAY_OFF = 0x00
LCD_CURSOR_ON = 0x02
LCD_CURSOR_OFF = 0x00
LCD_BLINK_ON = 0x01
LCD_BLINK_OFF = 0x00

# display/cursor shift
LCD_DISPLAY_MOVE = 0x08
LCD_CURSOR_MOVE = 0x00
LCD_MOVE_RIGHT = 0x04
LCD_MOVE_LEFT = 0x00

# function set
LCD_8BIT_MODE = 0x10
LCD_4BIT_MODE = 0x00
LCD_2LINE = 0x08
LCD_1LINE = 0x00
LCD_5x10_DOTS = 0x04
LCD_5x8_DOTS = 0x00

# backlight control
LCD_BACKLIGHT_ON = 0x08
LCD_BACKLIGHT_OFF = 0x00

# instruction and data registers
LCD_REGISTER_CMD = 0
LCD_REGISTER_DATA = 1

# EN pin
LCD_EN_BIT = 0b00000100

# data used in the initial stage of LCM
LCD_DATA1_AS_INIT = 0x30
LCD_DATA2_AS_INIT = 0x20

# Devices shared among driver objects:
#   (interface instance, slv) => Lcm2004Device instance
lcm2004_devices = {}


class LcmError(Exception):
  """Error occurred accessing LCM2004."""
  pass


class Lcm2004Device(object):
  """Defines a LCM2004 device shared among many LCM2004 drivers.

  Public Attributes:
    backlight_value: value indicating if a device has backlight.
  """
  def __init__(self):
    self.backlight_value = LCD_BACKLIGHT_ON


class lcm2004(hw_driver.HwDriver):
  """Provides drv=lcm2004 control."""

  # the number of column and row
  COLUMN = 20
  ROW = 4
  ROW_ADDR_OFFSET = [0x00, 0x40, 0x14, 0x54]

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
    super(lcm2004, self).__init__(interface, params)

    device_key = (interface, self._get_slave())
    if device_key not in lcm2004_devices:
      self._device = Lcm2004Device()
      lcm2004_devices[device_key] = self._device
      self._init()
    else:
      self._device = lcm2004_devices[device_key]

  def _init(self):
    """Initiates LCM.

       The initial process refers the figure 24
           in the page 46 of HD44780U datasheet.
    """
    # start in 8bit mode, try to set 4 bit mode
    self._write_expander(LCD_DATA1_AS_INIT)

    # second try
    self._write_expander(LCD_DATA1_AS_INIT)

    # set to 4-bit interface
    self._write_expander(LCD_DATA2_AS_INIT)

    # function set
    self._command(LCD_FUNCTION_SET | LCD_4BIT_MODE | LCD_2LINE | LCD_5x8_DOTS)

    # turn on the display with cursor
    self._command(LCD_DISPLAY_CONTROL | LCD_DISPLAY_ON |
                  LCD_CURSOR_ON | LCD_BLINK_OFF)

    # entry mode set
    self._command(LCD_ENTRY_MODE_SET | LCD_ENTRY_LEFT |
                  LCD_ENTRY_SHIFT_DECREMENT)

    self._home()

    self._clear()

  def _check_8bit(self, v):
    """Checks if v uses only lower 8 bits."""
    if v & 0xFF != v:
      raise LcmError('0x%x is not 8-bit' % v)

  def _get_slave(self):
    """Checks and return needed params to call driver.

    Returns:
      slave: 7-bit i2c address

    Raises:
      LcmError: If the 'slv' doesn't exist.
    """
    if 'slv' not in self._params:
      raise LcmError('Missing slave address "slv"')
    slave = int(self._params['slv'], 0)
    return slave

  def _write_byte(self, byte):
    """Writes one byte to PCF8574(remote IO expander).

    Args:
      byte: One byte sent to IIC bus.
    """
    self._check_8bit(byte)
    self._interface.wr_rd(self._get_slave(), [byte], 0)

  def _write_expander(self, byte):
    """Writes the byte to expander.

       By controlling the high/low of the En pin(bit 2),
       the byte will be sent to the LCM.
       The difference between _write_byte() & _write_expander() is:
       The _write_byte(): byte -IIC-> PCF8574.
       The _write_expander(): byte -IIC-> PCF8574 -Serial-> LCM.
       The _write_expander() sends the byte to LCM by pulling a pulse
       of the EN pin.

    Args:
      byte: 8 bits layout
        bit 7 - 4: High or low nibble of the data, which
            comes from the 2nd paramter of _send().
        bit 3: Backlight on(1)/off(0).
        bit 2: The En pin high(1)/low(0).
        bit 1: Read from(1)/Write to(0) LCM.
        bit 0: Data(1)/command(0) mode.
    """
    self._write_byte(byte)

    # Pull a pulse of EN pin
    self._write_byte(byte | LCD_EN_BIT)
    self._write_byte(byte & ~LCD_EN_BIT)

  def _send(self, data, mode):
    """Sends one byte data to either instruction or data register.

       Because of byte layout describing in _write_expander(),
       we need to separate the "data" byte into high nibble,
       and low nibble and send them in order. Besides that,
       we need to set backlight on/off and data/instruction bit
       before sending the nibble.

    Args:
      data: One byte.
      mode: LCD_REGISTER_CMD or LCD_REGISTER_DATA.
    """
    high_nibble = data & 0xF0
    low_nibble = (data << 4) & 0xF0
    backlight = self._device.backlight_value

    self._write_expander(high_nibble | backlight | mode)
    self._write_expander(low_nibble | backlight | mode)

  def _command(self, data):
    """Sends command to instruction register.

    Args:
      data: One byte command.
    """
    self._send(data, LCD_REGISTER_CMD)

  def _clear(self):
    """Cleans full screen."""
    self._command(LCD_CLEAR_DISPLAY)

  def _home(self):
    """Sets cursor to column 0 and row 0."""
    self._command(LCD_RETURN_HOME)

  def _backlight_on(self):
    """Turns on backlight."""
    self._device.backlight_value = LCD_BACKLIGHT_ON
    self._write_byte(LCD_BACKLIGHT_ON)

  def _backlight_off(self):
    """Turns off backlight."""
    self._device.backlight_value = LCD_BACKLIGHT_OFF
    self._write_byte(LCD_BACKLIGHT_OFF)

  def _Set_lcm_text(self, text):
    """Prints text to LCM.

    Args:
      text: string value to be printed on the LCM.
    """
    if len(text) > lcm2004.COLUMN:
      raise LcmError('The text length is larger than %d.' % lcm2004.COLUMN)

    for c in text:
      self._send(ord(c), LCD_REGISTER_DATA)

  def _Set_lcm_row(self, row_number):
    """Positions LCM cursor.

    Args:
      row_number: range from 0 to 3.
    """
    row = int(row_number)
    if row >= lcm2004.ROW:
      raise LcmError('Row number(%d) is out of range(0-3).' % row)

    self._command(LCD_SET_DDRAM_ADDR |
                  (lcm2004.ROW_ADDR_OFFSET[min(row, lcm2004.ROW - 1)]))

  def _Set_lcm_cmd(self, cmd):
    """Sends command to LCM.

    Args:
      cmd: clear | home | bklon | bkloff.
    """
    if cmd == 'clear':
      self._clear()
    elif cmd == 'home':
      self._home()
    elif cmd == 'bklon':
      self._backlight_on()
    elif cmd == 'bkloff':
      self._backlight_off()
    else:
      raise LcmError('Unsupported command(%s).' % cmd)
