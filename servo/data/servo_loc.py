# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
inline = """
  <map>
    <name>adc_mux</name>
    <doc>valid mux values for DUT's two banks of INA219 off PCA9540
    ADCs</doc>
    <params none="0" bank0="4" bank1="5"></params>
  </map>
  <control>
    <name>adc_mux</name>
    <doc>4 to 1 mux to steer remote i2c i2c_mux:rem to two sets of
    16 INA219 ADCs. Note they are only on leg0 and leg1</doc>
    <params interface="2" drv="pca9546" slv="0x70"
    map="adc_mux"></params>
  </control>
"""

inas = [(0x40, 'loc_0x40', 19.5, 0.030, "loc0", False),
        (0x41, 'loc_0x41', 5.0,  0.010, "loc0", False),
        (0x42, 'loc_0x42', 3.3,  0.010, "loc0", False),
        (0x43, 'loc_0x43', 1.05, 0.030, "loc0", False),
        (0x44, 'loc_0x44', 1.8,  0.010, "loc0", False),
        (0x45, 'loc_0x45', 1.5,  0.010, "loc0", False),
        (0x46, 'loc_0x46', 1.5,  0.010, "loc0", False),
        (0x47, 'loc_0x47', 4.5,  0.010, "loc0", False),
        (0x48, 'loc_0x48', 1.8,  0.010, "loc0", False),
        (0x49, 'loc_0x49', 1.8,  0.100, "loc0", False),
        (0x4a, 'loc_0x4a', 19.5, 0.100, "loc0", False),
        (0x4b, 'loc_0x4b', 3.3,  0.100, "loc0", False),
        (0x4c, 'loc_0x4c', 3.3,  0.010, "loc0", False),
        (0x4d, 'loc_0x4d', 1.8,  0.100, "loc0", False),
        (0x4e, 'loc_0x4e', 3.3,  0.100, "loc0", False),
        (0x4f, 'loc_0x4f', 3.3,  0.100, "loc0", False),
        (0x4e, 'usb_load_dhub', 5.0,  0.050, "loc1", True),
        (0x4f, 'usb_load_din', 5.0,  0.050, "loc1", True)]
