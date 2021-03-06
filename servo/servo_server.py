# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Servo Server."""
import contextlib
import datetime
import fcntl
import fnmatch
import imp
import logging
import os
import random
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
import ec3po_interface
import ftdigpio
import ftdii2c
import ftdi_common
import ftdiuart
import i2cbus
import keyboard_handlers
import servo_interfaces
import servo_postinit
import stm32gpio
import stm32i2c
import stm32uart


MAX_I2C_CLOCK_HZ = 100000

# It takes about 16-17 seconds for the entire probe usb device method,
# let's wait double plus some buffer.
_MAX_USB_LOCK_WAIT = 40

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
  _USB_LOCK_FILE = "/var/lib/servod/lock_file"

  # This is the key to get the main serial used in the _serialnames dict.
  MAIN_SERIAL = "main"
  MICRO_SERVO_SERIAL = "micro_servo"
  CCD_SERIAL = "ccd"

  def init_servo_interfaces(self, vendor, product, serialname,
                            interfaces):
    """Init the servo interfaces with the given interfaces.

    We don't use the self._{vendor,product,serialname} attributes because we
    want to allow other callers to initialize other interfaces that may not
    be associated with the initialized attributes (e.g. a servo v4 servod object
    that wants to also initialize a servo micro interface).

    Args:
      vendor: USB vendor id of FTDI device.
      product: USB product id of FTDI device.
      serialname: String of device serialname/number as defined in FTDI
          eeprom.
      interfaces: List of strings of interface types the server will
          instantiate.

    Raises:
      ServodError if unable to locate init method for particular interface.
    """
    # Extend the interface list if we need to.
    interfaces_len = len(interfaces)
    interface_list_len = len(self._interface_list)
    if interfaces_len > interface_list_len:
      self._interface_list += [None] * (interfaces_len - interface_list_len)

    shifted = 0
    for i, interface in enumerate(interfaces):
      is_ftdi_interface = False
      if type(interface) is dict:
        name = interface['name']
        # Store interface index for those that care about it.
        interface['index'] = i
      elif type(interface) is str and interface != 'dummy':
        name = interface
        # It's a FTDI related interface.
        interface = (i % ftdi_common.MAX_FTDI_INTERFACES_PER_DEVICE) + 1
        is_ftdi_interface = True
      elif type(interface) is str and interface == 'dummy':
        # 'dummy' reserves the interface for future use.  Typically the
        # interface will be managed by external third-party tools like
        # openOCD for JTAG or flashrom for SPI.  In the case of servo V4,
        # it serves as a placeholder for servo micro interfaces.
        continue
      else:
        raise ServodError("Illegal interface type %s" % type(interface))

      # servos with multiple FTDI are guaranteed to have contiguous USB PIDs
      if is_ftdi_interface and i and \
            ((i % ftdi_common.MAX_FTDI_INTERFACES_PER_DEVICE) == 0):
        product += 1
        self._logger.info("Changing to next FTDI part @ pid = 0x%04x",
                          product)

      self._logger.info("Initializing interface %d to %s", i + 1, name)
      try:
        func = getattr(self, '_init_%s' % name)
      except AttributeError:
        raise ServodError("Unable to locate init for interface %s" % name)
      result = func(vendor, product, serialname, interface)

      if isinstance(result, tuple):
        result_len = len(result)
        shifted += result_len - 1
        self._interface_list += [None] * result_len
        for result_index, r in enumerate(result):
          self._interface_list[i + result_index] = r
      else:
        self._interface_list[i + shifted] = result

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
          keyboards. Used in FAFT tests.  Use 'atmega' for on board AVR MCU.
          e.g. '/dev/ttyUSB0' or 'atmega'

    Raises:
      ServodError: if unable to locate init method for particular interface
    """
    self._logger = logging.getLogger("Servod")
    self._logger.debug("")
    self._vendor = vendor
    self._product = product
    self._serialnames = {self.MAIN_SERIAL: serialname}
    self._syscfg = config
    # Hold the last image path so we can reduce downloads to the usb device.
    self._image_path = None
    # list of objects (Fi2c, Fgpio) to physical interfaces (gpio, i2c) that ftdi
    # interfaces are mapped to
    self._interface_list = []
    # Dict of Dict to map control name, function name to to tuple (params, drv)
    # Ex) _drv_dict[name]['get'] = (params, drv)
    self._drv_dict = {}
    self._board = board
    self._version = version
    self._usbkm232 = usbkm232
    # Seed the random generator with the serial to differentiate from other
    # servod processes.
    random.seed(serialname if serialname else time.time())
    # Note, interface i is (i - 1) in list
    if not interfaces:
      try:
        interfaces = servo_interfaces.INTERFACE_BOARDS[board][vendor][product]
      except KeyError:
        interfaces = servo_interfaces.INTERFACE_DEFAULTS[vendor][product]

    self.init_servo_interfaces(vendor, product, serialname, interfaces)
    servo_postinit.post_init(self)

  def _init_keyboard_handler(self, servo, board=''):
    """Initialize the correct keyboard handler for board.

    Args:
      servo: servo object.
      board: string, board name.

    Returns:
      keyboard handler object.
    """
    if board == 'parrot':
      return keyboard_handlers.ParrotHandler(servo)
    elif board == 'stout':
      return keyboard_handlers.StoutHandler(servo)
    elif board in ('buddy', 'cranky', 'guado', 'jecht', 'mccloud', 'monroe',
                   'ninja', 'nyan_kitty', 'panther', 'rikku', 'stumpy',
                   'sumo', 'tidus', 'tricky', 'veyron_fievel', 'veyron_mickey',
                   'veyron_rialto', 'veyron_tiger', 'zako'):
      if self._usbkm232 is None:
        logging.info("No device path specified for usbkm232 handler. Use "
                     "the servo atmega chip to handle.")
        self._usbkm232 = 'atmega'
      if self._usbkm232 == 'atmega':
        # Use servo onboard keyboard emulator.
        self.set('atmega_rst', 'on')
        self.set('at_hwb', 'off')
        self.set('atmega_rst', 'off')
        self._usbkm232 = self.get('atmega_pty')
        # We don't need to set the atmega uart settings if we're a servo v4.
        if self._version != 'servo_v4':
          self.set('atmega_baudrate', '9600')
          self.set('atmega_bits', 'eight')
          self.set('atmega_parity', 'none')
          self.set('atmega_sbits', 'one')
          self.set('usb_mux_sel4', 'on')
          self.set('usb_mux_oe4', 'on')
          # Allow atmega bootup time.
          time.sleep(1.0)
      self._logger.info('USBKM232: %s', self._usbkm232)
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

  def _init_ftdi_dummy(self, vendor, product, serialname, interface):
    """Dummy interface for ftdi devices.

    This is a dummy function specifically for ftdi devices to not initialize
    anything but to help pad the interface list.

    Returns:
      None.
    """
    return None

  def _init_ftdi_gpio(self, vendor, product, serialname, interface):
    """Initialize gpio driver interface and open for use.

    Args:
      interface: interface number of FTDI device to use.

    Returns:
      Instance object of interface.

    Raises:
      ServodError: If init fails
    """
    fobj = ftdigpio.Fgpio(vendor, product, interface, serialname)
    try:
      fobj.open()
    except ftdigpio.FgpioError as e:
      raise ServodError('Opening gpio interface. %s ( %d )' % (e.msg, e.value))

    return fobj

  def _init_stm32_uart(self, vendor, product, serialname, interface):
    """Initialize stm32 uart interface and open for use

    Note, the uart runs in a separate thread.  Users wishing to
    interact with it will query control for the pty's pathname and connect
    with their favorite console program.  For example:
      cu -l /dev/pts/22

    Args:
      interface: dict of interface parameters.

    Returns:
      Instance object of interface

    Raises:
      ServodError: Raised on init failure.
    """
    self._logger.info("Suart: interface: %s" % interface)
    sobj = stm32uart.Suart(vendor, product, interface['interface'],
                           serialname)

    try:
      sobj.run()
    except stm32uart.SuartError as e:
      raise ServodError('Running uart interface. %s ( %d )' % (e.msg, e.value))

    self._logger.info("%s" % sobj.get_pty())
    return sobj

  def _init_stm32_gpio(self, vendor, product, serialname, interface):
    """Initialize stm32 gpio interface.
    Args:
      interface: interface number of stm32 device to use.

    Returns:
      Instance object of interface

    Raises:
      SgpioError: Raised on init failure.
    """
    interface_number = interface
    # Interface could be a dict.
    if type(interface) is dict:
      interface_number = interface['interface']
    self._logger.info("Sgpio: interface: %s" % interface_number)
    return stm32gpio.Sgpio(vendor, product, interface_number, serialname)

  def _init_stm32_i2c(self, vendor, product, serialname, interface):
    """Initialize stm32 USB to I2C bridge interface and open for use

    Args:
      interface: USB interface number of stm32 device to use

    Returns:
      Instance object of interface.

    Raises:
      Si2cError: Raised on init failure.
    """
    self._logger.info("Si2cBus: interface: %s" % interface)
    port = interface.get('port', 0)
    return stm32i2c.Si2cBus(vendor, product, interface['interface'],
                            port=port, serialname=serialname)

  def _init_bb_adc(self, vendor, product, serialname, interface):
    """Initalize beaglebone ADC interface."""
    return bbadc.BBadc()

  def _init_bb_gpio(self, vendor, product, serialname, interface):
    """Initalize beaglebone gpio interface."""
    return bbgpio.BBgpio()

  def _init_ftdi_i2c(self, vendor, product, serialname, interface):
    """Initialize i2c interface and open for use.

    Args:
      interface: interface number of FTDI device to use

    Returns:
      Instance object of interface

    Raises:
      ServodError: If init fails
    """
    fobj = ftdii2c.Fi2c(vendor, product, interface, serialname)
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

  def _init_dev_i2c(self, vendor, product, serialname, interface):
    """Initalize Linux i2c-dev interface."""
    return i2cbus.I2CBus('/dev/i2c-%d' % interface['bus_num'])

  def _init_ftdi_uart(self, vendor, product, serialname, interface):
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
    fobj = ftdiuart.Fuart(vendor, product, interface, serialname)
    try:
      fobj.run()
    except ftdiuart.FuartError as e:
      raise ServodError('Running uart interface. %s ( %d )' % (e.msg, e.value))

    self._logger.info("%s" % fobj.get_pty())
    return fobj

  # TODO (sbasi) crbug.com/187492 - Implement bbuart.
  def _init_bb_uart(self, vendor, product, serialname, interface):
    """Initalize beaglebone uart interface."""
    logging.debug('UART INTERFACE: %s', interface)
    return bbuart.BBuart(interface)

  def _init_ftdi_gpiouart(self, vendor, product, serialname,
                          interface):
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
    fgpio = self._init_ftdi_gpio(vendor, product, serialname, interface)
    fuart = ftdiuart.Fuart(vendor, product, interface, serialname, fgpio._fc)
    try:
      fuart.run()
    except ftdiuart.FuartError as e:
      raise ServodError('Running uart interface. %s ( %d )' % (e.msg, e.value))

    self._logger.info("uart pty: %s" % fuart.get_pty())
    return fgpio, fuart

  def _init_ec3po_uart(self, vendor, product, serialname, interface):
    """Initialize EC-3PO console interpreter interface.

    Args:
      interface: A dictionary representing the interface.

    Returns:
      An EC3PO object representing the EC-3PO interface or None if there's no
      interface for the USB PD UART.
    """
    vid = vendor
    pid = product
    # The current PID might be incremented if there are multiple FTDI.
    # Therefore, try rewinding the PID back one if we don't find the base PID in
    # the SERVO_ID_DEFAULTS
    if (vid, pid) not in servo_interfaces.SERVO_ID_DEFAULTS:
      self._logger.debug('VID:PID pair not found.  Rewinding PID back one...')
      pid -= 1
    self._logger.debug('vid:0x%04x, pid:0x%04x', vid, pid)

    if 'raw_pty' in interface:
      # We have specified an explicit target for this ec3po.
      raw_uart_name = interface['raw_pty']
      raw_ec_uart = self.get(raw_uart_name)

    # Servo V2 / V3 should have the interface indicies in the same spot.
    elif ((vid, pid) in servo_interfaces.SERVO_V2_DEFAULTS or
        (vid, pid) in servo_interfaces.SERVO_V3_DEFAULTS):
      # Determine if it's a PD interface or just main EC console.
      if interface['index'] == servo_interfaces.EC3PO_USBPD_INTERFACE_NUM:
        try:
          # Obtain the raw EC UART PTY and create the EC-3PO interface.
          raw_ec_uart = self.get('raw_usbpd_uart_pty')
        except NameError:
          # This overlay doesn't have a USB PD MCU, so skip init.
          self._logger.info('No PD MCU UART.')
          return None
        except AttributeError:
          # This overlay has no get method for the interface so skip init.  For
          # servo v2, it's common for interfaces to be overridden such as
          # reusing JTAG pins for the PD MCU UART instead.  Therefore, print an
          # error message indicating that the interface might be set
          # incorrectly.
          if (vid, pid) in servo_interfaces.SERVO_V2_DEFAULTS:
            self._logger.warn('No interface for PD MCU UART.')
            self._logger.warn('Usually, this happens because the interface is '
                              'set incorrectly.  If you\'re overriding an '
                              'existing interface, be sure to update the '
                              'interface lists for your board at the end of '
                              'servo/servo_interfaces.py')
          return None

      elif interface['index'] == servo_interfaces.EC3PO_EC_INTERFACE_NUM:
        raw_ec_uart = self.get('raw_ec_uart_pty')

    # Servo V3, miniservo, Toad, Reston, Fruitpie, or Plankton
    elif ((vid, pid) in servo_interfaces.MINISERVO_ID_DEFAULTS or
          (vid, pid) in servo_interfaces.TOAD_ID_DEFAULTS or
          (vid, pid) in servo_interfaces.RESTON_ID_DEFAULTS or
          (vid, pid) in servo_interfaces.FRUITPIE_ID_DEFAULTS or
          (vid, pid) in servo_interfaces.PLANKTON_ID_DEFAULTS):
      raw_ec_uart = self.get('raw_ec_uart_pty')
    else:
      raise ServodError(('Unexpected EC-3PO interface!'
                         ' (0x%04x:0x%04x) %r') % (vid, pid, interface))

    return ec3po_interface.EC3PO(raw_ec_uart)

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

  @contextlib.contextmanager
  def _block_other_servod(self, timeout=None):
    """Block other servod processes by locking a file.

    To enable multiple servods processes to safely probe_host_usb_dev, we use
    a given lock file to signal other servod processes that we're probing
    for a usb device.  This will be a context manager that will return
    if the block was successful or not.

    If the lock file exists, we open it and try to lock it.
    - If another servod processes has locked it already, we'll sleep a random
      amount of time and try again, we'll keep doing that until
      timeout amount of time has passed.

    - If we're able to lock the file, we'll yield that the block was successful
      and upon return, unlock the file and exit out.

    This blocking behavior is only enabled if the lock file exists, if it
    doesn't, then we pretend the block was successful.

    Args:
      timeout: Max waiting time for the block to succeed.
    """
    if not os.path.exists(self._USB_LOCK_FILE):
      # No lock file so we'll pretend the block was a success.
      yield True
    else:
      start_time = datetime.datetime.now()
      while True:
        with open(self._USB_LOCK_FILE) as lock_file:
          try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield True
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            break
          except IOError:
            current_time = datetime.datetime.now()
            current_wait_time = (current_time - start_time).total_seconds()
            if timeout and current_wait_time > timeout:
              yield False
              break
        # Sleep random amount.
        sleep_time = time.sleep(random.random())

  def safe_switch_usbkey_power(self, power_state, timeout=0):
    """Toggle the usb power safely.

    We'll make sure we're the only servod process toggling the usbkey power.

    Args:
      power_state: The setting to set for the usbkey power.
      timeout: Timeout to wait for blocking other servod processes, default is
          no timeout.

    Returns:
      An empty string to appease the xmlrpc gods.
    """
    with self._block_other_servod(timeout=timeout):
      if power_state != self.get(self._USB_J3_PWR):
        self.set(self._USB_J3_PWR, power_state)
    return ''

  def safe_switch_usbkey(self, mux_direction, timeout=0):
    """Toggle the usb direction safely.

    We'll make sure we're the only servod process toggling the usbkey direction.

    Args:
      power_state: The setting to set for the usbkey power.
      timeout: Timeout to wait for blocking other servod processes, default is
          no timeout.

    Returns:
      An empty string to appease the xmlrpc gods.
    """
    with self._block_other_servod(timeout=timeout):
      self._switch_usbkey(mux_direction)
    return ''

  def probe_host_usb_dev(self, timeout=_MAX_USB_LOCK_WAIT):
    """Probe the USB disk device plugged in the servo from the host side.

    Method can fail by:
    1) Having multiple servos connected and returning incorrect /dev/sdX of
       another servo unless _USB_LOCK_FILE exists on the servo host.  If that
       file exists, then it is safe to probe for usb devices among multiple
       servod instances.
    2) Finding multiple /dev/sdX and returning None.

    Args:
      timeout: Timeout to wait for blocking other servod processes.

    Returns:
      USB disk path if one and only one USB disk path is found, otherwise an
      empty string.
    """
    with self._block_other_servod(timeout=timeout) as block_success:
      if not block_success:
        return ''

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
        return ''

  def download_image_to_usb(self, image_path, probe_timeout=_MAX_USB_LOCK_WAIT):
    """Download image and save to the USB device found by probe_host_usb_dev.
    If the image_path is a URL, it will download this url to the USB path;
    otherwise it will simply copy the image_path's contents to the USB path.

    Args:
      image_path: path or url to the recovery image.
      probe_timeout: timeout for the probe to take.

    Returns:
      True|False: True if process completed successfully, False if error
                  occurred.
      Can't return None because XMLRPC doesn't allow it. PTAL at tbroch's
      comment at the end of set().
    """
    self._logger.debug("image_path(%s)" % image_path)
    self._logger.debug("Detecting USB stick device...")
    usb_dev = self.probe_host_usb_dev(timeout=probe_timeout)
    if not usb_dev:
      self._logger.error("No usb device connected to servo")
      return False

    # Let's check if we downloaded this last time and if so assume the image is
    # still on the usb device and return True.
    if self._image_path == image_path:
      self._logger.debug("Image already on USB device, skipping transfer")
      return True

    try:
      if image_path.startswith(self._HTTP_PREFIX):
        self._logger.debug("Image path is a URL, downloading image")
        urllib.urlretrieve(image_path, usb_dev)
      else:
        shutil.copyfile(image_path, usb_dev)
    except IOError as e:
      self._logger.error("Failed to transfer image to USB device: %s ( %s ) ",
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
    self._image_path = image_path
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
    usb_dev = self.probe_host_usb_dev()
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
      if self._serialnames[self.MAIN_SERIAL]:
        return self._serialnames[self.MAIN_SERIAL]
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
        # Workaround for bug chrome-os-partner:42349. Without this check, the
        # gpio will briefly pulse low if we set it from high to high.
        if self.get(control_name) != value:
          self.set(control_name, value)
        if verbose:
          self._logger.info('Initialized %s to %s', control_name, value)
      except Exception as e:
        self._logger.error("Problem initializing %s -> %s :: %s",
                           control_name, value, str(e))

    # Init keyboard after all the intefaces are up.
    self._keyboard = self._init_keyboard_handler(self, self._board)
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

  def ctrl_u(self, press_secs=''):
    """Simulate Ctrl-u simultaneous button presses."""
    self._keyboard.ctrl_u(press_secs)
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


  def sysrq_x(self, press_secs=''):
    """Simulate Alt VolumeUp X simultaneous press.

    This key combination is the kernel system request (sysrq) x.
    """
    self._keyboard.sysrq_x(press_secs)
    return True


  def get_servo_serials(self):
    """Return all the serials associated with this process."""
    return self._serialnames


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
