# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
inas = [
        (0x40, 'pp1050_pch_sus', 1.05, 0.05, 'rem', True), # A0: GND, A1: GND
        (0x41, 'pp3300_lte', 3.3, 0.01, 'rem', True),      # A0: Vs+, A1: GND
        (0x42, 'pp1800_codec', 1.8, 0.1, 'rem', True),     # A0: SDA, A1: GND
        (0x43, 'pp3300_pch', 3.3, 0.1, 'rem', True),       # A0: SCL, A1: GND
        (0x44, 'pp1050_pch', 1.05, 0.02, 'rem', True),     # A0: GND, A1: Vs+
        (0x45, 'pp1200_ddr', 1.2, 0.02, 'rem', True),      # A0: Vs+, A1: Vs+
        (0x46, 'pp3300_ssd', 3.3, 0.1, 'rem', True),       # A0: SDA, A1: Vs+
        (0x47, 'pp3300_pch_sus', 3.3, 0.1, 'rem', True),   # A0: SCL, A1: Vs+
        (0x48, 'pp1050_vccst', 1.05, 0.05, 'rem', True),   # A0: GND, A1: SDA
        (0x49, 'pp1200_cpu', 1.2, 0.03, 'rem', True),      # A0: Vs+, A1: SDA
        (0x4A, 'pp3300_lcd', 3.3, 0.02, 'rem', True),      # A0: SDA, A1: SDA
        (0x4B, 'pp3300_dsw_gated', 3.3, 0.1, 'rem', True), # A0: SCL, A1: SDA
        (0x4C, 'pp1050_modphy', 1.05, 0.02, 'rem', True),  # A0: GND, A1: SCL
        (0x4D, 'pp1200_ldoin', 1.2, 0.015, 'rem', True),   # A0: Vs+, A1: SCL
        (0x4E, 'pp3300_wlan', 3.3, 0.05, 'rem', True),     # A0: SDA, A1: SCL
        (0x4F, 'pp5000', 5.0, 0.01, 'rem', True),          # A0: SCL, A1: SCL
       ]

