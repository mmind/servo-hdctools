# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import fw_wp_state


class fwWpServoflex(fw_wp_state.FwWpStateDriver):
  """Driver for fw_wp_state for boards connecting servoflex's."""

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: driver interface object
      params: dictionary of params
    """
    super(fwWpServoflex, self).__init__(interface, params)
    self._fw_wp_vref = self._params.get('fw_wp_vref', 'pp1800')

  def _force_on(self):
    """Force the firmware to write-protected."""
    self._interface.set('fw_wp_vref', self._fw_wp_vref)
    self._interface.set('fw_wp_en', 'on')
    self._interface.set('fw_wp', 'on')

  def _force_off(self):
    """Force the firmware to not write-protected."""
    self._interface.set('fw_wp_vref', self._fw_wp_vref)
    self._interface.set('fw_wp_en', 'on')
    self._interface.set('fw_wp', 'off')

  def _reset(self):
    """Reset the firmware write-protection state to the system value."""
    self._interface.set('fw_wp_en', 'off')

  def _get_state(self):
    """Get the firmware write-protection state."""
    fw_wp_en = (self._interface.get('fw_wp_en') == 'on')
    fw_wp = (self._interface.get('fw_wp') == 'on')
    if fw_wp_en:
      return self._STATE_FORCE_ON if fw_wp else self._STATE_FORCE_OFF
    else:
      return self._STATE_ON if fw_wp else self._STATE_OFF
