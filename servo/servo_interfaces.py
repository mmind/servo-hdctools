# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Defines the interfaces for the different servo models."""
import collections

INTERFACE_DEFAULTS = collections.defaultdict(dict)

SERVO_ID_DEFAULTS = [(0x0403, 0x6011), (0x18d1, 0x5001), (0x18d1, 0x5002),
                     (0x18d1, 0x5004)]

# servo v1 w/o FT4232h EEPROM programmed
INTERFACE_DEFAULTS[0x0403][0x6011] = ['ftdi_gpio', 'ftdi_i2c',
                                      'ftdi_gpio', 'ftdi_gpio']
# servo v1
INTERFACE_DEFAULTS[0x18d1][0x5001] = ['ftdi_gpio', 'ftdi_i2c',
                                      'ftdi_gpio', 'ftdi_gpio']
# servo V2
# Dummy interface 0 == JTAG via openocd
# Dummy interface 4,5 == SPI via flashrom
INTERFACE_DEFAULTS[0x18d1][0x5002] = \
    ['dummy', 'ftdi_i2c', 'ftdi_uart', 'ftdi_uart', 'dummy',
     'dummy', 'ftdi_uart', 'ftdi_uart']

# servo v3
# Dummy interface 0 == JTAG via openocd
# Dummy interface 4,5 == SPI via flashrom
INTERFACE_DEFAULTS[0x18d1][0x5004] = \
    ['dummy', 'bb_i2c', 'bb_uart', 'bb_uart', 'dummy',
     'dummy', 'bb_uart', 'bb_uart']

# miniservo
MINISERVO_ID_DEFAULTS = [(0x403, 0x6001), (0x18d1, 0x5000)]
for vid, pid in MINISERVO_ID_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = ['ftdi_gpiouart']

SERVO_ID_DEFAULTS.extend(MINISERVO_ID_DEFAULTS)
