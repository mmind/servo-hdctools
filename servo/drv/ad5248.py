# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for Analog Devices AD5248 digital potentiometer.

AD5248 is a two-channel potentiometer. The resistance Rwb between terminal W1
and B1, or W2 and B2, is determined by each RDAC byte register, which can be
programmed via I2C interface.

Output resistance Rwb(D) = D/256 * full resistance + 2 * wiper resistance
  - D: RDAC register value
  - full resistance: depend on spec, may be 2.5k, 10k, 50k, 100k Ohm
  - wiper resistance: contact resistance on wiper, 160 Ohm in spec

Note that the greater D causes the greater Rwb. On the other hand, Rwa is the
complementally resistance between terminal W and A.
TODO(johnylin): add Rwa support if necessary.

For subtype 'rdac':
  - set: set RDAC value
  - get: read out RDAC value

For subtype 'r2p5k', 'r10k', 'r50k', 'r100k':
  - set: specify a resistance value (in Ohm) within spec range. Since ad5248 is
    only 256-step, servo will find the closest step to set.
    (Note: you may not 'get' the same value after 'set' due to this)
  - get: get equivalent output resistance value (in Ohm).
"""
import hw_driver

WIPER_RESISTANCE = 160
FULL_RESISTANCE_SPEC = {'r2p5k': 2500,
                        'r10k': 10000,
                        'r50k': 50000,
                        'r100k': 100000}

class Ad5248Error(Exception):
  """Error occurred accessing AD5248."""


class ad5248(hw_driver.HwDriver):
  """Object to access drv=ad5248 controls."""

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: FTDI interface object to handle low-level communication to
          control
      params: dictionary of params needed to perform operations on ad5248
          devices.  All items are strings initially but should be cast to types
          detailed below.

    Mandatory Params:
      slv: integer, 7-bit i2c slave address
      port: integer, either 0 || 1
      subtype: string, supporting 'rdac', 'r2p5k', 'r10k', 'r50k', and 'r100k'
    Optional Params:
    """
    super(ad5248, self).__init__(interface, params)
    self._slave = self._get_slave()
    self._port = self._get_port()
    self._subtype = self._get_subtype()

  def _get_slave(self):
    """Check and return slave param.

    Returns:
      slave: 7-bit i2c address.
    """
    if 'slv' not in self._params:
      raise Ad5248Error("getting slave address")
    slave = int(self._params['slv'], 0)
    return slave

  def _get_port(self):
    """Check and return port param.

    Returns:
      port: port ( 0 | 1 ) on the ad5248.
    """
    if 'port' not in self._params:
      raise Ad5248Error("getting port")
    port = int(self._params['port'], 0)
    if port & 0x1 != port:
      raise Ad5248Error("port value should be 0 | 1")
    return port

  def _get_subtype(self):
    """Check and return subtype param.

    Returns:
      subtype: subtype for full resistance spec.
    """
    if 'subtype' not in self._params:
      raise Ad5248Error("getting subtype")
    subtype = self._params['subtype']
    if subtype != 'rdac' and subtype not in FULL_RESISTANCE_SPEC:
      raise Ad5248Error("subtype value should be 'rdac' or %s" %
                        FULL_RESISTANCE_SPEC.keys())
    return subtype

  def _set_rdac(self, byte):
    """Sets RDAC register value of ad5248.

    Args:
      byte: 8-bit value. The format could be either a string '0xNN' or an
          integer.
    """
    if isinstance(byte, str):
      byte = int(byte, 0)
    if not 0 <= byte <= 255:
      raise Ad5248Error("setting value out of range 0~255")
    self._interface.wr_rd(self._slave, [self._port << 7, byte])

  def _set_resistance_value(self, value):
    """Sets real output resistance value of ad5248.

    Since ad5248 is digital, there are only 256 steps of resistance value
    supported. This function will find the step which is most closed to and
    lower than the given value.

    Args:
      value: an integer of proposed output resistance value.
    """
    full_resistance = FULL_RESISTANCE_SPEC[self._subtype]
    # Rwb(max) = full resistance - 1 LSB + 2 * wiper resistance
    lsb_value = full_resistance / 256
    max_value = full_resistance + 2 * WIPER_RESISTANCE - lsb_value
    if not 0 <= value <= max_value:
      raise Ad5248Error("setting value out of range 0~%d" % max_value)
    if value <= 2 * WIPER_RESISTANCE:
      write_byte = 0
    else:
      write_byte = (value - 2 * WIPER_RESISTANCE) * 256 / full_resistance
    self._set_rdac(write_byte)

  def _get_rdac(self):
    """Gets RDAC register value of ad5248.

    Returns:
      byte: 8-bit value as integer.
    """
    values = self._interface.wr_rd(self._slave, [self._port << 7], 1)
    return values[0]

  def _get_resistance_value(self):
    """Gets real output resistance value of ad5248.

    Returns:
      resistance: output resistance value by Ohm.
    """
    rdac_value = self._get_rdac()
    full_resistance = FULL_RESISTANCE_SPEC[self._subtype]
    return rdac_value * full_resistance / 256 + 2 * WIPER_RESISTANCE

  def _Set_rdac(self, byte):
    self._set_rdac(byte)

  def _Set_r2p5k(self, value):
    self._set_resistance_value(value)

  def _Set_r10k(self, value):
    self._set_resistance_value(value)

  def _Set_r50k(self, value):
    self._set_resistance_value(value)

  def _Set_r100k(self, value):
    self._set_resistance_value(value)

  def _Get_rdac(self):
    return self._get_rdac()

  def _Get_r2p5k(self):
    return self._get_resistance_value()

  def _Get_r10k(self):
    return self._get_resistance_value()

  def _Get_r50k(self):
    return self._get_resistance_value()

  def _Get_r100k(self):
    return self._get_resistance_value()
