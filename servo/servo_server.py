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
import ftdigpio
import ftdii2c
import ftdi_common
import ftdiuart
import servo_interfaces

MAX_I2C_CLOCK_HZ = 100000


class ServodError(Exception):
  """Exception class for servod."""

class Servod(object):
  """Main class for Servo debug/controller Daemon."""
  _USB_DETECTION_DELAY = 10
  _HTTP_PREFIX = "http://"

  def __init__(self, config, vendor, product, serialname=None,
               interfaces=None, board=""):
    """Servod constructor.

    Args:
      config: instance of SystemConfig containing all controls for
          particular Servod invocation
      vendor: usb vendor id of FTDI device
      product: usb product id of FTDI device
      serialname: string of device serialname/number as defined in FTDI eeprom.
      interfaces: list of strings of interface types the server will instantiate

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

    # Note, interface i is (i - 1) in list
    if not interfaces:
      interfaces = servo_interfaces.INTERFACE_DEFAULTS[vendor][product]

    for i, name in enumerate(interfaces):
      # servos with multiple FTDI are guaranteed to have contiguous USB PIDs
      if i and ((i % ftdi_common.MAX_FTDI_INTERFACES_PER_DEVICE) == 0):
        self._product += 1
        self._logger.info("Changing to next FTDI part @ pid = 0x%04x",
                          self._product)

      self._logger.info("Initializing FTDI interface %d to %s", i + 1, name)
      try:
        func = getattr(self, '_init_%s' % name)
      except AttributeError:
        raise ServodError("Unable to locate init for interface %s" % name)
      result = func((i % ftdi_common.MAX_FTDI_INTERFACES_PER_DEVICE) + 1)
      if isinstance(result, tuple):
        self._interface_list.extend(result)
      else:
        self._interface_list.append(result)

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

  # TODO (sbasi) crbug.com/187488 - Implement BBgpio.
  def _init_bb_gpio(self, interface):
    """Initalize beaglebone gpio interface."""
    pass

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
    pass

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
    pass

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
    index = int(params['interface']) - 1
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
    original_value = self.get("usb_mux_sel1")
    # Make the host unable to see the USB disk.
    if original_value != "dut_sees_usbkey":
      self.set("usb_mux_sel1", "dut_sees_usbkey")
      time.sleep(self._USB_DETECTION_DELAY)

    no_usb_set = self._get_usb_port_set()
    # Make the host able to see the USB disk.
    self.set("usb_mux_sel1", "servo_sees_usbkey")
    time.sleep(self._USB_DETECTION_DELAY)

    has_usb_set = self._get_usb_port_set()
    # Back to its original value.
    if original_value != "servo_sees_usbkey":
      self.set("usb_mux_sel1", original_value)
      time.sleep(self._USB_DETECTION_DELAY)
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
    if name == 'sleep':
      time.sleep(float(wr_val_str))
      return True

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
