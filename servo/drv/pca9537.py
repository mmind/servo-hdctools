# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls pca9537, a 4-bit ioexpander.
"""
import hw_driver
import tca6416


class pca9537(tca6416.tca6416):
  """Object to access drv=pca9537 controls.

  Note, This gpio expander is compatible to the tca6416 driver.  Only
  difference being it has a single port and consequently different register
  indexes (REG_x below).
  """


  # base indexes of the input, output, polarity and direction registers
  # respectively.
  REG_INP = 0
  REG_OUT = 1
  REG_POL = 2
  REG_DIR = 3


  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: FTDI interface object to handle low-level communication to
          control
      params: dictionary of params needed to perform operations on ina219
          devices.  All items are strings initially but should be cast to types
          detailed below.

    Mandatory Params:
      slv: integer, 7-bit i2c slave address
    Optional Params:
    """
    local_params = params.copy()
    local_params['port'] = '0'
    super(pca9537, self).__init__(interface, local_params)
    self._logger.debug("")
