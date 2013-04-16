# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls pca95xx.

Either:
   tca6416 compatible:
     PCA9534 -- 4bit GPIO expander
     PCA9537 -- 8bit GPIO expander
   pca9500 compatible:
     PCA9500 -- 8bit GPIO expander + EEPROM
"""
import pca9500
import pca9537

def pca95xx(interface, params):
  """Method to determine real driver object to instantiate.

  Returns:
    pca95xx instance that has inherited from either pc9500 or pca9537 driver.
  """

  def determine_device(interface, slave):
    """Determine which i2c device is present.

    There are number of these I2c->GPIO expanders that all share similar
    functionality and unfortunately slave addresses.  Two such are the pca9500
    (NXP) and pca953x (TI) devices.  They don't have any ID registers to
    formally distiguish them but the pca9500 does have an EEPROM at + 0x30 from
    the base slave address which serves as a reasonable identifier.

    TODO(crbug.com/233747): In case of I2c interface via ftdi (libftdii2c.so)
    there is no simple way inside python to disable stdout if it is being
    printed from libc.  For that reason, when pca9537 device is encountered
    you'll see the following benign error during hwinit:
      -E- :: Slave 0x56 failed wr_rd with fic->error:0 err:2

    Returns:
      driver object pca9500 if EEPROM identified else pca9537.
    """
    eeprom_slave = 0x30 + slave

    try:
      interface.wr_rd(eeprom_slave, [], 1)
      base = pca9500.pca9500
    except Exception:
      base = pca9537.pca9537

    return base

  slave = int(params['slv'], 0)
  base = determine_device(interface, slave)

  return base(interface, params)
