# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# MTK OAK board sense resistors feed INA219s on the board.
# The INAs are attached to servos remote I2C bus.
#

# power_total
#  5v_out
#  3v3_out
#  dvfs1
#  gpu
#  core
#  dvfs2
#  pmic
#  dram
#  sram15
#  panelled
#  panel_3v3
#  sram7
#  wifi_3v3
#  ec_3v3
#  ac_power

inas = [(0x40, 'battery', 6, 0.01, 'rem', True),
        (0x41, '5v_out', 5, 0.01, 'rem', True),
        (0x42, '3v3_out', 3.3, 0.01, 'rem', True),
        (0x43, 'dvfs1', 5, 0.01, 'rem', True),
        (0x44, 'gpu', 5, 0.1, 'rem', True),
        (0x45, 'core', 5, 0.1, 'rem', True),
        (0x46, 'dvfs2', 5, 0.1, 'rem', True),
        (0x47, 'pmic', 5, 0.01, 'rem', True),
        (0x48, 'dram', 5, 0.1, 'rem', True),
        (0x49, 'sram15', 5, 0.1, 'rem', True),
        (0x4A, 'panelled', 11.1, 0.1, 'rem', True),
        (0x4B, 'panel_3v3', 3.3, 0.1, 'rem', True),
        (0x4C, 'sram7', 5, 0.1, 'rem', True),
        (0x4D, 'wifi_3v3', 3.3, 0.1, 'rem', True),
        (0x4E, 'ec_3v3', 3.3, 0.1, 'rem', True),
        (0x4F, 'ac_power', 3.3, 0.01, 'rem', True)]
