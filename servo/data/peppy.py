# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
inas = [
    (0x40, 'Vin', 19.5, 0.1, 'rem', True),           # PR125
    (0x41, 'PP5000', 5, 0.1, 'rem', True),           # JP6
    (0x42, 'PP3300_DSW', 3.3, 0.1, 'rem', True),     # JP4
    (0x43, 'PP3300_PCH', 3.3, 0.1, 'rem', True),     # PR70
    (0x44, 'WL_VDD', 3.3, 0.1, 'rem', True),         # PR64
    (0x45, 'PP3300_DX', 3.3, 0.1, 'rem', True),      # PR46
    (0x46, 'PP3300_PCH_SUS',3.3,0.1,'rem',True),     # PR35
    (0x47, 'PP1050_PCH_SUS',1.05,0.1,'rem',True),    # JP10
    (0x49, 'PP1050_PCH',1.05,0.1,'rem',True),        # JP2
    (0x48, 'PP1500_PCH_TS',1.05,0.1,'rem',True),     # PR157
    (0x4B, 'V1.05DX_MODPHY',1.05,0.1,'rem',True),    # R303,R304
    (0x4A, 'CPU_CPVCCIN',1.8,0.01,'rem',True),       # JP11
    (0x4C, 'PP1350_DDr',1.35 ,0.1,'rem',True),       # JP12
    ]
