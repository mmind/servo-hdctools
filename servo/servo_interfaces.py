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
# ec3po_uart interface 8,9 == usbpd console, ec console.  Applicable to servo v3
# as well.
EC3PO_USBPD_INTERFACE_NUM = 8
EC3PO_EC_INTERFACE_NUM = 9
SERVO_V2_DEFAULTS = [(0x18d1, 0x5002)]
for vid, pid in SERVO_V2_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = \
    ['dummy', 'ftdi_i2c', 'ftdi_uart', 'ftdi_uart', 'dummy',
     'dummy', 'ftdi_uart', 'ftdi_uart',
     {'name': 'ec3po_uart'},
     {'name': 'ec3po_uart'}]

# servo v3
SERVO_V3_DEFAULTS = [(0x18d1, 0x5004)]
for vid, pid in SERVO_V3_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = \
    ['bb_gpio',
     {'name': 'dev_i2c', 'bus_num': 1},
     {'name': 'bb_uart', 'uart_num': 5,
      'txd': ['lcd_data8', 0x4], 'rxd': ['lcd_data9', 0x4]},
     {'name': 'dev_i2c', 'bus_num': 2},
     'bb_adc',
     'dummy',
     {'name': 'bb_uart', 'uart_num': 1},
     {'name': 'bb_uart', 'uart_num': 2},
     {'name': 'ec3po_uart'},
     {'name': 'ec3po_uart'},
     {'name': 'bb_uart', 'uart_num': 4}]

INTERFACE_DEFAULTS[0x0403][0x6014] = INTERFACE_DEFAULTS[0x18d1][0x5004]

# miniservo
MINISERVO_ID_DEFAULTS = [(0x403, 0x6001), (0x18d1, 0x5000)]
for vid, pid in MINISERVO_ID_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = ['ftdi_gpiouart', {'name': 'ec3po_uart'}]

SERVO_ID_DEFAULTS.extend(MINISERVO_ID_DEFAULTS)

# Toad
TOAD_ID_DEFAULTS = [(0x403, 0x6015)]
for vid, pid in TOAD_ID_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = ['ftdi_gpiouart', {'name': 'ec3po_uart'}]

SERVO_ID_DEFAULTS.extend(TOAD_ID_DEFAULTS)

# Reston
RESTON_ID_DEFAULTS = [(0x18d1, 0x5007)]
for vid, pid in RESTON_ID_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = ['ftdi_gpiouart', {'name': 'ec3po_uart'}]

SERVO_ID_DEFAULTS.extend(RESTON_ID_DEFAULTS)

# Fruitpie
FRUITPIE_ID_DEFAULTS = [(0x18d1, 0x5009)]
for vid, pid in FRUITPIE_ID_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = ['ftdi_gpiouart', {'name': 'ec3po_uart'}]

SERVO_ID_DEFAULTS.extend(FRUITPIE_ID_DEFAULTS)

# Plankton
PLANKTON_ID_DEFAULTS = [(0x18d1, 0x500c)]
for vid, pid in PLANKTON_ID_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = ['ftdi_gpiouart', {'name': 'ec3po_uart'}]

SERVO_ID_DEFAULTS.extend(PLANKTON_ID_DEFAULTS)

# Allow Board overrides of interfaces as we've started to overload some servo V2
# pinout functionality.  To-date just swapping EC SPI interface for USB PD MCU
# UART
# TODO(tbroch) See about availability of extra uart on Servo V3/beaglebone
INTERFACE_BOARDS = collections.defaultdict(
    lambda: collections.defaultdict(dict))
# samus re-purposes EC SPI to be USB PD UART
INTERFACE_BOARDS['samus'][0x18d1][0x5002] = \
    list(INTERFACE_DEFAULTS[0x18d1][0x5002])
INTERFACE_BOARDS['samus'][0x18d1][0x5002][5] = 'ftdi_uart'
# oak re-purposes EC SPI to be USB PD UART
INTERFACE_BOARDS['oak'][0x18d1][0x5002] = \
    list(INTERFACE_DEFAULTS[0x18d1][0x5002])
INTERFACE_BOARDS['oak'][0x18d1][0x5002][5] = 'ftdi_uart'
# strago re-purposes JTAG to be UART
INTERFACE_BOARDS['strago'][0x18d1][0x5002] = \
    list(INTERFACE_DEFAULTS[0x18d1][0x5002])
INTERFACE_BOARDS['strago'][0x18d1][0x5002][0] = 'ftdi_uart'

# Skylake boards re-purpose JTAG to be UART
INTERFACE_BOARDS['chell'][0x18d1][0x5002] = \
    list(INTERFACE_DEFAULTS[0x18d1][0x5002])
INTERFACE_BOARDS['chell'][0x18d1][0x5002][0] = 'ftdi_uart'
INTERFACE_BOARDS['glados'][0x18d1][0x5002] = \
    list(INTERFACE_DEFAULTS[0x18d1][0x5002])
INTERFACE_BOARDS['glados'][0x18d1][0x5002][0] = 'ftdi_uart'
INTERFACE_BOARDS['kunimitsu'][0x18d1][0x5002] = \
    list(INTERFACE_DEFAULTS[0x18d1][0x5002])
INTERFACE_BOARDS['kunimitsu'][0x18d1][0x5002][0] = 'ftdi_uart'
INTERFACE_BOARDS['lars'][0x18d1][0x5002] = \
    list(INTERFACE_DEFAULTS[0x18d1][0x5002])
INTERFACE_BOARDS['lars'][0x18d1][0x5002][0] = 'ftdi_uart'
