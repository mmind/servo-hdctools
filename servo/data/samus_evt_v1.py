# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

inas = [
        (0x40, 'pp1050_vccusb3pll', 1.05, 0.100, "loc0", True),   # L20 1 & 3
        (0x41, 'pp1050_vccsata3pll', 1.05,  0.100, "loc0", True), # L21 2 & 4
        (0x42, 'pp1050_vccclk', 1.05, 0.100, "loc0", True),       # L18 6 & 8
        (0x43, 'pp1050_vccaclkpll', 1.05,  0.100, "loc0", True),  # L19 7 & 9
        (0x44, 'pp1200_ssd', 1.2,  0.015, "loc0", True),      # R18 11 & 13
        (0x45, 'pp1800_ddr', 1.8,  0.010, "loc0", True),      # R437 12 & 14
        (0x46, 'pp1800_ssd', 1.8,  0.100, "loc0", True),      # R456 16 & 18
        (0x47, 'pp3300_rtc', 3.3,  0.010, "loc0", True),      # R500 17 & 19
        (0x48, 'pp3300_autobahn', 3.3,  0.100, "loc0", True), # R32 21 & 23
        (0x49, 'pp3300_sd', 3.3,  0.100, "loc0", True),       # R470 22 & 24
        (0x4a, 'pp3300_dsw', 3.3, 0.100, "loc0", True),       # R475 26 & 28
        (0x4b, 'pp3300_mcu', 3.3,  0.100, "loc0", True),      # R342 27 & 29
        (0x4c, 'pp1200_ldoin', 1.2,  0.015, "loc0", True),    # R224 31 & 33
        (0x4d, 'pp5000_usb', 5.0,  0.010, "loc0", True),      # R272 34 & 32
        (0x4e, 'vbat', 9.0,  0.005, "loc0", True),            # R451 38 & 36
        (0x4f, 'pp3300_usb_pd', 3.3, 0.100, "loc0", True),    # R493 37 & 39
      ]
