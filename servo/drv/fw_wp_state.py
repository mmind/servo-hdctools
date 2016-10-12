# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hw_driver


class FwWpStateDriver(hw_driver.HwDriver):
  """Abstract superclass to provide board-specific WP operations.

  This driver handles a single control with these settings:
    * 'force_on' - Force to turn on firmware write-protection.
    * 'force_off' - Force to turn off firmware write-protection.
    * 'reset' - For setter, reset the value to the system one.
    * 'on' - For getter, the system value is write-protected.
    * 'off' - For getter, the system value is not write-protected.

  Actual implementation of the required behaviors is delegated to
  the methods `_force_on()`, `_force_off()`, `_reset()`, and
  `_get_state()`, which must be implemented in a subclass.

  """

  _STATE_FORCE_ON = 'force_on'
  _STATE_FORCE_OFF = 'force_off'
  _STATE_RESET = 'reset'
  _STATE_ON = 'on'
  _STATE_OFF = 'off'

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: driver interface object
      params: dictionary of params
    """
    super(FwWpStateDriver, self).__init__(interface, params)

  def _force_on(self):
    """Force the firmware to write-protected."""
    raise NotImplementedError()

  def _force_off(self):
    """Force the firmware to not write-protected."""
    raise NotImplementedError()

  def _reset(self):
    """Reset the firmware write-protection state to the system value."""
    raise NotImplementedError()

  def _get_state(self):
    """Get the firmware write-protection state."""
    raise NotImplementedError()

  def set(self, statename):
    """Set firmware write-protection state according to `statename`."""
    if statename == self._STATE_FORCE_ON:
      self._force_on()
    elif statename == self._STATE_FORCE_OFF:
      self._force_off()
    elif statename == self._STATE_RESET:
      self._reset()
    else:
      raise ValueError("Invalid fw_wp_state setting: '%s'. Try one of "
                       "'%s', '%s', or '%s'." % (statename,
                           self._FORCE_ON, self._FORCE_OFF, self._RESET))

  def get(self):
    """Get firmware write-protection state."""
    return self._get_state()
