# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
inas = [
        (0x40, 'vcc_5v',  5.0,  0.01, 'rem', True),       # A0: GND, A1: GND
        (0x43, 'vdd_gpu', 1.0,  0.01, 'rem', True),       # A0: SCL, A1: GND
        (0x45, 'vdd_cpu', 1.0,  0.01, 'rem', True),       # A0: Vs+, A1: Vs+
        (0x46, 'vdd_log', 1.0,  0.01, 'rem', True),       # A0: SDA, A1: Vs+
        (0x49, 'vcc_ddr', 1.35, 0.01, 'rem', True),       # A0: Vs+, A1: SDA
        (0x4A, 'vcc_33',  3.3,  0.01, 'rem', True),       # A0: SDA, A1: SDA
       ]

