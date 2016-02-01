# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# MTK OAK board sense resistors feed INA219s on the board.
# The INAs are attached to servos remote I2C bus.

inas = [(0x40, 'battery', 7.4, 0.01, 'rem', True),
        (0x41, '5v_out', 4.2, 0.01, 'rem', True),
        (0x42, '3v3_out', 3.3, 0.01, 'rem', True),
        (0x43, 'dvfs1', 4.2, 0.01, 'rem', True),
        (0x44, 'gpu', 4.2, 0.1, 'rem', True),
        (0x45, 'core', 4.2, 0.1, 'rem', True),
        (0x46, 'dvfs2', 4.2, 0.1, 'rem', True),
        (0x47, 'pmic', 4.2, 0.01, 'rem', True),
        (0x48, 'dram', 4.2, 0.1, 'rem', True),
        (0x49, 'sram15', 4.2, 0.1, 'rem', True),
        (0x4A, 'panelled', 7.4, 0.1, 'rem', True),
        (0x4B, 'panel_3v3', 3.3, 0.1, 'rem', True),
        (0x4C, 'sram7', 4.2, 0.1, 'rem', True),
        (0x4D, 'wifi_3v3', 3.3, 0.1, 'rem', True),
        (0x4E, 'stby_3v3', 3.3, 0.1, 'rem', True),
        (0x4F, 'ac_power', 20, 0.01, 'rem', True)]
