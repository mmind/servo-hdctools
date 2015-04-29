# Copyright 2015 The Chromium OS Authors. All rights reserved.
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

inas = [(0x40, 'pp3000_always', 3, 1, "loc0", True),
        (0x41, 'pp2800_ec', 3, 1, "loc0", True),
        (0x42, 'pplcd', 3.8, 0.02, "loc0", True),
        (0x43, 'pp1800_lcd', 1.8, 0.02, "loc0", True),
        (0x44, 'pp3300', 3.8, 0.1, "loc0", True),
        (0x46, 'pp3300_wifi', 3.3, 0.1, "loc0", True),
        (0x47, 'pp3300_sensorhub', 3.3, 0.1, "loc0", True),
        (0x48, 'ppvar_sys_pmic', 3.8, 0.005, "loc0", True),
        (0x49, 'pp_vbat', 3.8, 0.02, "loc0", True),
        (0x4A, 'cpu_in', 3.8, 0.01, "loc0", True),
        (0x4B, 'gpu_in', 3.8, 0.01, "loc0", True),
        (0x4C, 'soc_in', 3.8, 0.1, "loc0", True),
        (0x4D, 'pp1800_in', 3.8, 0.1, "loc0", True)]
