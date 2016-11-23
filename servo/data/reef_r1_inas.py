# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# These devices are ina3221 (3-channels/i2c address) devices
inas = [('0x40:0', 'pp3300_edp_dx',   3.30,   0.020, 'rem', True), #R367
        ('0x40:1', 'pp3300_a',        3.30,   0.002, 'rem', True), #R422
        ('0x40:2', 'pp1800_a',        1.80,   0.020, 'rem', True), #R416
        #
        ('0x41:0', 'pp1240_a',        1.24,   0.020, 'rem', True), #R417
        ('0x41:1', 'pp1800_dram_u',   1.80,   0.020, 'rem', True), #R403
        ('0x41:2', 'pp1050_s',        1.05,   0.010, 'rem', True), #R412
        #
        ('0x42:0', 'pp3300_pd_a',     3.30,   0.100, 'rem', True), #R384
        ('0x42:1', 'pp3300_wlan_dx',  3.30,   0.020, 'rem', True), #R389
        ('0x42:2', 'pp3300_soc_a',    3.30,   0.020, 'rem', True), #R383
        #
        ('0x43:0', 'pp1100_vddq',     1.10,   0.002, 'rem', True), #R425
        ('0x43:1', 'pp3300_ec',       3.30,   2.200, 'rem', True), #R415
        ('0x43:2', 'pp5000_a',        5.00,   0.002, 'rem', True), #R421
        ]
