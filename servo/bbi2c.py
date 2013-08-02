# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Allows creation of i2c interface for beaglebone devices."""
import logging
import subprocess


class BBi2cError(Exception):
  """Class for exceptions of BBi2c."""
  def __init__(self, msg, value=0):
    """BBi2cError constructor.

    Args:
      msg: string, message describing error in detail
      value: integer, value of error when non-zero status returned.  Default=0
    """
    super(BBi2cError, self).__init__(msg, value)
    self.msg = msg
    self.value = value

class BBi2c(object):
  """Provide interface to i2c through beaglebone"""

  def __init__(self, interface):
    self._logger = logging.getLogger("BBi2c")
    self._interface = interface
    self._bus_num = interface['bus_num']

  def open(self):
    """Opens access to FTDI interface as a i2c (MPSSE mode) interface.

    Raises:
      BBi2cError: If open fails
    """
    pass

  def close(self):
    """Close connection to i2c through beaglebone and cleanup.

    Raises:
      BBi2cError: If close fails
    """
    pass

  def setclock(self, speed=100000):
    """Sets i2c clock speed.

    Args:
      speed: clock speed in hertz.  Default is 100kHz
    """
    pass

  def _write(self, slv, address, wlist):
    """Preform a single i2cset write command.

    Args:
      slv: 7-bit address of the slave device.
      address: data address we are writing to. Will be written to the i2c bus.
      wlist: list of bytes to write to the slave. List length must be between
          0-2 bytes.

    Raises:
      BBi2cError: If wlist has more than 3 bytes or the i2cset call fails.
    """
    # i2cset can write up to 3 bytes to an i2c device in the format of:
    # [1-byte address][0-2 bytes of data]
    args = ['i2cset', '-y', str(self._bus_num), '0x%02x' % slv,
            address]
    if len(wlist) > 2:
      raise BBi2cError('Can only write up to 3 bytes (1-byte register address '
                       'and 2-byte word) per i2cset command. '
                       'wlist: %s' % wlist)
    # Form the data argument and reverse the bytes due to endianness.
    if wlist:
      data = '0x' + ''.join('%02x' % wbyte for wbyte in reversed(wlist))
      args.append(data)
      if len(wlist) == 2:
        # Put the command in word mode.
        args.append('w')
    try:
      logging.debug(' '.join(args))
      subprocess.check_call(args)
    except subprocess.CalledProcessError:
      raise BBi2cError('Failed i2c write to slave address: %s data: %s' % (slv,
                       wlist))

  def _read(self, slv, address, rcnt):
    """Read from a slave i2c device.

    Args:
      slv: 7-bit address of the slave device.
      address: data address to read.
      rcnt: number of bytes (0-2) to read from the device.

    Returns:
      list of bytes read from i2c device.

    Raises:
      BBi2cError: If read (i2cget call) fails or if rcnt > 2.
    """
    if not rcnt:
      return []

    if rcnt > 2:
      raise BBi2cError('Can only read up to 2 bytes per i2cget command.')

    if rcnt == 2:
      return self._read_two_bytes(slv, address)

    return self._read_one_byte(slv)

  def _read_one_byte(self, slv):
    """Read one byte from a slave i2c device.

    Args:
      slv: 7-bit address of the slave device.

    Returns:
      list of bytes read from i2c device.

    Raises:
      BBi2cError: If read (i2cget call) fails.
    """
    read_bytes = []
    args = ['i2cget', '-y', str(self._bus_num), '0x%x' % slv]
    try:
      logging.debug(' '.join(args))
      read_value = subprocess.check_output(args)
    except subprocess.CalledProcessError:
      raise BBi2cError('Failed i2c read of 1 byte from slave address: %s' %
                       slv)
    read_value_int = int(read_value, 0)
    read_bytes.append(read_value_int)
    return read_bytes

  def _read_two_bytes(self, slv, address):
    """Read two byte from a slave i2c device.

    Args:
      slv: 7-bit address of the slave device.
      address: data address to read.

    Returns:
      list of bytes read from i2c device.

    Raises:
      BBi2cError: If read (i2cget call) fails.
    """
    read_bytes = []
    args = ['i2cget', '-y', str(self._bus_num), '0x%x' % slv, address, 'w']
    try:
      logging.debug(' '.join(args))
      read_value = subprocess.check_output(args)
    except subprocess.CalledProcessError:
      raise BBi2cError('Failed i2c read of 2 bytes from slave address: %s, '
                       'data address: %s.' % (slv, address))
    read_value_int = int(read_value, 0)
    # Grab the second byte first (converting little endian to big).
    read_bytes.append(read_value_int & 0xff)
    # Grab the first byte.
    read_bytes.append(read_value_int >> 8)
    return read_bytes

  def wr_rd(self, slv, wlist, rcnt):
    """Write and/or read a slave i2c device.

    Args:
      slv: 7-bit address of the slave device
      wlist: list of bytes to write to the slave.  If list length is zero its
          just a read.
      rcnt: number of bytes (0-2) to read from the device. If zero, its just a
          write.

    Returns:
      list of bytes read from i2c device.
    """
    self._logger.debug('wr_rd. slv: 0x%x, wlist: %s, rcnt: %s', slv, wlist,
                       rcnt)
    address = '0x%02x' % wlist[0]
    if wlist:
      self._write(slv, address, wlist[1:])

    return self._read(slv, address, rcnt)


def test():
  """Test code. (forked from ftdii2c.py)"""
  loglevel=logging.INFO
  logging.basicConfig(level=loglevel,
                      format='%(asctime)s - %(name)s - ' +
                      '%(levelname)s - %(message)s')
  i2c = BBi2c(3)

  wbuf = [0]
  slv = 0x21
  rbuf = i2c.wr_rd(slv, wbuf, 1)
  logging.info('first: i2c read of slv=0x%02x reg=0x%02x == 0x%02x' %
               (slv, wbuf[0], rbuf[0]))
  errcnt = 0
  for cnt in xrange(1000):
    try:
      rbuf = i2c.wr_rd(slv, [], 1)
    except:
      errcnt += 1
      logging.error('errs = %d cnt = %d' % (errcnt, cnt))

  logging.info('last: i2c read of slv=0x%02x reg=0x%02x == 0x%02x' %
               (slv, wbuf[0], rbuf[0]))

if __name__ == '__main__':
  test()
