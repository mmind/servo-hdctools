# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
"""
import drv.hw_driver


CMD_MASK = 0xf

class Pca9546Error(Exception):
  """Error class for PCA9546"""


class pca9546(drv.hw_driver.HwDriver):
  """Object to access drv=pca9546 controls."""
  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: interface object to handle low-level communication to control
      params: dictionary of params needed to perform operations on pca9546
          devices.

    Mandatory Params:
      slv: integer, 7-bit i2c slave address
    """
    super(pca9546, self).__init__(interface, params)
    self._logger.debug("")
    self._slave = int(self._params['slv'], 0)

  def get(self):
    """Get PCA9546 mux.
    """
    return self._interface.wr_rd(self._slave, [], 1)[0]

  def set(self, value):
    """Set PCA954 mux.

    Args:
      value: 4-bit unsigned integer to set mux output

    Raises:
      Pca9546Error: if value is out of bounds
    """
    self._logger.debug("value = %s" % str(value))
    if value & ~CMD_MASK:
      raise Pca9546Error("command value 0x%x can't be greater than 0x%x" %
                         (value, CMD_MASK))
    self._interface.wr_rd(self._slave, [CMD_MASK & value], 0)
