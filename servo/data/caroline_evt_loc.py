# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# for use with servo INA adapter board.  If measuring via servo V1 this can just
# be ignored.  clobber_ok added if user wishes to include servo_loc.xml
# additionally.
inline = """
  <map>
    <name>adc_mux</name>
    <doc>valid mux values for DUT's two banks of INA219 off PCA9540
    ADCs</doc>
    <params clobber_ok="" none="0" bank0="4" bank1="5"></params>
  </map>
  <control>
    <name>adc_mux</name>
    <doc>4 to 1 mux to steer remote i2c i2c_mux:rem to two sets of
    16 INA219 ADCs. Note they are only on leg0 and leg1</doc>
    <params clobber_ok="" interface="2" drv="pca9546" slv="0x70"
    map="adc_mux"></params>
  </control>
"""

inas = [(0x40, 'cpu_gt', 1, 0.002, "loc0", True),
        (0x41, 'vbat', 7.6, 0.01, "loc0", True),
        (0x42, 'vdd_lcd', 24, 0.002, "loc0", True),
        (0x43, 'p1.8v_alw', 1.8, 0.1, "loc0", True),
        (0x44, 'p1.8v_mem', 1.8, 0.1, "loc0", True),
        (0x45, 'p1.2v_aux', 1.2, 0.007, "loc0", True),
        (0x46, 'p3.3v_dsw', 3.3, 0.1, "loc0", True),
        (0x47, 'p5.0v_alw', 5, 0.015, "loc0", True),
        (0x48, 'p3.3v_alw', 3.3, 0.018, "loc0", True),
        (0x49, 'p1.0v_alw', 1, 0.018, "loc0", True),
        (0x4A, 'vccio', 0.975, 0.018, "loc0", True),
        (0x4B, 'pch_prim_core', 0.85, 0.015, "loc0", True),
        (0x4C, 'p3.3v_dsw_usbc', 3.3, 0.1, "loc0", True),
        (0x4D, 'p3.3v_dx_edp', 3.3, 0.1, "loc0", True),
        (0x4E, 'cpu_sa', 1, 0.002, "loc0", True),
        (0x4F, 'cpu_la', 1, 0.002, "loc0", True)]

