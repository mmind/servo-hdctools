# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""EEPROM driver for ST M24C02.

The driver provides functions to read data from or write data to
one of 8 ST M24C02 EEPROMs, which slave addresses are 0x50 - 0x57.
"""

# servo libs
import hw_driver


# Devices shared among driver objects:
#   (interface instance, slv) => M24C02Device instance
m24c02_devices = {}


class EepromError(Exception):
  """Error occurred accessing M24C02."""
  pass


class M24C02Device(object):
  """Defines a M24C02 device shared among many M24C02 drivers."""
  def __init__(self, offset, read_count):
    self._offset = offset
    self._read_count = read_count

  def set(self, offset, read_count):
    """Set offset and read count.

    Args:
      offset: Start address for reading/writing.
      read_count: Size of reading bytes.

    Raises:
      ValueError: If offset or count doesn't make sense.
    """
    if (offset < 0) or (offset > (m24c02._EEPROM_SIZE - 1)):
      raise ValueError("Offset(%d) error." % offset)
    if (offset + read_count) > m24c02._EEPROM_SIZE:
      raise ValueError("Boundary(%d) error." % (offset + read_count))

    self._offset = offset
    self._read_count = read_count

  def get(self):
    """Get the operating parameters.

    Returns:
      Get offset and read count.
    """
    return (self._offset, self._read_count)


class m24c02(hw_driver.HwDriver):
  """Provides drv=m24c02 control."""

  # Supported M24C02 slave addresses.
  SUPPORTED_ADDRESS = (80, 81, 82, 83, 84, 85, 86, 87)

  _EEPROM_SIZE = 256
  HELP_TEXT = """
    # Step 1. Prepare parameters for operating EEPROM.
      dut-control plankton_rom_[1-8]_parameter
      dut-control plankton_rom_[1-8]_parameter:"[offset];[read count]"

    # Step 2. Read/write data from/to EEPROM.
      dut-control plankton_rom_[1-8]_data
      dut-control plankton_rom_[1-8]_data:"[text]"

    # Example
      dut-control plankton_rom_1_parameter
      dut-control plankton_rom_1_parameter:"10;20"
      dut-control plankton_rom_1_data               # read 20 bytes from offset 10
      dut-control plankton_rom_1_data:"Hello"  # write "Hello" to  offset 10
    """

  def _get_slave(self):
    """Checks and return needed params to call driver.

    Returns:
      slave: 7-bit i2c address.

    Raises:
      EepromError: If the 'slv' doesn't exist.
    """
    if 'slv' not in self._params:
      raise EepromError('Missing slave address "slv"')
    slave = int(self._params['slv'], 0)
    return slave

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: Interface object to handle low-level communication.
      params: Dictionary of params needed to perform operations on the device.

    Raises:
      ValueError: If slave address doesn't make sense.
    """
    super(m24c02, self).__init__(interface, params)

    slave = self._get_slave()
    if slave not in m24c02.SUPPORTED_ADDRESS:
      raise ValueError("Slave address(%d) error." % slave)

    offset = 0
    read_count = m24c02._EEPROM_SIZE
    device_key = (interface, slave)
    if device_key not in m24c02_devices:
      m24c02_devices[device_key] = M24C02Device(offset, read_count)

    self._device = m24c02_devices[device_key]

  def _read_byte(self, offset):
    """Reads one byte from EEPROM.

    Args:
      offset: Start address for reading.

    Returns:
      Read back one byte.
    """
    buffer = self._interface.wr_rd(self._get_slave(), [offset], 1)
    return buffer[0]

  def _read_bytes(self, offset, count):
    """Reads one or more bytes from EEPROM.

    Args:
      offset: Start address for reading.
      count: Size of reading bytes.

    Returns:
      A list of bytes.
    """
    # TODO(Aaron) To replace this with bulk read command.
    return [self._read_byte(addr) for addr in xrange(offset, offset + count)]

  def _write_byte(self, offset, value):
    """Writes one byte to EEPROM.

    Args:
      offset: Start address for writing.
      value: One byte written to EEPROM.
    """
    self._interface.wr_rd(self._get_slave(), [offset, value], 0)

  def _write_bytes(self, offset, text):
    """Writes one or more bytes to EEPROM.

    Args:
      offset: Start address for writing.
      text: One or more bytes written to EEPROM.

    Raises:
      ValueError: If text exceeds EEPROM size.
    """
    if (offset + len(text)) > m24c02._EEPROM_SIZE:
      raise ValueError("Boundary(%d) error." % (offset + len(text)))

    for c in text:
      self._write_byte(offset, ord(c))
      offset = offset + 1

  def _Get_rom_params(self):
    """Gets operating paramters.

    Returns:
      Show slave address, offset, and read count.
    """
    return (self._get_slave(),) + self._device.get()

  def _Set_rom_params(self, params):
    """Sets offset and read count.

    Args:
      params: Format is "[offset];[read count]"

    Raises:
      EepromError: If offset or count doesn't make sense.
    """
    try:
      offset, read_count = map(int, params.split(';', 1))
      self._device.set(offset, read_count)
    except (ValueError, IndexError) as e:
      raise EepromError(str(e) + m24c02.HELP_TEXT)

  def _Get_data(self):
    """Reads bytes from one of 8 EEPROMs.

    Returns:
      Read one or more bytes.
    """
    offset, read_count = self._device.get()
    return self._read_bytes(offset, read_count)

  def _Set_data(self, text):
    """Writes bytes to one of 8 EEPROMs.

    Args:
      text: data will be written to EEPROM.

    Raises:
      EepromError: If text exceeds EEPROM size.
    """
    try:
      offset, dummy = self._device.get()
      self._write_bytes(offset, text)
    except ValueError as e:
      raise EepromError(str(e) + m24c02.HELP_TEXT)
