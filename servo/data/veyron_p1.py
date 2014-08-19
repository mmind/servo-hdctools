# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
inas = [
        (0x40, 'batt', 7.6, 0.01, 'rem', True), # A0: GND, A1: GND
        (0x41, 'vcc_5v', 5.0, 0.01, 'rem', True),      # A0: Vs+, A1: GND
        (0x42, 'vcc_33v', 3.3, 0.01, 'rem', True),     # A0: SDA, A1: GND
        (0x43, 'vdd_gpu', 1.0, 0.01, 'rem', True),       # A0: SCL, A1: GND
        (0x44, 'vcc_18v', 1.8, 0.01, 'rem', True),     # A0: GND, A1: Vs+
        (0x45, 'vdd_cpu', 1.0, 0.01, 'rem', True),      # A0: Vs+, A1: Vs+
        (0x46, 'vdd_log', 1.0, 0.01, 'rem', True),       # A0: SDA, A1: Vs+
        (0x47, 'vcc_sys', 3.8, 0.01, 'rem', True),   # A0: SCL, A1: Vs+
        (0x48, 'vcc_flash', 2.0, 0.01, 'rem', True),   # A0: GND, A1: SDA
        (0x49, 'vcc_ddr', 1.35, 0.01, 'rem', True),      # A0: Vs+, A1: SDA
        (0x4A, 'vcc_led', 12.0, 0.01, 'rem', True),      # A0: SDA, A1: SDA
        (0x4B, 'vcc_ec', 3.3, 0.01, 'rem', True), # A0: SCL, A1: SDA
        (0x4C, 'vcc_20v', 2.0, 0.01, 'rem', True),  # A0: GND, A1: SCL
        (0x4D, 'vcc_wifi', 1.8, 0.01, 'rem', True),   # A0: Vs+, A1: SCL
        (0x4E, 'vcc_sd', 3.3, 0.01, 'rem', True),     # A0: SDA, A1: SCL
        (0x4F, 'vcc_codec', 1.8, 0.01, 'rem', True),          # A0: SCL, A1: SCL
       ]

