# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
inas = [(0x40, 'ppvar_vbat', 12, 0.01, 'loc0', True),
        (0x41, 'pp5000', 5, 0.01, 'loc0', True),
        (0x42, 'pp3300', 3.3, 0.01, 'loc0', True),
        (0x43, 'pp1350_ddr', 3.3, 0.01, 'loc0', True),
        (0x45, 'ap_arm', 1, 0.01, 'loc0', True),
        (0x46, 'ap_g3d', 1, 0.01, 'loc0', True),
        (0x47, 'ap_int', 1, 0.01, 'loc0', True),
        (0x48, 'ap_mif', 1, 0.1, 'loc0', True),
        (0x49, 'pp1800', 1.8, 0.1, 'loc0', True),
        (0x4a, '1350_ldoin', 1.35, 0.1, 'loc0', True),
        (0x4b, '2000_ldoin', 2, 0.1, 'loc0', True),
        (0x4c, 'emmc', 2.85, 0.1, 'loc0', True),
        (0x4e, 'wlan_3v3', 3.3, 0.1, 'loc0', True),
        (0x4d, 'ppvar_ac', 12, 0.012, 'loc0', True),
        (0x4f, 'wlan_1v8', 1.8, 0.1, 'loc0', True),
        ]
