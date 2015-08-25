# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Servo Server."""
import fnmatch
import imp
import logging
import os
import shutil
import SimpleXMLRPCServer
import subprocess
import tempfile
import time
import urllib

# TODO(tbroch) deprecate use of relative imports
from drv.hw_driver import HwDriverError
import bbadc
import bbi2c
import bbgpio
import bbuart
import ftdigpio
import ftdii2c
import ftdi_common
import ftdiuart
import i2cbus
import keyboard_handlers
import servo_interfaces

MAX_I2C_CLOCK_HZ = 100000


class ServodError(Exception):
  """Exception class for servod."""

class Servod(object):
  """Main class for Servo debug/controller Daemon."""
  _USB_DETECTION_DELAY = 10
  _USB_POWEROFF_DELAY = 2
  _HTTP_PREFIX = "http://"
  _USB_J3 = "usb_mux_sel1"
  _USB_J3_TO_SERVO = "servo_sees_usbkey"
  _USB_J3_TO_DUT = "dut_sees_usbkey"
  _USB_J3_PWR = "prtctl4_pwren"
  _USB_J3_PWR_ON = "on"
  _USB_J3_PWR_OFF = "off"

  def __init__(self, config, vendor, product, serialname=None,
               interfaces=None, board="", version=None, usbkm232=None):
    """Servod constructor.

    Args:
      config: instance of SystemConfig containing all controls for
          particular Servod invocation
      vendor: usb vendor id of FTDI device
      product: usb product id of FTDI device
      serialname: string of device serialname/number as defined in FTDI eeprom.
      interfaces: list of strings of interface types the server will instantiate
      version: String. Servo board version. Examples: servo_v1, servo_v2,
          servo_v2_r0, servo_v3
      usbkm232: String. Optional. Path to USB-KM232 device which allow for
                sending keyboard commands to DUTs that do not have built in
                keyboards. Used in FAFT tests.
                e.g. /dev/ttyUSB0

    Raises:
      ServodError: if unable to locate init method for particular interface
    """
    self._logger = logging.getLogger("Servod")
    self._logger.debug("")
    self._vendor = vendor
    self._product = product
    self._serialname = serialname
    self._syscfg = config
    # list of objects (Fi2c, Fgpio) to physical interfaces (gpio, i2c) that ftdi
    # interfaces are mapped to
    self._interface_list = []
    # Dict of Dict to map control name, function name to to tuple (params, drv)
    # Ex) _drv_dict[name]['get'] = (params, drv)
    self._drv_dict = {}
    self._board = board
    self._version = version
    self._usbkm232 = usbkm232

    self._keyboard = self._init_keyboard_handler(self, self._board)

    # Note, interface i is (i - 1) in list
    if not interfaces:
      try:
        interfaces = servo_interfaces.INTERFACE_BOARDS[board][vendor][product]
      except KeyError:
        interfaces = servo_interfaces.INTERFACE_DEFAULTS[vendor][product]

    for i, interface in enumerate(interfaces):
      is_ftdi_interface = False
      if type(interface) is dict:
        name = interface['name']
      elif type(interface) is str:
        # Its FTDI related interface
        name = interface
        interface = (i % ftdi_common.MAX_FTDI_INTERFACES_PER_DEVICE) + 1
        is_ftdi_interface = True
      else:
        raise ServodError("Illegal interface type %s" % type(interface))

      # servos with multiple FTDI are guaranteed to have contiguous USB PIDs
      if is_ftdi_interface and i and \
            ((i % ftdi_common.MAX_FTDI_INTERFACES_PER_DEVICE) == 0):
        self._product += 1
        self._logger.info("Changing to next FTDI part @ pid = 0x%04x",
                          self._product)

      self._logger.info("Initializing interface %d to %s", i + 1, name)
      try:
        func = getattr(self, '_init_%s' % name)
      except AttributeError:
        raise ServodError("Unable to locate init for interface %s" % name)
      result = func(interface)
      if isinstance(result, tuple):
        self._interface_list.extend(result)
      else:
        self._interface_list.append(result)

  def _init_keyboard_handler(self, servo, board=''):
    """Initialize the correct keyboard handler for board.

    @param servo: servo object.
    @param board: string, board name.

    """
    if board == 'parrot':
      return keyboard_handlers.ParrotHandler(servo)
    elif board == 'stout':
      return keyboard_handlers.StoutHandler(servo)
    elif board in ('buddy', 'cranky', 'guado', 'jecht', 'mccloud', 'monroe',
                   'ninja', 'nyan_kitty', 'panther', 'rikku', 'stumpy',
                   'sumo', 'tidus', 'tricky', 'veyron_mickey', 'veyron_rialto',
                   'zako'):
      if self._usbkm232 is None:
        logging.warn("No device path specified for usbkm232 handler. Returning "
                     "the MatrixKeyboardHandler, which is likely the wrong "
                     "keyboard handler for the board type specified.")
        return keyboard_handlers.MatrixKeyboardHandler(servo)
      return keyboard_handlers.USBkm232Handler(servo, self._usbkm232)
    else:
      # The following boards don't use Chrome EC.
      if board in ('alex', 'butterfly', 'lumpy', 'zgb'):
        return keyboard_handlers.MatrixKeyboardHandler(servo)
      return keyboard_handlers.ChromeECHandler(servo)

  def __del__(self):
    """Servod deconstructor."""
    for interface in self._interface_list:
      del(interface)

  def _init_dummy(self, interface):
    """Initialize dummy interface.

    Dummy interface is just a mechanism to reserve that interface for non servod
    interaction.  Typically the interface will be managed by external
    third-party tools like openOCD or urjtag for JTAG or flashrom for SPI
    interfaces.

    TODO(tbroch): Investigate merits of incorporating these third-party
    interfaces into servod or creating a communication channel between them

    Returns: None
    """
    return None

  def _init_ftdi_gpio(self, interface):
    """Initialize gpio driver interface and open for use.

    Args:
      interface: interface number of FTDI device to use.

    Returns:
      Instance object of interface.

    Raises:
      ServodError: If init fails
    """
    fobj = ftdigpio.Fgpio(self._vendor, self._product, interface,
                          self._serialname)
    try:
      fobj.open()
    except ftdigpio.FgpioError as e:
      raise ServodError('Opening gpio interface. %s ( %d )' % (e.msg, e.value))

    return fobj

  def _init_bb_adc(self, interface):
    """Initalize beaglebone ADC interface."""
    return bbadc.BBadc()

  def _init_bb_gpio(self, interface):
    """Initalize beaglebone gpio interface."""
    return bbgpio.BBgpio()

  def _init_ftdi_i2c(self, interface):
    """Initialize i2c interface and open for use.

    Args:
      interface: interface number of FTDI device to use

    Returns:
      Instance object of interface

    Raises:
      ServodError: If init fails
    """
    fobj = ftdii2c.Fi2c(self._vendor, self._product, interface,
                        self._serialname)
    try:
      fobj.open()
    except ftdii2c.Fi2cError as e:
      raise ServodError('Opening i2c interface. %s ( %d )' % (e.msg, e.value))

    # Set the frequency of operation of the i2c bus.
    # TODO(tbroch) make configureable
    fobj.setclock(MAX_I2C_CLOCK_HZ)

    return fobj

  # TODO (sbasi) crbug.com/187489 - Implement bb_i2c.
  def _init_bb_i2c(self, interface):
    """Initalize beaglebone i2c interface."""
    return bbi2c.BBi2c(interface)

  def _init_dev_i2c(self, interface):
    """Initalize Linux i2c-dev interface."""
    return i2cbus.I2CBus('/dev/i2c-%d' % interface['bus_num'])

  def _init_ftdi_uart(self, interface):
    """Initialize ftdi uart inteface and open for use

    Note, the uart runs in a separate thread (pthreads).  Users wishing to
    interact with it will query control for the pty's pathname and connect
    with there favorite console program.  For example:
      cu -l /dev/pts/22

    Args:
      interface: interface number of FTDI device to use

    Returns:
      Instance object of interface

    Raises:
      ServodError: If init fails
    """
    fobj = ftdiuart.Fuart(self._vendor, self._product, interface,
                          self._serialname)
    try:
      fobj.run()
    except ftdiuart.FuartError as e:
      raise ServodError('Running uart interface. %s ( %d )' % (e.msg, e.value))

    self._logger.info("%s" % fobj.get_pty())
    return fobj

  # TODO (sbasi) crbug.com/187492 - Implement bbuart.
  def _init_bb_uart(self, interface):
    """Initalize beaglebone uart interface."""
    logging.debug('UART INTERFACE: %s', interface)
    return bbuart.BBuart(interface)

  def _init_ftdi_gpiouart(self, interface):
    """Initialize special gpio + uart interface and open for use

    Note, the uart runs in a separate thread (pthreads).  Users wishing to
    interact with it will query control for the pty's pathname and connect
    with there favorite console program.  For example:
      cu -l /dev/pts/22

    Args:
      interface: interface number of FTDI device to use

    Returns:
      Instance objects of interface

    Raises:
      ServodError: If init fails
    """
    fgpio = self._init_ftdi_gpio(interface)
    fuart = ftdiuart.Fuart(self._vendor, self._product, interface,
                           self._serialname, fgpio._fc)
    try:
      fuart.run()
    except ftdiuart.FuartError as e:
      raise ServodError('Running uart interface. %s ( %d )' % (e.msg, e.value))

    self._logger.info("uart pty: %s" % fuart.get_pty())
    return fgpio, fuart

  def _camel_case(self, string):
    output = ''
    for s in string.split('_'):
      if output:
        output += s.capitalize()
      else:
        output = s
    return output

  def _get_param_drv(self, control_name, is_get=True):
    """Get access to driver for a given control.

    Note, some controls have different parameter dictionaries for 'getting' the
    control's value versus 'setting' it.  Boolean is_get distinguishes which is
    being requested.

    Args:
      control_name: string name of control
      is_get: boolean to determine

    Returns:
      tuple (param, drv) where:
        param: param dictionary for control
        drv: instance object of driver for particular control

    Raises:
      ServodError: Error occurred while examining params dict
    """
    self._logger.debug("")
    # if already setup just return tuple from driver dict
    if control_name in self._drv_dict:
      if is_get and ('get' in self._drv_dict[control_name]):
        return self._drv_dict[control_name]['get']
      if not is_get and ('set' in self._drv_dict[control_name]):
        return self._drv_dict[control_name]['set']

    params = self._syscfg.lookup_control_params(control_name, is_get)
    if 'drv' not in params:
      self._logger.error("Unable to determine driver for %s" % control_name)
      raise ServodError("'drv' key not found in params dict")
    if 'interface' not in params:
      self._logger.error("Unable to determine interface for %s" %
                         control_name)
      raise ServodError("'interface' key not found in params dict")

    interface_id = params.get(
            '%s_interface' % self._version, params['interface'])
    if interface_id == 'servo':
      interface = self
    else:
      index = int(interface_id) - 1
      interface = self._interface_list[index]

    servo_pkg = imp.load_module('servo', *imp.find_module('servo'))
    drv_pkg = imp.load_module('drv',
                              *imp.find_module('drv', servo_pkg.__path__))
    drv_name = params['drv']
    drv_module = getattr(drv_pkg, drv_name)
    drv_class = getattr(drv_module, self._camel_case(drv_name))
    drv = drv_class(interface, params)
    if control_name not in self._drv_dict:
      self._drv_dict[control_name] = {}
    if is_get:
      self._drv_dict[control_name]['get'] = (params, drv)
    else:
      self._drv_dict[control_name]['set'] = (params, drv)
    return (params, drv)

  def doc_all(self):
    """Return all documenation for controls.

    Returns:
      string of <doc> text in config file (xml) and the params dictionary for
      all controls.

      For example:
      warm_reset             :: Reset the device warmly
      ------------------------> {'interface': '1', 'map': 'onoff_i', ... }
    """
    return self._syscfg.display_config()

  def doc(self, name):
    """Retreive doc string in system config file for given control name.

    Args:
      name: name string of control to get doc string

    Returns:
      doc string of name

    Raises:
      NameError: if fails to locate control
    """
    self._logger.debug("name(%s)" % (name))
    if self._syscfg.is_control(name):
      return self._syscfg.get_control_docstring(name)
    else:
      raise NameError("No control %s" %name)

  def _switch_usbkey(self, mux_direction):
    """Connect USB flash stick to either servo or DUT.

    This function switches 'usb_mux_sel1' to provide electrical
    connection between the USB port J3 and either servo or DUT side.

    Switching the usb mux is accompanied by powercycling
    of the USB stick, because it sometimes gets wedged if the mux
    is switched while the stick power is on.

    Args:
      mux_direction: "servo_sees_usbkey" or "dut_sees_usbkey".
    """
    self.set(self._USB_J3_PWR, self._USB_J3_PWR_OFF)
    time.sleep(self._USB_POWEROFF_DELAY)
    self.set(self._USB_J3, mux_direction)
    time.sleep(self._USB_POWEROFF_DELAY)
    self.set(self._USB_J3_PWR, self._USB_J3_PWR_ON)
    if mux_direction == self._USB_J3_TO_SERVO:
      time.sleep(self._USB_DETECTION_DELAY)

  def _get_usb_port_set(self):
    """Gets a set of USB disks currently connected to the system

    Returns:
      A set of USB disk paths.
    """
    usb_set = fnmatch.filter(os.listdir("/dev/"), "sd[a-z]")
    return set(["/dev/" + dev for dev in usb_set])

  def _probe_host_usb_dev(self):
    """Probe the USB disk device plugged in the servo from the host side.

    Method can fail by:
    1) Having multiple servos connected and returning incorrect /dev/sdX of
       another servo.
    2) Finding multiple /dev/sdX and returning None.

    Returns:
      USB disk path if one and only one USB disk path is found, otherwise None.
    """
    original_value = self.get(self._USB_J3)
    original_usb_power = self.get(self._USB_J3_PWR)
    # Make the host unable to see the USB disk.
    if (original_usb_power == self._USB_J3_PWR_ON and
        original_value != self._USB_J3_TO_DUT):
      self._switch_usbkey(self._USB_J3_TO_DUT)
    no_usb_set = self._get_usb_port_set()

    # Make the host able to see the USB disk.
    self._switch_usbkey(self._USB_J3_TO_SERVO)
    has_usb_set = self._get_usb_port_set()

    # Back to its original value.
    if original_value != self._USB_J3_TO_SERVO:
      self._switch_usbkey(original_value)
    if original_usb_power != self._USB_J3_PWR_ON:
      self.set(self._USB_J3_PWR, self._USB_J3_PWR_OFF)
      time.sleep(self._USB_POWEROFF_DELAY)

    # Subtract the two sets to find the usb device.
    diff_set = has_usb_set - no_usb_set
    if len(diff_set) == 1:
      return diff_set.pop()
    else:
      return None

  def download_image_to_usb(self, image_path):
    """Download image and save to the USB device found by probe_host_usb_dev.
    If the image_path is a URL, it will download this url to the USB path;
    otherwise it will simply copy the image_path's contents to the USB path.

    Args:
      image_path: path or url to the recovery image.

    Returns:
      True|False: True if process completed successfully, False if error
                  occurred.
      Can't return None because XMLRPC doesn't allow it. PTAL at tbroch's
      comment at the end of set().
    """
    self._logger.debug("image_path(%s)" % image_path)
    self._logger.debug("Detecting USB stick device...")
    usb_dev = self._probe_host_usb_dev()
    if not usb_dev:
      self._logger.error("No usb device connected to servo")
      return False

    try:
      if image_path.startswith(self._HTTP_PREFIX):
        self._logger.debug("Image path is a URL, downloading image")
        urllib.urlretrieve(image_path, usb_dev)
      else:
        shutil.copyfile(image_path, usb_dev)
    except IOError as e:
      self._logger.error("Failed to transfer image to USB device: %s ( %d ) ",
                         e.strerror, e.errno)
      return False
    except urllib.ContentTooShortError:
      self._logger.error("Failed to download URL: %s to USB device: %s",
                         image_path, usb_dev)
      return False
    except BaseException as e:
      self._logger.error("Unexpected exception downloading %s to %s: %s",
                         image_path, usb_dev, str(e))
      return False
    finally:
      # We just plastered the partition table for a block device.
      # Pass or fail, we mustn't go without telling the kernel about
      # the change, or it will punish us with sporadic, hard-to-debug
      # failures.
      subprocess.call(["sync"])
      subprocess.call(["blockdev", "--rereadpt", usb_dev])
    return True

  def make_image_noninteractive(self):
    """Makes the recovery image noninteractive.

    A noninteractive image will reboot automatically after installation
    instead of waiting for the USB device to be removed to initiate a system
    reboot.

    Mounts partition 1 of the image stored on usb_dev and creates a file
    called "non_interactive" so that the image will become noninteractive.

    Returns:
      True|False: True if process completed successfully, False if error
                  occurred.
    """
    result = True
    usb_dev = self._probe_host_usb_dev()
    if not usb_dev:
      self._logger.error("No usb device connected to servo")
      return False
    # Create TempDirectory
    tmpdir = tempfile.mkdtemp()
    if tmpdir:
      # Mount drive to tmpdir.
      partition_1 = "%s1" % usb_dev
      rc = subprocess.call(["mount", partition_1, tmpdir])
      if rc == 0:
        # Create file 'non_interactive'
        non_interactive_file = os.path.join(tmpdir, "non_interactive")
        try:
          open(non_interactive_file, "w").close()
        except IOError as e:
          self._logger.error("Failed to create file %s : %s ( %d )",
                             non_interactive_file, e.strerror, e.errno)
          result = False
        except BaseException as e:
          self._logger.error("Unexpected Exception creating file %s : %s",
                             non_interactive_file, str(e))
          result = False
        # Unmount drive regardless if file creation worked or not.
        rc = subprocess.call(["umount", partition_1])
        if rc != 0:
          self._logger.error("Failed to unmount USB Device")
          result = False
      else:
        self._logger.error("Failed to mount USB Device")
        result = False

      # Delete tmpdir. May throw exception if 'umount' failed.
      try:
        os.rmdir(tmpdir)
      except OSError as e:
        self._logger.error("Failed to remove temp directory %s : %s",
                           tmpdir, str(e))
        return False
      except BaseException as e:
        self._logger.error("Unexpected Exception removing tempdir %s : %s",
                           tmpdir, str(e))
        return False
    else:
      self._logger.error("Failed to create temp directory.")
      return False
    return result

  def set_get_all(self, cmds):
    """Set &| get one or more control values.

    Args:
      cmds: list of control[:value] to get or set.

    Returns:
      rv: list of responses from calling get or set methods.
    """
    rv = []
    for cmd in cmds:
      if ':' in cmd:
        (control, value) = cmd.split(':')
        rv.append(self.set(control, value))
      else:
        rv.append(self.get(cmd))
    return rv

  def get(self, name):
    """Get control value.

    Args:
      name: name string of control

    Returns:
      Response from calling drv get method.  Value is reformatted based on
      control's dictionary parameters

    Raises:
      HwDriverError: Error occurred while using drv
    """
    self._logger.debug("name(%s)" % (name))
    if name == 'serialname':
      if self._serialname:
        return self._serialname
      return 'unknown'
    (param, drv) = self._get_param_drv(name)
    try:
      val = drv.get()
      rd_val = self._syscfg.reformat_val(param, val)
      self._logger.debug("%s = %s" % (name, rd_val))
      return rd_val
    except AttributeError, error:
      self._logger.error("Getting %s: %s" % (name, error))
      raise
    except HwDriverError:
      self._logger.error("Getting %s" % (name))
      raise

  def get_all(self, verbose):
    """Get all controls values.

    Args:
      verbose: Boolean on whether to return doc info as well

    Returns:
      string creating from trying to get all values of all controls.  In case of
      error attempting access to control, response is 'ERR'.
    """
    rsp = []
    for name in self._syscfg.syscfg_dict['control']:
      self._logger.debug("name = %s" %name)
      try:
        value = self.get(name)
      except Exception:
        value = "ERR"
        pass
      if verbose:
        rsp.append("GET %s = %s :: %s" % (name, value, self.doc(name)))
      else:
        rsp.append("%s:%s" % (name, value))
    return '\n'.join(sorted(rsp))

  def set(self, name, wr_val_str):
    """Set control.

    Args:
      name: name string of control
      wr_val_str: value string to write.  Can be integer, float or a
          alpha-numerical that is mapped to a integer or float.

    Raises:
      HwDriverError: Error occurred while using driver
    """
    self._logger.debug("name(%s) wr_val(%s)" % (name, wr_val_str))
    (params, drv) = self._get_param_drv(name, False)
    wr_val = self._syscfg.resolve_val(params, wr_val_str)
    try:
      drv.set(wr_val)
    except HwDriverError:
      self._logger.error("Setting %s -> %s" % (name, wr_val_str))
      raise
    # TODO(tbroch) Figure out why despite allow_none=True for both xmlrpc server
    # & client I still have to return something to appease the
    # marshall/unmarshall
    return True

  def hwinit(self, verbose=False):
    """Initialize all controls.

    These values are part of the system config XML files of the form
    init=<value>.  This command should be used by clients wishing to return the
    servo and DUT its connected to a known good/safe state.

    Note that initialization errors are ignored (as in some cases they could
    be caused by DUT firmware deficiencies). This might need to be fine tuned
    later.

    Args:
      verbose: boolean, if True prints info about control initialized.
        Otherwise prints nothing.

    Returns:
      This function is called across RPC and as such is expected to return
      something unless transferring 'none' across is allowed. Hence adding a
      dummy return value to make things simpler.
    """
    for control_name, value in self._syscfg.hwinit:
      try:
        self.set(control_name, value)
      except Exception as e:
        self._logger.error("Problem initializing %s -> %s :: %s",
                           control_name, value, str(e))
      if verbose:
        self._logger.info('Initialized %s to %s', control_name, value)
    return True

  def echo(self, echo):
    """Dummy echo function for testing/examples.

    Args:
      echo: string to echo back to client
    """
    self._logger.debug("echo(%s)" % (echo))
    return "ECH0ING: %s" % (echo)

  def get_board(self):
    """Return the board specified at startup, if any."""
    return self._board

  def get_version(self):
    """Get servo board version."""
    return self._version

  def power_long_press(self):
    """Simulate a long power button press."""
    # After a long power press, the EC may ignore the next power
    # button press (at least on Alex).  To guarantee that this
    # won't happen, we need to allow the EC one second to
    # collect itself.
    self._keyboard.power_long_press()
    return True

  def power_normal_press(self):
    """Simulate a normal power button press."""
    self._keyboard.power_normal_press()
    return True

  def power_short_press(self):
    """Simulate a short power button press."""
    self._keyboard.power_short_press()
    return True

  def power_key(self, secs=''):
    """Simulate a power button press.

    Args:
      secs: Time in seconds to simulate the keypress.
    """
    self._keyboard.power_key(secs)
    return True

  def ctrl_d(self, press_secs=''):
    """Simulate Ctrl-d simultaneous button presses."""
    self._keyboard.ctrl_d(press_secs)
    return True

  def ctrl_u(self):
    """Simulate Ctrl-u simultaneous button presses."""
    self._keyboard.ctrl_u()
    return True

  def ctrl_enter(self, press_secs=''):
    """Simulate Ctrl-enter simultaneous button presses."""
    self._keyboard.ctrl_enter(press_secs)
    return True

  def d_key(self, press_secs=''):
    """Simulate Enter key button press."""
    self._keyboard.d_key(press_secs)
    return True

  def ctrl_key(self, press_secs=''):
    """Simulate Enter key button press."""
    self._keyboard.ctrl_key(press_secs)
    return True

  def enter_key(self, press_secs=''):
    """Simulate Enter key button press."""
    self._keyboard.enter_key(press_secs)
    return True

  def refresh_key(self, press_secs=''):
    """Simulate Refresh key (F3) button press."""
    self._keyboard.refresh_key(press_secs)
    return True

  def ctrl_refresh_key(self, press_secs=''):
    """Simulate Ctrl and Refresh (F3) simultaneous press.

    This key combination is an alternative of Space key.
    """
    self._keyboard.ctrl_refresh_key(press_secs)
    return True

  def imaginary_key(self, press_secs=''):
    """Simulate imaginary key button press.

    Maps to a key that doesn't physically exist.
    """
    self._keyboard.imaginary_key(press_secs)
    return True


def test():
  """Integration testing.

  TODO(tbroch) Enhance integration test and add unittest (see mox)
  """
  logging.basicConfig(level=logging.DEBUG,
                      format="%(asctime)s - %(name)s - " +
                      "%(levelname)s - %(message)s")
  # configure server & listen
  servod_obj = Servod(1)
  # 4 == number of interfaces on a FT4232H device
  for i in xrange(4):
    if i == 1:
      # its an i2c interface ... see __init__ for details and TODO to make
      # this configureable
      servod_obj._interface_list[i].wr_rd(0x21, [0], 1)
    else:
      # its a gpio interface
      servod_obj._interface_list[i].wr_rd(0)

  server = SimpleXMLRPCServer.SimpleXMLRPCServer(("localhost", 9999),
                                                 allow_none=True)
  server.register_introspection_functions()
  server.register_multicall_functions()
  server.register_instance(servod_obj)
  logging.info("Listening on localhost port 9999")
  server.serve_forever()

if __name__ == "__main__":
  test()

  # simple client transaction would look like
  """
  remote_uri = 'http://localhost:9999'
  client = xmlrpclib.ServerProxy(remote_uri, verbose=False)
  send_str = "Hello_there"
  print "Sent " + send_str + ", Recv " + client.echo(send_str)
  """
