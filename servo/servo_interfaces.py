# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Defines the interfaces for the different servo models."""

import collections

INTERFACE_DEFAULTS = collections.defaultdict(dict)

SERVO_ID_DEFAULTS = [(0x0403, 0x6011), (0x0403, 0x6014), (0x18d1, 0x5001),
                     (0x18d1, 0x5002), (0x18d1, 0x5004), (0x18d1, 0x500f),
                     (0x18d1, 0x5014), (0x18d1, 0x501a), (0x18d1, 0x501b)]

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
    ['ftdi_dummy', 'ftdi_i2c', 'ftdi_uart', 'ftdi_uart', 'ftdi_dummy',
     'ftdi_dummy', 'ftdi_uart', 'ftdi_uart',
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

# Ryu Raiden CCD
RAIDEN_DEFAULTS = [(0x18d1, 0x500f)]
for vid, pid in RAIDEN_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = \
    [{'name': 'stm32_uart', 'interface': 0}, # 1: EC_PD
     {'name': 'stm32_uart', 'interface': 1}, # 2: AP
     'dummy',                                # 3
     'dummy',                                # 4
     'dummy',                                # 5
     'dummy',                                # 6
     'dummy',                                # 7
     'dummy',                                # 8
     'dummy',                                # 9
     {'name': 'ec3po_uart',                  #10: dut ec console
      'raw_pty': 'raw_ec_uart_pty'},
    ]

# cr50 CCD
CCD_DEFAULTS = [(0x18d1, 0x5014)]
for vid, pid in CCD_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = \
    [{'name': 'stm32_uart', 'interface': 2}, # 1: EC_PD
     {'name': 'stm32_i2c', 'interface': 5},  # 2: i2c
     {'name': 'stm32_uart', 'interface': 1}, # 3: AP
     {'name': 'stm32_uart', 'interface': 0}, # 4: cr50 console
     'dummy',                                # 5: HID: intf 1
     'dummy',                                # 6: USB FW: intf 4
     'dummy',                                # 7: SPI: intf 5
     {'name': 'ec3po_uart',                  # 8: cr50 console
      'raw_pty': 'raw_cr50_console_pty'},
     'dummy',                                # 9: dummy
     {'name': 'ec3po_uart',                  #10: dut ec console
      'raw_pty': 'raw_ec_uart_pty'},
    ]

# Servo micro
SERVO_MICRO_DEFAULTS = [(0x18d1, 0x501a)]
for vid, pid in SERVO_MICRO_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = \
    ['dummy',                                # 1:
     {'name': 'stm32_uart', 'interface': 0}, # 2: uart3/legacy
     {'name': 'stm32_uart', 'interface': 3}, # 3: servo console
     {'name': 'stm32_i2c', 'interface': 4},  # 4: i2c
     {'name': 'stm32_uart', 'interface': 5}, # 5: uart2 / dut ap
     {'name': 'stm32_uart', 'interface': 6}, # 6: uart1 / dut ec
     {'name': 'ec3po_uart',                  # 7: servo console
      'raw_pty': 'raw_servo_console_pty'},
     'dummy',                                # 8: dummy
     {'name': 'ec3po_uart',                  # 9: dut pd console
      'raw_pty': 'raw_usbpd_uart_pty'},
     {'name': 'ec3po_uart',                  #10: dut ec console
      'raw_pty': 'raw_ec_uart_pty'},
    ]

# Servo v4
SERVO_V4_DEFAULTS = [(0x18d1, 0x501b)]
for vid, pid in SERVO_V4_DEFAULTS:
  # dummy slots for servo micro use (interface #1-10).
  INTERFACE_DEFAULTS[vid][pid] = ['dummy'] * 10

  # Buffer slots for servo micro (interface #11-20).
  INTERFACE_DEFAULTS[vid][pid] += ['dummy'] * 10

  # Servo v4 interfaces.
  INTERFACE_DEFAULTS[vid][pid] += \
    [{'name': 'stm32_gpio', 'interface': 1}, #21: 32x GPIO block.
     {'name': 'stm32_uart', 'interface': 0}, #22: servo console.
     {'name': 'stm32_i2c', 'interface': 2},  #23: i2c
     {'name': 'stm32_uart', 'interface': 3}, #24: dut sbu uart
     {'name': 'stm32_uart', 'interface': 4}, #25: atmega uart
     {'name': 'ec3po_uart',                  #26: servo v4 console
      'raw_pty': 'raw_servo_v4_console_pty'},
    ]

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
# pinout functionality.  To-date just swapping EC SPI and JTAG interfaces for
# USB PD MCU UART.  Note this can NOT be done on servo V3.  See crbug.com/567842
# for details.
INTERFACE_BOARDS = collections.defaultdict(
    lambda: collections.defaultdict(dict))

# re-purposes EC SPI to be UART for USBPD MCU
for board in ['elm', 'oak', 'samus']:
  INTERFACE_BOARDS[board][0x18d1][0x5002] = \
      list(INTERFACE_DEFAULTS[0x18d1][0x5002])
  INTERFACE_BOARDS[board][0x18d1][0x5002][5] = 'ftdi_uart'

# re-purposes JTAG to be UART for USBPD MCU
for board in ['asuka', 'caroline', 'cave', 'chell', 'glados', 'kunimitsu',
              'lars', 'pbody', 'sentry', 'strago']:
  INTERFACE_BOARDS[board][0x18d1][0x5002] = \
      list(INTERFACE_DEFAULTS[0x18d1][0x5002])
  INTERFACE_BOARDS[board][0x18d1][0x5002][0] = 'ftdi_uart'
