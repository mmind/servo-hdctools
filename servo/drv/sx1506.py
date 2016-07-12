# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for sx1506 16bit ioexpander.
"""
import hw_driver
import i2c_reg


class Sx1506Error(Exception):
  """Error occurred accessing Sx1506."""

# We need a shared register cache between all the bits,
# as there is no readable state register.
# Indexing is: reg_cache[((interface, i2c addr), reg addr)] = value
reg_cache = {}


class sx1506(hw_driver.HwDriver):
  """Object to access drv=sx1506 controls."""


  # base indexes of the data, direction, pullup and pulldown registers
  # respectively.
  REG_DATA= 0
  REG_DIR= 2
  REG_PU= 4
  REG_PD= 6


  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: i2c interface object to handle low-level communication to
          control
      params: dictionary of params needed to perform operations on an sx1506
          io expander.  All items are strings initially but should be cast to types
          detailed below.


    Mandatory Params:
      slv: integer, 7-bit i2c slave address
      offset: integer, gpio's bit position from lsb
    Optional Params:
    """
    super(sx1506, self).__init__(interface, params)
    slave = self._get_slave()
    self._i2c_obj = i2c_reg.I2cReg.get_device(self._interface, slave,
                                              addr_len=1, reg_len=1,
                                              msb_first=True, no_read=False,
                                              use_reg_cache=False)
    # Remember what GPIOs we have set.
    global reg_cache
    self._reg_cache = reg_cache
    self._cacheindex = (self._interface, slave)
    # Cache REG_DATA
    outputs = self._reg_cache.get((self._cacheindex, self.REG_DATA), 0xffff)
    self._reg_cache[(self._cacheindex, self.REG_DATA)] = outputs
    # Cache REG_DIR
    dir = self._reg_cache.get((self._cacheindex, self.REG_DIR), self.read16(self.REG_DIR))
    self._reg_cache[(self._cacheindex, self.REG_DIR)] = dir

    # Initlialize pullup
    if self._io_type == 'PU':
      (offset, mask) = self._get_offset_mask()

      pu_reg = self.read16(self.REG_PU)
      pu_reg = pu_reg | mask
      self.write16(self.REG_PU, pu_reg)

  def read16(self, reg):
    value_low = self._i2c_obj._read_reg(reg + 1)
    value_high = self._i2c_obj._read_reg(reg)

    value = value_low | (value_high << 8)
    return value

  def write16(self, reg, val):
    self._i2c_obj._write_reg(reg + 1, (val & 0xff))
    self._i2c_obj._write_reg(reg, (val >> 8))

  def get(self):
    """Get gpio value.

    sx1506 has data registers REG_DATA. GPIO's current value
    can be read there.

    Returns:
      integer in formatted representation
    """
    self._logger.debug("")
    value = self.read16(self.REG_DATA)
    return self._create_logical_value(value)

  def set(self, fmt_value):
    """Set value on ioexpander.

    1. Read cached value
    2. Mask accordingly
    3. Write value to Output register
    4. Read Direction reg cache (Note 0 == output, 1 == input)
       a. if input, Write Direction register
    5. Read Input register for returning

    Args:
      fmt_value: Integer value to write to hardware.  If None or empty string
        defaults to 0.

    Raises:
      Sx1506Error: If width of open drain driver is != 1 or open drain type is
        not recognized.
    """
    self._logger.debug("sx1506 set %s" % fmt_value)
    (_, mask) = self._get_offset_mask()
    if mask is None:
        raise Sx1506Error("Unable to determine mask.  Is offset declared?")

    change_to_input = False
    if self._io_type == "PU" and fmt_value == 1:
      self._logger.debug("Set to input because its io type is PU")
      change_to_input = True

    # output register handling
    if not change_to_input:
      hw_value = 0
      if fmt_value:
        hw_value = self._create_hw_value(fmt_value)

      current_out_reg = self._reg_cache[(self._cacheindex, self.REG_DATA)]
      new_out_reg = hw_value | (current_out_reg & ~mask)
      if new_out_reg != current_out_reg:
        self._reg_cache[(self._cacheindex, self.REG_DATA)] = new_out_reg
        self.write16(self.REG_DATA, new_out_reg)

    current_dir_reg = self._reg_cache[(self._cacheindex, self.REG_DIR)]
    if change_to_input:
      new_dir_reg = current_dir_reg | mask
    else:
      new_dir_reg = current_dir_reg & ~mask

    if new_dir_reg != current_dir_reg:
      self._reg_cache[(self._cacheindex, self.REG_DIR)] = new_dir_reg
      self.write16(self.REG_DIR, new_dir_reg)

  def _get_slave(self):
    """Check and return needed params to call driver.

    Returns:
      slave: 7-bit i2c address
    """
    if 'slv' not in self._params:
      raise Sx1506Error("getting slave address")
    slave = int(self._params['slv'], 0)
    return slave
