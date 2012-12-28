# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of drv=daisy_ec.

Provides the following EC controlled function:
  lid_open
"""
import pty_driver

GPIOC_CRH_ADDR  = 0x40011004
GPIOC_BRR_ADDR  = 0x40011014
GPIOC_BSRR_ADDR = 0x40011010
GPIOC_PC13_MASK = 0x2000

class daisyEcError(Exception):
  """Exception class for daisy ec."""


class daisyEc(pty_driver.ptyDriver):
  """Object to access drv=daisy_ec controls.

  Note, instances of this object get dispatched via base class,
  HwDriver's get/set method. That method ultimately calls:
    "_[GS]et_%s" % params['subtype'] below.

  For example, a control to read lid_open would be dispatched to
  call _Get_lid_open.
  """

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: FTDI interface object to handle low-level communication to
        control
      params: dictionary of params needed to perform operations on
        devices. The only params used now is 'subtype', which is used
        by get/set method of base class to decide how to dispatch
        request.
    """
    super(daisyEc, self).__init__(interface, params)
    self._logger.debug("")
    self._lid_setup = False

  def _setup_lid_control(self):
    """Setup EC to control the lid open/close GPIO.

    The lid GPIO is attached to PC13 of the EC.  To configure it for open-drain
    style output we need to:
    1. Set its configuration (cnf) to General purpose OD. To do that set bits
       <23:22> == 01b
    2. Set its mode to output mode (slow).  To do that set bits
       <21:20> == 11b
    """
    if self._lid_setup:
      return

    # force lid open (PC13) initially before changing the GPIO config
    self._issue_cmd('ww 0x%08x 0x%08x\r' % (GPIOC_BSRR_ADDR, GPIOC_PC13_MASK))

    # reconfigure PC13 to a open-drain output
    cmd = 'rw 0x%08x\r' % GPIOC_CRH_ADDR
    rexp = ['read 0x%08x = (0x.{8})' % GPIOC_CRH_ADDR]
    cur_val = self._issue_cmd_get_results(cmd, rexp)[0][1]
    cur_val = int(cur_val, 0)
    new_val = cur_val & 0xff0fffff | 0x00700000
    self._issue_cmd('ww 0x%08x 0x%08x\r' % (GPIOC_CRH_ADDR, new_val))
    self._lid_setup = True

  def _Set_lid_open(self, value):
    """Setter of lid_open control.

    Args:
      value: 0: lid closed; 1: lid open
    """
    self._setup_lid_control()

    # PC13's BRR register address
    addr = GPIOC_BRR_ADDR
    # PC13's BSRR register address
    if value == 1:
      addr = GPIOC_BSRR_ADDR
    self._issue_cmd('ww 0x%08x 0x%08x\r' % (addr, GPIOC_PC13_MASK))

  def _Get_lid_open(self):
    """Getter of lid_open.

    Returns: integer value with ...
      1: lid is open
      0: lid is closed
    """
    self._setup_lid_control()

    re_match = self._issue_cmd_get_results("gpioget LID_OPEN\r",
                                           ["\s+([01]).*"])[0]
    return int(re_match[1])
