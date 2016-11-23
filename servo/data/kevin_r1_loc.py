# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
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
inas = [
        (0x40, 'pp5000',         5.0, 0.01, 'loc', True),
        (0x41, 'ppvar_gpu',      0.9, 0.01, 'loc', True),
        (0x42, 'pp3300_wifi_bt', 3.3, 0.01, 'loc', True),
        (0x43, 'pp1500_ap_io',   1.5, 0.10, 'loc', True),
        (0x44, 'pp3300_alw',     3.3, 0.01, 'loc', True),
        (0x45, 'ppvar_litcpu',   0.9, 0.01, 'loc', True),
        (0x46, 'pp1800_s0',      1.8, 0.05, 'loc', True),
        (0x47, 'ppvar_logic',    0.9, 0.01, 'loc', True),
        (0x48, 'ppvar_bigcpu',   0.9, 0.01, 'loc', True),
        (0x49, 'pp900_ap',       0.9, 0.01, 'loc', True),
        (0x4A, 'pp1800_ec',      1.8, 0.10, 'loc', True),
        (0x4B, 'pp1800_sensor',  1.8, 0.01, 'loc', True),
        (0x4C, 'pp1800_alw',     1.8, 0.05, 'loc', True),
        (0x4D, 'pp1200_lpddr',   1.2, 0.01, 'loc', True),
        (0x4E, 'pp3300_ec',      3.3, 0.10, 'loc', True),
        (0x4F, 'pp3300_s0',      3.3, 0.05, 'loc', True),
       ]

