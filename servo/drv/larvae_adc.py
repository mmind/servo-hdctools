# Copyright 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ADC driver.

It returns Larvae's ADC sensors' value (AIN0 to AIN6).
"""

# servo libs
import hw_driver


class larvaeAdc(hw_driver.HwDriver):
  """Reads ADC inputs."""

  def __init__(self, interface, params):
    """Constructor."""
    super(larvaeAdc, self).__init__(interface, params)

  def get(self):
    """Reads ADC inputs.

    Returns:
      ADC values from AIN0 to AIN6.
    """
    buffer = self._interface.read()
    return buffer[0:7]
