# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""i2c register module
"""
import logging


# dictionary key'd off (interface, slv) with value == Ina219 instance such that
# multiple controls that map to same physical IC on same I2C bus share one
# object.  This caching allows object to keep track of stateful things about the
# the device such as where the register index is pointing.
_devices = {}


class I2cRegError(Exception):
  """Exception class for I2cRegError."""


class I2cReg(object):
  """Provides methods for devices with registered indexing over i2c."""
  def __init__(self, i2c, slave, addr_len=1, reg_len=2, msb_first=True,
               no_read=False, use_reg_cache=False):
    """I2cReg constructor.

    Args:
      i2c: instance provides methods to access device via i2c
          Must include: wr_rd(slave, bytes to wr, wr_list, bytes to read)
      slave: 7-bit i2c address of device
      addr_len: length of register address in bytes
      reg_len: length of register in bytes
      msb_first: if True, most significant byte is first
      no_read: if True, do NOT read value after a write is performed
      use_reg_cache: i2c device remembers last register index internally 
          don't re-write if it matches

    Raises:
      ValueError: if addr_len is != 1
    """
    self._logger = logging.getLogger("I2cReg")
    self._i2c = i2c
    self._slave = slave
    self._addr_len = addr_len
    self._reg_len = reg_len
    self._msb_first = msb_first
    self._no_read = no_read
    self._use_reg_cache = use_reg_cache
    self._reg = None

    # TODO(tboch) fixme addr_len unused
    if self._addr_len != 1:
      raise ValueError("address length must be 1")
    # 7-bit i2c has 112 valid slaves addresses from 0x8 -> 0x77 only
    if (slave < 0x8) or (slave > 0x77):
      raise I2cRegError("slave addr range should be within (8,119)")

  @classmethod
  def get_device(cls, i2c, slave, addr_len, reg_len, msb_first, no_read,
                 use_reg_cache):
    """Get device from module dict or create one if it doesn't exist.

    This class method allows sharing of objects that have the same i2c bus and
    slave address.  This makes it possible to keep stateful information about
    the i2c device.  Particularly its register index.  Many i2c devices have
    registered indexing and store there current register index internally.
    Caching it allows this driver to reduce the size of the transaction to the
    i2c slave by removing the register index when the device is already pointing
    to that register

    Args:
      See constructor
    
    Returns:
      instance of I2cReg object
    """
    key = (i2c, slave)
    if key in _devices:
      return _devices[key]
    else:
      dev_obj = cls(i2c, slave, addr_len, reg_len, msb_first, no_read,
                    use_reg_cache)
      _devices[key] = dev_obj
    return dev_obj
    
  def _read_reg(self, reg):
    """Read the register.
    
    Args:
      reg: i2c register to read

    Returns:
      integer value read from i2c reg
    """
    self._logger.debug("")
    rlist = self._wr_rd(reg, [], self._reg_len)
    return self._convert_rd(rlist, self._msb_first)

  def _write_reg(self, reg, value):
    """Write the register.

    Args:
      reg: i2c register to read
      value: integer value to write to reg

    Returns:
      integer value read after the write of reg
    """
    self._logger.debug("")
    wlist = []
    for _ in xrange(self._reg_len):
      wlist.append(value & 0xff)
      value = value >> 8
    if value != 0: 
      raise ValueError("write reg value larger than register")
    if self._msb_first:
      wlist.reverse()

    read_len = 0 if self._no_read else self._reg_len
    rlist = self._wr_rd(reg, wlist, read_len)
    return self._convert_rd(rlist, self._msb_first)

  @staticmethod
  def _convert_rd(rlist, msb_first):
    """Convert read value in c_ubyte array to integer.

    Args:
      rlist: list of integers to convert
      msb_first: if True, most significant byte first in rd_arr

    Returns:
      integer value converted from c_ubyte array based on byte ordering

    >>> "0x%08x" % I2cReg._convert_rd([1, 2, 3], False)
    '0x00030201'
    >>> "0x%08x" % I2cReg._convert_rd([1, 2, 3], True)
    '0x00010203'
    >>> "0x%016x" % I2cReg._convert_rd([1, 2, 3, 4, 5], False)
    '0x0000000504030201'
    >>> "0x%02x" % I2cReg._convert_rd([], False)
    '0x00'
    >>> "0x%02x" % I2cReg._convert_rd([], True)
    '0x00'
    """
    if msb_first:
      rlist.reverse()

    value = 0
    for cnt, byte in enumerate(rlist):
      assert (byte & 0xff) == byte, "byte range is 0 -> 255"
      value |= byte << (cnt * 8)
    return value

  def _wr_rd(self, reg, wlist, rcnt):
    """Convenience function for accessing i2c device.

    Args:
      reg: register index to access on i2c device
      wlist: list of bytes to write
      rcnt: number of bytes to read
    
    Returns:
      list of c_ubyte's read from i2c device.
    """
    # checked the last register access ... if same can remove from
    # operation if device keeps last index.
    self._logger.debug("")
    if not self._use_reg_cache or reg != self._reg:
      wlist = [reg] + wlist
    else:
      self._logger.debug("Ignoring register index %d is cached" % reg)

    rlist = self._i2c.wr_rd(self._slave, wlist, rcnt)
    if self._use_reg_cache:
      self._reg = reg
    return rlist
