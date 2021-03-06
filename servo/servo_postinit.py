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


class UsbHierarchy(object):
  """A helper class to analyze the sysfs hierarchy of USB devices."""

  USB_SYSFS_PATH = '/sys/bus/usb/devices'
  CHILD_RE = re.compile(r'\d+-\d+(\.\d+){1,}\Z')
  BUS_FILE = 'busnum'
  DEV_FILE = 'devnum'

  def __init__(self):
    # Get the current USB sysfs hierarchy.
    self.refresh_usb_hierarchy()

  def refresh_usb_hierarchy(self):
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
    usb_hierarchy = {}
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

        usb_hierarchy[(bus, dev)] = parent

    self._usb_hierarchy = usb_hierarchy

  def _get_parent_path(self, usb_device):
    """Return the USB sysfs path of the supplied usb_device's parent.

    Args:
      usb_device: usb.core.Device object.

    Returns:
      SysFS path string of parent of the supplied usb device.
    """
    return self._usb_hierarchy.get((str(usb_device.bus),
                                    str(usb_device.address)))

  def share_same_parent(self, usb_device1, usb_device2):
    """Check if the given two USB devices share the same parent.

    Args:
      usb_device1: usb.core.Device object.
      usb_device2: usb.core.Device object.

    Returns:
      True if they share the same parent; otherwise, False.
    """
    usb_parent1 = self._get_parent_path(usb_device1)
    usb_parent2 = self._get_parent_path(usb_device2)
    return (usb_parent1 and usb_parent2
            and usb_parent1 == usb_parent2)


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
  # Only support CR50 CCD.
  CCD_CFG = 'ccd_cr50.xml'

  def _get_all_usb_devices(self, vid_pid_list):
    """Return all associated USB devices which match the given VID/PID's.

    Args:
      vid_pid_list: List of tuple (vid, pid).

    Returns:
      List of usb.core.Device objects.
    """
    all_devices = []
    for vid, pid in vid_pid_list:
      devs = usb.core.find(idVendor=vid, idProduct=pid, find_all=True)
      if devs:
        all_devices.extend(devs)
    return all_devices

  def get_servo_v4_usb_device(self):
    """Return associated servo v4 usb.core.Device object.

    Returns:
      servo v4 usb.core.Device object associated with the servod instance.
    """
    servo_v4_candidates = self._get_all_usb_devices(
        servo_interfaces.SERVO_V4_DEFAULTS)
    for d in servo_v4_candidates:
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
    return self._get_all_usb_devices(servo_interfaces.SERVO_MICRO_DEFAULTS)

  def get_ccd_devices(self):
    """Return all CCD USB devices detected.

    Returns:
      List of CCD USB devices as usb.core.Device objects.
    """
    return self._get_all_usb_devices(servo_interfaces.CCD_DEFAULTS)

  def prepend_config(self, new_cfg_file):
    """Prepend the given new config file to the existing system config.

    The new config, like servo_micro, is properly overwritten by some board
    overlays. So we will recreate the config list but with the new config
    in front and append the rest of the existing config files loaded
    up. Duplicates are ok since the SystemConfig object keeps track of that
    for us and will ignore them.

    Args:
      new_cfg_file: List of config files.
    """
    cfg_files = [new_cfg_file]
    cfg_files.extend(
        [os.path.basename(f) for f in self.servod._syscfg._loaded_xml_files])

    self._logger.debug("Resetting system config files")
    new_syscfg = system_config.SystemConfig()
    for cfg_file in cfg_files:
      new_syscfg.add_cfg_file(cfg_file)
    self.servod._syscfg = new_syscfg

  def add_servo_serial(self, servo_usb, servo_serial_key):
    """Add the servo serial number.

    Args:
      servo_usb: usb.core.Device object that represents the new detected
          servo we should be checking against.
      servo_serial_key: Key to the servo serial dict.
    """
    serial = usb.util.get_string(servo_usb, 256, servo_usb.iSerialNumber)
    self.servod._serialnames[servo_serial_key] = serial

  def init_servo_interfaces(self, servo_usb):
    """Initialize the new servo interfaces.

    Args:
      servo_usb: usb.core.Device object that represents the new detected
          servo we should be checking against.
    """
    vendor = servo_usb.idVendor
    product = servo_usb.idProduct
    serial = usb.util.get_string(servo_usb, 256, servo_usb.iSerialNumber)
    servo_interface = servo_interfaces.INTERFACE_DEFAULTS[vendor][product]

    self.servod.init_servo_interfaces(vendor, product, serial,
                                      servo_interface)

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

    # Snapshot the USB hierarchy at this moment.
    usb_hierarchy = UsbHierarchy()

    # We want to check if we have a servo micro connected to this servo v4
    # and if so, initialize it and add it to the servod instance.
    servo_v4 = self.get_servo_v4_usb_device()
    servo_micro_candidates = self.get_servo_micro_devices()
    for servo_micro in servo_micro_candidates:
      # The micro-servo and the STM chip of servo v4 share the same internal hub
      # on servo v4 board. Check the USB hierarchy to find the micro-servo
      # behind. Assume we have at most one servo micro behind the servo v4.
      if usb_hierarchy.share_same_parent(servo_v4, servo_micro):
        self.prepend_config(self.SERVO_MICRO_CFG)
        self.add_servo_serial(servo_micro, self.servod.MICRO_SERVO_SERIAL)
        self.init_servo_interfaces(servo_micro)
        return

    # Try to enable CCD iff no servo-micro is detected.
    ccd_candidates = self.get_ccd_devices()
    for ccd in ccd_candidates:
      # Pick the proper CCD endpoint behind the servo v4.
      if usb_hierarchy.share_same_parent(servo_v4, ccd):
        self.prepend_config(self.CCD_CFG)
        self.add_servo_serial(ccd, self.servod.CCD_SERIAL)
        self.init_servo_interfaces(ccd)
        return

    # If no CCD endpoint is detected, print a message to inform users.
    self._logger.info("No micro-servo and CCD detected.")


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
