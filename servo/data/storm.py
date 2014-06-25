# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
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
inas = [(0x40,'pp12000', 12.0, 0.013, 'rem dut_adc_mux:bank0', True),
        (0x41,'pp5000', 5.0, 0.01, 'rem dut_adc_mux:bank0', True),
        (0x42,'pp1250', 1.25, .05, 'rem dut_adc_mux:bank0', True),
        (0x43,'pp3300', 3.3, .013, 'rem dut_adc_mux:bank0', True),
        (0x44,'pp1050_cx', 1.05, .01, 'rem dut_adc_mux:bank0', True),
        (0x45,'pp1050_apc0', 1.05, .01, 'rem dut_adc_mux:bank0', True),
        (0x46,'pp1050_apc1', 1.05, .01, 'rem dut_adc_mux:bank0', True),
        (0x47,'pp1800', 1.8, .02, 'rem dut_adc_mux:bank0', True),
        (0x48,'pp1200_s17', 1.2, .02, 'rem dut_adc_mux:bank0', True),
        (0x49,'pp1350', 1.35, .02, 'rem dut_adc_mux:bank0', True),
        (0x4a,'pp2500', 2.5, .05, 'rem dut_adc_mux:bank0', True),
        (0x4b,'pp5000_sata', 5.0, .013, 'rem dut_adc_mux:bank0', True),
        (0x4c,'pp4200_2g', 4.2, .013, 'rem dut_adc_mux:bank0', True),
        (0x4d,'pp3300_2g', 3.3, .020, 'rem dut_adc_mux:bank0', True),
        (0x4e,'pp4200_5g', 4.2, .01, 'rem dut_adc_mux:bank0', True),
        (0x4f,'pp3300_5g', 3.3, .020, 'rem dut_adc_mux:bank0', True),
        (0x40,'pp3300_aux', 3.3, .020, 'rem dut_adc_mux:bank1', True),
        (0x41,'pp12000_sata', 12.0, .02, 'rem dut_adc_mux:bank1', True),
        (0x42,'pp3300_6lo_fem', 3.3, 0.2, 'rem dut_adc_mux:bank1', True),
        (0x43,'pp_spare', 99, 0.01, 'rem dut_adc_mux:bank1', True)]
