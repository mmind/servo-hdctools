# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls tca6416 dual port (16bit) ioexpander.
"""
import drv.hw_driver


# base indexes of the input, output, polarity and direction registers
# respectively.  Base is for port 0, +1 for port 1
REG_INP = 0
REG_OUT = 2
REG_POL = 4
REG_DIR = 6


class Tca6416Error(Exception):
  """Error occurred accessing TCA6416."""


# TODO(tbroch) style guide wants these to be camel-case but can we have
# exception as these get loaded dynamically
class tca6416(drv.hw_driver.HwDriver):
  """Object to access drv=tca6416 controls."""
  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: FTDI interface object to handle low-level communication to
          control
      params: dictionary of params needed to perform operations on ina219
          devices.  All items are strings initially but should be cast to types
          detailed below.

    Per TCA6416 datasheet Pg8 ( SCPS153A-DECEMBER 2007-REVISED FEBUARY 2009 )
    the device does support register index caching, 'Once a new command has been
    sent, the register that was addressed continues to be accessed by reads
    until a new command byte has been sent.'  However the ports act as a
    pair so the behavior is more complex.

    For example if you start with a transcation like:
    i2c write of 0x00 (input register of port 0) then
    i2c read of 1 byte == input register values of port 0 then
    i2c read of 1 byte == input register values of port 1 then
    i2c read of 1 byte == input register values of port 0 then
    
    Effectively the reg value to cache is:
      reg_cache = (reg & 0x6) ^ (~reg & (0x1 & rcnt))

    As we use the TCA6416 for mostly single bit gpio's there's not much utility
    to adding this complication to manage register caching.  For that reason it
    remains off ( use_reg_cache=False )

    Mandatory Params:
      slv: integer, 7-bit i2c slave address
      port: integer, either 0 || 1
    Optional Params:
    """
    super(tca6416, self).__init__(interface, params)
    (slave, port) = self._get_slave_port()
    self._i2c_obj = drv.i2c_reg.I2cReg.get_device(self._interface, slave,
                                                  addr_len=1, reg_len=1,
                                                  msb_first=True,
                                                  use_reg_cache=False)
    self._port = port

  def get(self):
    """Get gpio value.

    tca6416 has a dedicated input register ( per port ) so GPIO's current value
    can be read there.

    Returns:
      integer in formatted representation
    """
    self._logger.debug("")
    value = self._i2c_obj._read_reg(REG_INP + self._port)
    return self._create_logical_value(value)

  def set(self, fmt_value):
    """Set value on ioexpander.

    1. Read Output register
    2. Mask accordingly
    3. Write value to Output register
    4. Read Direction register (Note 0 == output, 1 == input)
       a. if input, Write Direction register 
    5. Read Input register for returning

    Args: 
      fmt_value: Integer value to write to hardware.
    """
    self._logger.debug("")
    hw_value = 0
    (offset, mask) = self._get_offset_mask()
    if fmt_value:
      hw_value = self._create_hw_value(fmt_value)
    # output register handling
    out_reg = self._i2c_obj._read_reg(REG_OUT + self._port)
    self._i2c_obj._write_reg(REG_OUT + self._port, 
                             hw_value | (out_reg & ~mask))

    #TODO(tbroch) cache direction register for speedup
    dir_reg = self._i2c_obj._read_reg(REG_DIR + self._port)
    if dir_reg & mask:
      # its presently an input ... flip dir bit(s)
      self._i2c_obj._write_reg(REG_DIR + self._port, dir_reg & ~mask)

  def _get_slave_port(self):
    """Check and return needed params to call driver.
    
    Returns:
      tuple (slave, port) where
        slave: 7-bit i2c address
        port: port ( 0 | 1 ) on the tca6416 (used to calc register index)
    """
    if 'slv' not in self._params:
      raise Tca6416Error("getting slave address")
    slave = int(self._params['slv'], 0)
    if 'port' not in self._params:
      raise Tca6416Error("getting port")
    port = int(self._params['port'], 0)
    if port & 0x1 != port:
      raise Tca6416Error("port value should be 0 | 1")
    return (slave, port)
