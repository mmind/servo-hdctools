# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Big
# vdd_mux
#  vdd_lcd_bl
#  5v_sys
#   1.8v_vddio
#    1.8v_vdd_wf
#   1.35v_lp0 (not listed here)
#    vddio_ddr_ap
#    vddio_dram
#   5v_core
#   5v_cpu
#   5v_gpu
#  3.3v_sys
#   3.3v_run (not listed here)
#    3.3v_panel
#    3.3v_usbcam (not listed here)
#   3.3v_lp0 (not listed here)
#    3.3v_vdd_wf
#  5v_stby (not listed here)
#   3.3v_stby

inas = [(0x40, 'vdd_mux', 15.2, 0.20, 'loc0', True),
        (0x41, '5v_sys', 5, 0.1, 'loc0', True),
        (0x42, '3_3v_sys', 3.3, 0.1, 'loc0', True),
        (0x44, '1_8v_vddio', 1.8, 0.02, 'loc0', True),
        (0x45, '5v_core', 5, 0.02, 'loc0', True),
        (0x46, '5v_cpu', 5, 0.02, 'loc0', True),
        (0x48, 'vddio_ddr_ap', 1.35, 0.01, 'loc0', True),
        (0x49, 'vddio_dram', 1.35, 0.01, 'loc0', True),
        (0x4A, 'vdd_lcd_bl', 15.2, 0.02, 'loc0', True),
        (0x4B, '3_3v_panel', 3.3, 0.02, 'loc0', True),
        (0x4C, '5v_gpu', 5, 0.02, 'loc0', True),
        (0x4D, '1_8v_vdd_wf', 1.8, 0.05, 'loc0', True),
        (0x4E, '3_3v_vdd_wf', 3.3, 0.02, 'loc0', True),
        (0x4F, '3_3v_stby', 3.3, 5.0, 'loc0', True)]

