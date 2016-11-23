# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# These devices are ina3221 (3-channels/i2c address) devices
inas = [('0x40:0', 'pp975_io',        7.6, 0.100, 'rem', True),
        ('0x40:1', 'spare1',          0.0, 0.001, 'rem', False),
        ('0x40:2', 'pp3300_dsw_ec',   3.3, 0.100, 'rem', True),
        ('0x41:0', 'pp3300_dx_edp',   3.3, 0.100, 'rem', True),
        ('0x41:1', 'pp3300_dsw',      3.3, 0.100, 'rem', True),
        ('0x41:2', 'pp5000_a',        7.6, 0.001, 'rem', False),
        ('0x42:0', 'pp1800_a',        7.6, 0.100, 'rem', True),
        ('0x42:1', 'pp1200_vddq',     7.6, 0.100, 'rem', True),
        ('0x42:2', 'pp850_prim_core', 7.6, 0.100, 'rem', True),
        ('0x43:0', 'pp1000_a',        7.6, 0.100, 'rem', True),
        ('0x43:1', 'pp3000_a',        7.6, 0.100, 'rem', True),
        ('0x43:2', 'pp1800_u_dram',   7.6, 0.100, 'rem', True)]
