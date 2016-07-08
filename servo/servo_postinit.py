# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Specific Servo PostInit functions."""

import collections
import logging
import usb

import servo_interfaces


POST_INIT = collections.defaultdict(dict)


class BasePostInit(object):
  """Base Class for Post Init classes."""

  def __init__(self, servod):
    self.servod = servod
    self._logger = logging.getLogger(self.__class__.__name__)

  def post_init(self):
    """Main entry to the post init class, must be implemented by subclasses."""
    raise NotImplementedError('post_init not implemented')


class ServoV4PostInit(BasePostInit):
  """Servo v4 Post init class.

  We're going to check if there are any dut interfaces attached and if they are
  connected through the specific servo v4 initialized in the servod object.  If
  so, we're going to initialize the dut interfaces connected to the v4 so that
  the user can control the servo v4 and dut interfaces through one servod
  process.
  """

  SERVO_MICRO_CFG = 'servo_micro.xml'

  def __init__(self, *args, **dargs):
    super(ServoV4PostInit, self).__init__(*args, **dargs)
    self.servo_micro_devices = None

  def get_servo_micro_devices(self):
    """Return all servo micros detected.

    Returns:
      List of servo micro devices as usb.core.Device objects.
    """
    if self.servo_micro_devices is not None:
      return self.servo_micro_devices
    self.servo_micro_devices = []
    for vid, pid in servo_interfaces.SERVO_MICRO_DEFAULTS:
      devs = usb.core.find(idVendor=vid, idProduct=pid, find_all=True)
      if devs:
        self.servo_micro_devices.extend(devs)
    return self.servo_micro_devices

  def servo_micro_detected(self):
    """Check if there are any servo micros.

    Returns:
      True if detected, False otherwise.
    """
    return len(self.get_servo_micro_devices()) > 0

  def servo_micro_behind_v4(self, servo_micro):
    """Check if the supplied servo_micro device is behind the servo v4.

    We'll be checking to see if the port the servo v4 is on is the same port
    as the servo micro.

    Args:
      servo_micro: usb.core.Device object that represents the servo_micro
          we should be checking against.

    Returns:
      True if the servo_micro device is behind the servo v4, False otherwise.
    """
    # TODO(kevcheng): Implement this.
    return True

  def add_servo_micro_config(self):
    """Add in the servo micro interface."""
    self.servod._syscfg.add_cfg_file(self.SERVO_MICRO_CFG)

  def init_servo_micro(self):
    """Initialize the servo micro interfaces.

    We'll override the existing dummy interfaces self.servod._interface_list
    with servo micro interfaces.
    """
    # TODO(kevcheng): refactor out the init stuff to make this clean and then
    # init the servo micro interfaces in the exisiting
    # self.servod._interface_list.
    return

  def post_init(self):
    self._logger.debug("")
    # We want to check if we have a servo micro connected to this servo v4
    # and if so, initialize it and add it to the servod instance.
    if self.servo_micro_detected():
      for servo_micro in self.get_servo_micro_devices():
        # We'll assume we have at most one servo micro behind the v4.
        if self.servo_micro_behind_v4(servo_micro):
          self.add_servo_micro_config()
          self.init_servo_micro()
          return


# Add in servo v4 post init method.
for vid, pid in servo_interfaces.SERVO_V4_DEFAULTS:
  POST_INIT[vid][pid] = ServoV4PostInit

def post_init(servod):
  """Entry point to call post init for a given vid/pid and servod.

  Args:
    servod: servo_server.Servod object.
  """
  post_init_class = POST_INIT.get(servod._vendor, {}).get(servod._product)
  if post_init_class:
    post_init_class(servod).post_init()
