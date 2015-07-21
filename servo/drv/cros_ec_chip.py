# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hw_driver


class crosEcChip(hw_driver.HwDriver):
  """Driver for getting EC chip name."""
  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: driver interface object
      params: dictionary of params
    """
    super(crosEcChip, self).__init__(interface, params)
    self._ec_chip = self._params.get('ec_chip', 'unknown')

  def _Get_ec_chip(self):
    """Get the EC chip name."""
    return self._ec_chip
