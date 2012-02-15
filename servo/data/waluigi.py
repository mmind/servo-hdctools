# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
inline = """
  <map>
    <name>dut_adc_mux</name>
    <doc>valid mux values for DUT's two banks of INA219
    ADCs</doc>
    <params bank0="1" bank1="2"></params>
  </map>
  <control>
    <name>dut_adc_mux</name>
    <doc>4 to 1 mux to steer remote i2c i2c_mux:rem to two sets of
    16 INA219 ADCs. Note they are only on leg0 and leg1</doc>
    <params interface="2" drv="pca9546" slv="0x70"
    map="dut_adc_mux"></params>
  </control>
"""

inas = [(0x40, 'ppvar_vbat', 19.6, 0.03, 'rem dut_adc_mux:bank0', True),
        (0x41, 'pp5000', 5, 0.01, 'rem dut_adc_mux:bank0', True),
        (0x42, 'pp3300', 3.3, 0.01, 'rem dut_adc_mux:bank0', True),
        (0x43, 'nc1', 999, 0, 'rem dut_adc_mux:bank0', False),
        (0x44, 'vmem', 1.35, 0.01, 'rem dut_adc_mux:bank0', True),
        (0x45, 'vddcore', 1, 0.01, 'rem dut_adc_mux:bank0', True),
        (0x46, 'vddcpu', 1, 0.001, 'rem dut_adc_mux:bank0', True),
        (0x47, 'pp1500', 1.5, 0.01, 'rem dut_adc_mux:bank0', True),
        (0x48, 'pp1350_cpu', 1.35, 0, 'rem dut_adc_mux:bank0', False),
        (0x49, 'pp1350_dram', 1.35, 0.05, 'rem dut_adc_mux:bank0', True),
        (0x4a, 'ppvar_bl', 14, 0.1, 'rem dut_adc_mux:bank0', True),
        (0x4b, 'pp3300_lcd', 3.3, 0.1, 'rem dut_adc_mux:bank0', True),
        (0x4c, 'pp3300_wwan', 3.3, 0.01, 'rem dut_adc_mux:bank0', True),
        (0x4d, 'pp1800_wlan', 1.8, 0.1, 'rem dut_adc_mux:bank0', True),
        (0x4e, 'pp3300_wlan', 3.3, 0.1, 'rem dut_adc_mux:bank0', True),
        (0x4f, 'pp3300_lvds', 3.3, 0.1, 'rem dut_adc_mux:bank0', True),
        (0x40, 'pp1800', 1.8, 0.01, 'rem dut_adc_mux:bank1', True),
        (0x41, 'pp1800_t30', 1.8, 0.05, 'rem dut_adc_mux:bank1', True),
        (0x42, 'pp3300_t30', 3.3, 0.05, 'rem dut_adc_mux:bank1', True),
        (0x43, 'pp3300_satacon', 3.3, 0.01, 'rem dut_adc_mux:bank1', True),
        (0x44, 'pp3300_emmc', 3.3, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x45, 'pp3300_gyro', 3.3, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x46, 'pp3300_tpm', 3.3, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x47, 'pp1800_codec', 1.8, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x48, 'pp5000_audio', 5, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x49, 'pp1200_ldo6', 1.2, 0.2, 'rem dut_adc_mux:bank1', True),
        (0x4a, 'pp1050_ldo1', 1.05, 0.2, 'rem dut_adc_mux:bank1', True),
        (0x4b, 'pp1100_ldo7', 1.1, 0.2, 'rem dut_adc_mux:bank1', True),
        (0x4c, 'pp1000_ldo8', 1, 0.2, 'rem dut_adc_mux:bank1', True),
        (0x4d, 'pp3300_always', 3.3, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x4e, 'pp5000_always', 5, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x4f, 'nc2', 999, 0, 'rem dut_adc_mux:bank1', False)]
