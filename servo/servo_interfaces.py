# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Defines the interfaces for the different servo models."""

import collections

INTERFACE_DEFAULTS = collections.defaultdict(dict)

SERVO_ID_DEFAULTS = [(0x0403, 0x6011), (0x0403, 0x6014), (0x18d1, 0x5001),
                     (0x18d1, 0x5002), (0x18d1, 0x5004)]

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
INTERFACE_DEFAULTS[0x18d1][0x5004] = \
    ['bb_gpio',
     {'name': 'bb_i2c', 'bus_num': 1},
     {'name': 'bb_uart', 'uart_num': 5,
      'txd' : ['lcd_data8', 0x4], 'rxd' : ['lcd_data9', 0x4]},
     {'name': 'bb_i2c', 'bus_num': 2},
     'dummy',
     'dummy',
     {'name': 'bb_uart', 'uart_num': 1},
     {'name': 'bb_uart', 'uart_num': 2}]

INTERFACE_DEFAULTS[0x0403][0x6014] = INTERFACE_DEFAULTS[0x18d1][0x5004]

# miniservo
MINISERVO_ID_DEFAULTS = [(0x403, 0x6001), (0x18d1, 0x5000)]
for vid, pid in MINISERVO_ID_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = ['ftdi_gpiouart']

SERVO_ID_DEFAULTS.extend(MINISERVO_ID_DEFAULTS)

# Toad
TOAD_ID_DEFAULTS = [(0x403, 0x6015)]
for vid, pid in TOAD_ID_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = ['ftdi_gpiouart']

SERVO_ID_DEFAULTS.extend(TOAD_ID_DEFAULTS)

# Reston
RESTON_ID_DEFAULTS = [(0x18d1, 0x5007)]
for vid, pid in RESTON_ID_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = ['ftdi_gpiouart']

SERVO_ID_DEFAULTS.extend(RESTON_ID_DEFAULTS)

# Fruitpie
FRUITPIE_ID_DEFAULTS = [(0x18d1, 0x5009)]
for vid, pid in FRUITPIE_ID_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = ['ftdi_gpiouart']

SERVO_ID_DEFAULTS.extend(FRUITPIE_ID_DEFAULTS)
