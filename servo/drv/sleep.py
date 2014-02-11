# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for sleep delay pseudo-control.
"""
import time

import hw_driver


class sleep(hw_driver.HwDriver):
  """Simple HwDriver  wrapper around time.sleep()."""

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: driver interface object; ignored.
      params: dictionary of params; ignored.
    """
    super(sleep, self).__init__(interface, params.copy())

  def set(self, seconds):
    """Sleep for the given number of seconds."""
    time.sleep(seconds)
