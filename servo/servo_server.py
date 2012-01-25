# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Servo Server."""
import imp
import logging
import SimpleXMLRPCServer

# TODO(tbroch) deprecate use of relative imports
import ftdigpio
import ftdii2c
import ftdi_common
import ftdiuart

MAX_I2C_CLOCK_HZ = 100000


class ServodError(Exception):
  """Exception class for servod."""

class Servod(object):
  """Main class for Servo debug/controller Daemon."""
  def __init__(self, config, vendor, product, serialname=None, interfaces=None):
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

    # Note, interface i is (i - 1) in list
    if not interfaces:
      interfaces = ftdi_common.INTERFACE_DEFAULTS[vendor][product]

    for i, name in enumerate(interfaces):
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

      # servos with multiple FTDI are guaranteed to have contiguous USB PIDs
      if i and i % ftdi_common.MAX_FTDI_INTERFACES_PER_DEVICE == 0:
        self._product += 1

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

  def _init_gpio(self, interface):
    """Initialize gpio driver interface and open for use.

    Args:
      interface: interface number of FTDI device to use.

    Returns:
      Instance object of interface.
    """
    fobj = ftdigpio.Fgpio(self._vendor, self._product, interface,
                          self._serialname)
    fobj.open()
    return fobj

  def _init_i2c(self, interface):
    """Initialize i2c interface and open for use.

    Args:
      interface: interface number of FTDI device to use

    Returns:
      Instance object of interface
    """
    fobj = ftdii2c.Fi2c(self._vendor, self._product, interface,
                        self._serialname)
    fobj.open()
    # Set the frequency of operation of the i2c bus.
    # TODO(tbroch) make configureable
    fobj.setclock(MAX_I2C_CLOCK_HZ)
    return fobj

  def _init_uart(self, interface):
    """Initialize uart inteface and open for use

    Note, the uart runs in a separate thread (pthreads).  Users wishing to
    interact with it will query control for the pty's pathname and connect
    with there favorite console program.  For example:
      cu -l /dev/pts/22

    Args:
      interface: interface number of FTDI device to use

    Returns:
      Instance object of interface
    """
    fobj = ftdiuart.Fuart(self._vendor, self._product, interface)
    fobj.run()
    self._logger.info("%s" % fobj.get_pty())
    return fobj

  def _init_gpiouart(self, interface):
    """Initialize special gpio + uart interface and open for use

    Note, the uart runs in a separate thread (pthreads).  Users wishing to
    interact with it will query control for the pty's pathname and connect
    with there favorite console program.  For example:
      cu -l /dev/pts/22

    Args:
      interface: interface number of FTDI device to use

    Returns:
      Instance objects of interface
    """
    fgpio = self._init_gpio(interface)
    fuart = ftdiuart.Fuart(self._vendor, self._product, interface, fgpio._fc)
    fuart.run()
    self._logger.info("uart pty: %s" % fuart.get_pty())
    return fgpio, fuart

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
    drv_class = getattr(drv_module, drv_name)
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
    except drv.hw_driver.HwDriverError:
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
    rsp = ""
    for name in self._syscfg.syscfg_dict['control']:
      self._logger.debug("name = %s" %name)
      try:
        value = self.get(name)
      except Exception:
        value = "ERR"
        pass
      if verbose:
        rsp += "GET %s = %s :: %s\n" % (name, value, self.doc(name))
      else:
        rsp += "%s:%s\n" % (name, value)
    return rsp

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
    except drv.hw_driver.HwDriverError:
      self._logger.error("Setting %s -> %s" % (name, wr_val_str))
      raise
    # TODO(tbroch) Figure out why despite allow_none=True for both xmlrpc server
    # & client I still have to return something to appease the
    # marshall/unmarshall
    return True

  def echo(self, echo):
    """Dummy echo function for testing/examples.

    Args:
      echo: string to echo back to client
    """
    self._logger.debug("echo(%s)" % (echo))
    return "ECH0ING: %s" % (echo)


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
