# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
inline = """
  <map>
    <name>dut_adc_mux</name>
    <doc>valid mux values for DUT's two banks of INA219 ADCs</doc>
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
inas = [(0x40, 'ppvar_vbat', 12, 0.01, 'rem dut_adc_mux:bank0', True),
        (0x41, 'pp5000', 5, 0.01, 'rem dut_adc_mux:bank0', True),
        (0x42, 'pp3300', 3.3, 0.01, 'rem dut_adc_mux:bank0', True),
        (0x43, 'wwan', 3.3, 0.01, 'rem dut_adc_mux:bank0', True),
        (0x44, 'sys_mem', 1.5, 0.01, 'rem dut_adc_mux:bank0', True),
        (0x45, 'ap_arm', 1, 0.01, 'rem dut_adc_mux:bank0', True),
        (0x46, 'ap_g3d', 1, 0.01, 'rem dut_adc_mux:bank0', True),
        (0x47, 'ap_int', 1, 0.01, 'rem dut_adc_mux:bank0', True),
        (0x48, 'ap_mif', 1, 0.1, 'rem dut_adc_mux:bank0', True),
        (0x49, 'pp1800', 1.8, 0.1, 'rem dut_adc_mux:bank0', True),
        (0x4a, '1350_ldoin', 1.35, 0.1, 'rem dut_adc_mux:bank0', True),
        (0x4b, '2000_ldoin', 2, 0.1, 'rem dut_adc_mux:bank0', True),
        (0x4c, 'emmc', 2.85, 0.1, 'rem dut_adc_mux:bank0', True),
        (0x4d, 'spare_1v2', 1.2, 0.1, 'rem dut_adc_mux:bank0', True),
        (0x4e, 'wlan_3v3', 3.3, 0.1, 'rem dut_adc_mux:bank0', True),
        (0x4f, 'wlan_1v8', 1.8, 0.1, 'rem dut_adc_mux:bank0', True),
        (0x40, 'dram', 1.5, 0.01, 'rem dut_adc_mux:bank1', True),
        (0x41, 'back_lite', 12, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x42, 'lcd', 3.3, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x43, 'sata', 3.3, 0.01, 'rem dut_adc_mux:bank1', True),
        (0x44, 'lan', 3.3, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x45, 'gyro', 3.3, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x46, 'tpm', 3.3, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x47, 'codec_1v8', 1.8, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x48, 'codec_5v0', 5, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x49, 'mipib_1v8', 1.8, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x4a, 'mipib_3v3', 3.3, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x4b, 'ap_1v8', 1.8, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x4c, '5v_always', 5, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x4d, '3v_always', 3.3, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x4e, 'hsic_hub', 3.3, 0.1, 'rem dut_adc_mux:bank1', True),
        (0x4f, 'touch_screen', 5, 0.1, 'rem dut_adc_mux:bank1', True)]
