# Copyright 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Allows creation of ADC interface for beaglebone devices."""
import glob
import os


class BBadcError(Exception):
  """Class for exceptions of BBadc."""

  def __init__(self, msg, value=0):
    """BBadc constructor.

    Args:
      msg: string, message describing error in detail
      value: integer, value of error when non-zero status returned.  Default=0
    """
    super(BBAdcError, self).__init__(msg, value)
    self.msg = msg
    self.value = value


class BBadc(object):
  """Provides interface to ADC through beaglebone."""

  ADC_ENABLE_COMMAND = 'echo cape-bone-iio > %s'
  ADC_ENABLE_NODE = '/sys/devices/bone_capemgr.*/slots'
  ADC_IN_NODE = '/sys/devices/ocp.*/helper.*/AIN*'

  def __init__(self):
    """Enables ADC drvier."""
    adc_nodes = glob.glob(BBadc.ADC_ENABLE_NODE)
    for adc_node in adc_nodes:
      os.system(BBadc.ADC_ENABLE_COMMAND % adc_node)

  def read(self):
    """Reads ADC values.

    Returns:
      ADC inputs from AIN0 to AIN7.
    """
    buffer = []
    adc_in_nodes = glob.glob(BBadc.ADC_IN_NODE)
    for adc_in in adc_in_nodes:
      with open(adc_in, 'r') as f:
        buffer.append(int(f.read(), 10))

    return buffer
