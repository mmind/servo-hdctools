# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Specific Servo PostInit functions."""

import collections
import logging
import os
import re
import subprocess
import usb

import servo_interfaces
import system_config


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
  USB_SYSFS_PATH = '/sys/bus/usb/devices'
  CHILD_RE = re.compile(r'\d+-\d+(\.\d+){1,}\Z')
  BUS_FILE = 'busnum'
  DEV_FILE = 'devnum'

  def __init__(self, *args, **dargs):
    super(ServoV4PostInit, self).__init__(*args, **dargs)
    self.servo_micro_devices = None
    self.usb_hierarchy = None

  def get_servo_v4_usb_device(self):
    """Return associated servo v4 usb.core.Device object.

    Returns:
      servo v4 usb.core.Device object associated with the servod instance.
    """
    servo_v4_devices = []
    for vid, pid in servo_interfaces.SERVO_V4_DEFAULTS:
      devs = usb.core.find(idVendor=vid, idProduct=pid, find_all=True)
      if devs:
        servo_v4_devices.extend(devs)
    for d in servo_v4_devices:
      d_serial = usb.util.get_string(d, 256, d.iSerialNumber)
      if (not self.servod._serialnames[self.servod.MAIN_SERIAL] or
          d_serial == self.servod._serialnames[self.servod.MAIN_SERIAL]):
        return d
    return None

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

  def _get_usb_hierarchy(self):
    """Walk through usb sysfs files and gather parent identifiers.

    The usb sysfs dir contains dirs of the following format:
    - 1-2
    - 1-2:1.0
    - 1-2.4
    - 1-2.4:1.0

    The naming convention works like so:
      <roothub>-<hub port>[.port[.port]]:config.interface

    We are only going to be concerned with the roothub, hub port and port.
    We are going to create a hierarchy where each device will store the usb
    sysfs path of its roothub and hub port.  We will also grab the device's
    bus and device number to help correlate to a usb.core.Device object.

    We will walk through each dir and only match on device dirs
    (e.g. '1-2.4') and ignore config.interface dirs.  When we get a hit, we'll
    grab the bus/dev and infer the roothub and hub port from the dir name
    ('1-2' from '1-2.4') and store the info into a dict.

    The dict key will be a tuple of (bus, dev) and value be the sysfs path.

    Returns:
      Dict of tuple (bus,dev) to sysfs path.
    """
    if self.usb_hierarchy is not None:
      return self.usb_hierarchy

    self.usb_hierarchy = {}
    for usb_dir in os.listdir(self.USB_SYSFS_PATH):
      bus_file = os.path.join(self.USB_SYSFS_PATH, usb_dir, self.BUS_FILE)
      dev_file = os.path.join(self.USB_SYSFS_PATH, usb_dir, self.DEV_FILE)
      if (self.CHILD_RE.match(usb_dir)
          and os.path.exists(bus_file)
          and os.path.exists(dev_file)):
        parent_arr = usb_dir.split('.')[:-1]
        parent = '.'.join(parent_arr)

        bus = ''
        with open(bus_file, 'r') as bfile:
          bus = bfile.read().strip()

        dev = ''
        with open(dev_file, 'r') as dfile:
          dev = dfile.read().strip()

        self.usb_hierarchy[(bus, dev)] = parent
    return self.usb_hierarchy

  def _get_parent(self, usb_device):
    """Return the parent of the supplied usb_device.

    Args:
      usb_device: usb.core.Device object.

    Returns:
      SysFS path string of parent of the supplied usb device.
    """
    return self._get_usb_hierarchy().get((str(usb_device.bus),
                                          str(usb_device.address)))


  def servo_micro_behind_v4(self, servo_micro):
    """Check if the supplied servo_micro device is behind the servo v4.

    We'll be checking to see if the servo v4 shares the same parent
    as the servo micro.

    Args:
      servo_micro: usb.core.Device object that represents the servo_micro
          we should be checking against.

    Returns:
      True if the servo_micro device is behind the servo v4, False otherwise.
    """
    servo_v4 = self.get_servo_v4_usb_device()

    servo_v4_parent = self._get_parent(servo_v4)
    servo_micro_parent = self._get_parent(servo_micro)
    self._logger.debug('servo v4 parent: %s', servo_v4_parent)
    self._logger.debug('servo micro parent: %s', servo_micro_parent)

    return (servo_v4_parent and servo_micro_parent
            and servo_v4_parent == servo_micro_parent)

  def add_servo_micro_config(self):
    """Add in the servo micro interface.

    We need to recreate a system config so servo_micro controls are properly
    overwritten.  We will recreate the config list but with servo micro
    in front and append the rest of the existing config files loaded
    up.  Duplicates are ok since the SystemConfig object keeps track of that
    for us and will ignore them.
    """
    cfg_files = [self.SERVO_MICRO_CFG]
    cfg_files.extend(
        [os.path.basename(f) for f in self.servod._syscfg._loaded_xml_files])

    self._logger.debug("Resetting system config files")
    new_syscfg = system_config.SystemConfig()
    for cfg_file in cfg_files:
      new_syscfg.add_cfg_file(cfg_file)
    self.servod._syscfg = new_syscfg

  def init_servo_micro(self, servo_micro):
    """Initialize the servo micro interfaces.

    Args:
      servo_micro: usb.core.Device object that represents the servo_micro
          we should be checking against.
    """
    vendor = servo_micro.idVendor
    product = servo_micro.idProduct
    serial = usb.util.get_string(servo_micro, 256, servo_micro.iSerialNumber)
    servo_micro_interface = servo_interfaces.INTERFACE_DEFAULTS[vendor][product]
    self.servod._serialnames['servo_micro'] = serial

    self.servod.init_servo_interfaces(vendor, product, serial,
                                      servo_micro_interface)

  def kick_devices(self):
    """General method to do misc actions.

    We'll need to do certain things (like 'lsusb' for servo micro) to ensure
    we can detect and initialize extra devices properly.  This method is here
    to hold all those necessary pre-postinit actions.
    """
    # Run 'lsusb' so that servo micros are configured and show up in sysfs.
    subprocess.call(['lsusb'])

  def post_init(self):
    self._logger.debug("")

    # Do misc actions so we can detect devices we might want to initialize.
    self.kick_devices()

    # We want to check if we have a servo micro connected to this servo v4
    # and if so, initialize it and add it to the servod instance.
    if self.servo_micro_detected():
      for servo_micro in self.get_servo_micro_devices():
        # We'll assume we have at most one servo micro behind the v4.
        if self.servo_micro_behind_v4(servo_micro):
          self.add_servo_micro_config()
          self.init_servo_micro(servo_micro)
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
