# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Base class to provide access to Texas Instruments INA-based ADCs

Presently tested for:
  INA219
  INA231
"""
import logging
import numpy


import hw_driver
import i2c_reg


class Ina2xxError(Exception):
  """Error occurred accessing INA219."""


class ina2xx(hw_driver.HwDriver):
  """class definition

  Note, instances of this object get dispatched via base class,
  HwDriver's get/set method.  That method ulitimately calls:
    "_[GS]et_%s" % params['subtype'] below.

  For example, a control to read the millivolts of an ADC would be
  dispatched to call _Get_millivolts.
  """
  # TODO(tbroch) Need to investigate modal uses and need to change configuration
  # register.  As it stands we capture samples continuously w/ 12-bit samples
  # averaged across 532usecs
  # TODO(tbroch) For debug, provide shuntv readings
  MAX_CHANNEL = 0
  REG_IDX = dict(cfg=0, shv=1, busv=2, pwr=3, cur=4, cal=5, msken=6, alrt=7)

  # maximum number of re-reads of bus voltage to do before raising
  # exception for failing to see a data conversion.  Note the CNVR bit
  # is affected by averaging and multiplication as well. I decided on
  # 100 by sampling the number average retries during calibration and
  # multiplying by 2x to be on the safe side
  BUSV_READ_RETRY = 100

  # sign bit of current output register
  CUR_SIGN = 0x8000
  # maximum value of current output register.
  CUR_MAX = 0x7fff
  # maximum number of re-reads of current register to do before raising
  # exception because current reading is still saturated
  CUR_READ_RETRY = 10

  # maximum value of power output register.
  PWR_MAX = 0xffff

  # mask ( 3-bits ) for ina219 configuration modes
  CFG_MODE_MASK = 0x7
  # continuous mode
  CFG_MODE_CONT = 0x7
  # sleep mode
  CFG_MODE_SLEEP = 0

  def __init__(self, interface, params):
    """Constructor.

    Args:
    interface: FTDI interface object to handle low-level communication to
      control
    params: dictionary of params needed to perform operations on
      ina219 devices.  All items are strings initially but should be
      cast to types detailed below.

    Mandatory Params:
      slv: integer, 7-bit i2c slave address
      subtype: string, used by get/set method of base class to decide
        how to dispatch request.  Examples are: millivolts, milliamps,
        milliwatts

    Optional Params:
      reg: integer, raw register index [0:5] to read / write.
      rsense: float, sense resistor size for adc in ohms.  Needed to properly
        compute current and power measurements

    Raises:
      ina2xxError: if needed params are absent
    """
    super(ina2xx, self).__init__(interface, params)
    self._logger.debug("")
    self._slave = int(self._params['slv'], 0)
    # TODO(tbroch) Re-visit enabling use_reg_cache once re-req's are
    # incorporated into cache's key field ( crosbug.com/p/2678 )
    self._i2c_obj = i2c_reg.I2cReg.get_device(self._interface, self._slave,
                                              addr_len=1, reg_len=2,
                                              msb_first=True, no_read=False,
                                              use_reg_cache=False)
    if 'subtype' not in self._params:
      raise Ina2xxError("Unable to find subtype param")
    subtype = self._params['subtype']
    try:
      self._rsense = float(self._params['rsense'])
    except Exception:
      if (subtype == 'milliamps') or (subtype == 'milliwatts'):
        raise Ina2xxError("No sense resistor in params")
      self._rsense = None
    # base class
    self._msb_first = True
    self._reg_len = 2
    self._mode = None
    self._reset()

  def _read_cnvr_ovf(self):
    raise NotImplementedError('Must be defined by child class')

  def _read_cnvr(self):
    (is_cnvr, _) = self._read_cnvr_ovf()
    return is_cnvr

  def _read_ovf(self):
    (_, is_ovf) = self._read_cnvr_ovf()
    return is_ovf

  def _reset(self):
    """Reset object state when device is transistioned to certain modes."""
    # TODO(tbroch) Not clear from data sheet what power-down makes IC forget
    # so I'm whacking everything stateful
    self._calib_reg = None
    self._reg_cache = None

  def _get_reg_idx(self, name):
    """Get register index and insure its valid.

    Args:
      name: string of register index name.

    Raises:
      Ina2xxError: if index or channel is out of range.
      NotImplementedError: if channel is set incorrectly.
    """
    channel = 0
    if 'channel' in self._params:
      try:
        channel = int(self._params['channel'])
      except ValueError, e:
        raise Ina2xxError(e)

    if channel > self.MAX_CHANNEL or channel < 0:
      raise Ina2xxError("register channel %d, out of range" % channel)

    reg = self.REG_IDX[name]
    if name in ['busv', 'shv']:
      reg += channel * 2

    if reg > self.MAX_REG_INDEX or reg < self.REG_IDX['cfg']:
      raise Ina2xxError("register index %d, out of range" % reg)

    return reg

  def _has_reg(self, reg):
    return reg in self.REG_IDX

  def _read_reg(self, name):
    """Read architected register and return value."""
    return self._i2c_obj._read_reg(self._get_reg_idx(name))

  def _write_reg(self, name, value):
    """Write architected register."""
    self._i2c_obj._write_reg(self._get_reg_idx(name), value)

  def _read_busv(self):
    """Read bus voltage value."""
    busv_reg = self._read_reg('busv')
    return busv_reg >> self.BUSV_MV_OFFSET

  def _get_next_ovf(self):
    """Watch conversion ready bit assertion then return overflow status

    Note datasheet doesn't spell this out but it seems logical.

    Returns:
      is_ovf: Boolean of whether overflow has occurred

    Raises:
      Ina2xxError: if conversion didn't assert after self.BUSV_READ_RETRY times
    """
    for _ in xrange(self.BUSV_READ_RETRY):
      is_cnvr = self._read_cnvr()
      if is_cnvr:
        break

    # if we didn't _break_ from for loop
    if not is_cnvr:
      raise Ina2xxError("Failed to see conversion (CNVR) while calibrating")
    return self._read_ovf()

  def _calibrate(self):
    """Calibrate the INA219.

    Proper calibration of adc is paramount in successful sampling of the current
    and power measurements.

    As such, if overflow occurs re-calibration is done.  The calibration
    register is inversely proportional to precision of the adc's lsb for current
    and power conversion.

    For example, for a 50mOhm sense resistor with the calibration register set
    to its maximum (MAX_CALIB), the adc is capable of 800mA range @ ~12.5uA/lsb.
    Dividing the calibration by two would provide 1600mA range @ 25uA/lsb.

    Raises:
      Ina2xxError: If calibration failed or doesn't have register.
    """
    self._logger.debug("")
    if not self._has_reg('cal'):
      raise Ina2xxError('ADC does NOT have calibration register')

    # TODO(tbroch): should look at re-calibrating to increase precision if
    # there's plenty of headroom in result

    # TODO(tbroch): remove read of calibration below once instantiation of INA
    # controls resolves that there is only one device for many controls.
    # Currently it is possible to overflow and adjust calibration say for the
    # milliwatts but be  unaware of the change for the milliamps calculations as
    # each control has a separate instance of ina219 object and therefore a
    # private copy of the calibration register.
    calib_reg = self._calib_reg = self._read_reg('cal')

    if self._calib_reg in [None, 0]:
      self._write_reg('cal', self.MAX_CALIB)
      self._calib_reg = self.MAX_CALIB
      is_ovf = self._get_next_ovf()
    else:
      is_ovf = self._read_ovf()

    while is_ovf:
      if calib_reg == self.MIN_CALIB:
        raise Ina2xxError("Failed to calibrate for lowest precision")
      calib_reg = (self._calib_reg >> 1) & self.MAX_CALIB
      self._logger.debug("writing calibrate to 0x%04x" % (calib_reg))
      self._write_reg('cal', calib_reg)
      self._calib_reg = calib_reg
      is_ovf = self._get_next_ovf()

  def _Get_millivolts(self):
    """Retrieve voltage measurement for ADC in millivolts.

    Returns:
      integer of potential in millivolts
    """
    self._logger.debug("")
    busv = self._read_busv()
    millivolts = busv * self.BUSV_MV_PER_LSB
    assert millivolts < self.BUSV_MAX, \
        "bus voltage measurement exceeded maximum"
    if millivolts >= self.BUSV_MAX:
      self._logger.error("bus voltage measurement exceeded maximum %x" %
                         millivolts)
    return millivolts

  def _get_milliamps_reg(self):
    """Retrieve current measurement for ADC in milliamps from current register.

    Note may trigger calibration which will increase latency.  This calibration
    occurs when math overflow is detected from the OVF bit in the BUSV
    register.  If OVF asserts, software will attempt to adjust the calibration
    register until overflow is gone.

    Returns:
      float of current in milliamps

    Raises:
      AssertionError: when current is saturated.
    """
    self._logger.debug("")
    milliamps_per_lsb = self._milliamps_per_lsb()
    raw_cur = self._read_reg('cur')
    assert raw_cur != self.CUR_MAX, "current saturated"
    if raw_cur == self.CUR_MAX:
      self._logger.error("current saturated %x\n" % raw_cur)
    raw_cur = int(numpy.int16(raw_cur))
    return raw_cur * milliamps_per_lsb

  def _get_shunt_millivolts(self):
    """Retrieve shunt voltage measurement for ADC.

    Returns:
      float of shunt voltage in millivolts.

    Raises:
      Ina2xxError: if shunt voltage overflowed.
    """
    vshunt_reg = self._read_reg('shv')
    logging.debug('shv = 0x%x', vshunt_reg)

    # its negative ... two's complement
    if vshunt_reg & 0x8000:
      vshunt_reg = ~vshunt_reg & self.SHV_MASK
      vshunt_reg += 1 << self.SHV_OFFSET
      vshunt_reg *= -1
      logging.debug('shv = 0x%04x after negate', vshunt_reg)

    if abs(vshunt_reg) >= self.SHV_MASK:
      raise Ina2xxError('vshunt overflow 0x%04x', vshunt_reg)

    vshunt_reg = vshunt_reg >> self.SHV_OFFSET
    return vshunt_reg * self.SHV_UV_PER_LSB / 1000.

  def _Get_shuntmv(self):
    """Retrieve shunt voltage measurement for ADC in millivolts.

    Returns:
      float of shunt voltage in millivolts.
    """
    return self._get_shunt_millivolts()

  def _get_milliamps_calc(self):
    """Retrieve current measurement for ADC in milliamps by calculation.

    Calculation is I = Vshunt / Rsense

    Returns:
      float of current in milliamps
    """
    logging.debug('')

    vshunt_mv = self._get_shunt_millivolts()
    logging.debug('vshunt_mv = %2.2f', vshunt_mv)
    return vshunt_mv / self._rsense

  def _Get_milliamps(self):
    """Retrieve current measurement for ADC in milliamps.

    At moment there are two methods for determining current:
      1. Reading ADCs current reg and scaling by ma/lsb
      2. Reading shunt voltage reg and calculating via Ohm's law
         I = Vshunt/Rsense

    Below is list of devices and which method they can support.
      Method 1: INA219, INA231
      Method 2: INA219, INA231, INA3221

    The method will retrieve current in milliamps choosing best available
    method.

    Returns:
      float of current in milliamps
    """
    if self._has_reg('cur'):
      return self._get_milliamps_reg()
    else:
      return self._get_milliamps_calc()

  def _get_milliwatts_reg(self):
    """Retrieve power measurement for ADC in milliamps from power register.

    Note may trigger calibration which will increase latency

    Returns:
      float of power in milliwatts

    Raises:
      AssertionError: when power is saturated.
    """
    self._logger.debug("")
    # call first to force compulsory calibration
    milliwatts_per_lsb = self._milliwatts_per_lsb()
    raw_pwr = self._read_reg('pwr')
    assert not (raw_pwr & 0x8000), \
        "Unknown whether power register is signed or unsigned"
    if raw_pwr & 0x8000:
      self._logger.error("Power may be signed %x\n" % raw_pwr)
    assert raw_pwr != self.PWR_MAX, "power saturated"
    if raw_pwr == self.PWR_MAX:
      self._logger.error("power saturated %x\n" % raw_pwr)
    raw_pwr = int(numpy.int16(raw_pwr))
    return raw_pwr * milliwatts_per_lsb

  def _get_milliwatts_calc(self):
    """Retrieve power measurement for ADC in milliamps from calculation.

    Returns:
      float of power in milliwatts
    """
    volts = self._Get_millivolts() / 1000.
    milliamps = self._get_milliamps_calc()
    return volts * milliamps

  def _Get_milliwatts(self):
    """Retrieve power measurement for INA ADCs in milliwatts.

    See _Get_milliamps for details on multiple methods.

    Returns:
      float of power in milliwatts
    """
    if self._has_reg('pwr'):
      return self._get_milliwatts_reg()
    else:
      return self._get_milliwatts_calc()

  def _Get_readreg(self):
    """Read raw register value from INA219.

    Returns:
      Integer value of register

    Raises:
      Ina2xxError: If error with register access
    """
    self._logger.debug("")
    if 'reg' not in self._params:
      raise Ina2xxError("no register defined in parameters")
    reg = self._params['reg']

    return self._read_reg(reg)

  def _Set_writereg(self, value):
    """Write raw register value from INA219.

    Args:
      value: Integer value to write to register

    Raises:
      Ina2xxError: If error with register access
    """
    self._logger.debug("")
    if 'reg' not in self._params:
      raise Ina2xxError("no register defined in parameters")
    reg = self._params['reg']

    self._write_reg(reg, value)
    if reg is 'cal':
      self._calib_reg = value

  def _wake(self):
    """Wake up the INA219 adc from sleep."""
    self._logger.debug("")
    if self._mode is None or (self._mode != self.CFG_MODE_CONT):
      self._set_cfg_mode(self.CFG_MODE_CONT)

  def _sleep(self):
    """Place device in low-power ( no measurement state )."""
    self._logger.debug("")
    if self._mode is None or (self._mode != self.CFG_MODE_SLEEP):
      self._reset()
      self._set_cfg_mode(self.CFG_MODE_SLEEP)

  def _set_cfg_mode(self, mode):
    """Set the configuration mode of the INA219.

    Setting the configuration mode allows device to operate in different modes.
    Presently only plan to implemented sleep & continuous.  By default, the
    device powers on in continuous mode.

    Args:
      mode: integer value to write to configuration register to change the mode.
    """
    self._logger.debug("")
    assert (mode & self.CFG_MODE_MASK) == mode, "Invalid mode: %d" % mode
    cfg_reg = self._read_reg('cfg')
    self._write_reg('cfg', (cfg_reg & ~self.CFG_MODE_MASK) | mode)

    self._mode = mode

  def _milliamps_per_lsb(self):
    """Calculate milliamps per least significant bit of the current register.

    Returns:
      float of current per lsb value in milliamps.
    """
    self._logger.debug("")
    self._calibrate()
    assert self._calib_reg, "Calibration reg not calibrated"
    lsb = self.CUR_LSB_COEFFICIENT / (self._calib_reg * self._rsense)
    self._logger.debug("lsb = %f" % lsb)
    return lsb

  def _milliwatts_per_lsb(self):
    """Calculate milliwatts per least significant bit of the power register.

    Returns:
      float of power per lsb value in milliwatts.
    """
    self._logger.debug("")
    lsb = self.PWR_LSB_COEFFICIENT * self._milliamps_per_lsb()
    self._logger.debug("lsb = %f" % lsb)
    return lsb


def testit(testname, adc):
  """Test major features of one ADC.

  Args:
    testname: string name of test
    adc: integer of 7-bit i2c slave address
  """
  for i in range(0, 6):
    print "%s: [%d] = 0x%04x" % (testname, i, adc._read_reg(i))
  print "%s: mv = %d" % (testname, adc.millivolts())
  print "%s: ma = %d" % (testname, adc.milliamps())
  print "%s: mw = %d" % (testname, adc.milliwatts())


def test():
  """Integration testing
  """
  import ftdi_utils
  (options, args) = ftdi_utils.parse_common_args(interface=2)
  loglevel = logging.INFO
  if options.debug:
    loglevel = logging.DEBUG
  logging.basicConfig(level=loglevel,
                      format="%(asctime)s - %(name)s - " +
                      "%(levelname)s - %(message)s")
  import ftdii2c
  i2c = ftdii2c.Fi2c(options.vendor, options.product, options.interface)
  i2c.open()
  i2c.setclock(100000)

  slv = 0x40
  wbuf = [0]
  # try raw transaction to ftdii2c library reading cfg reg 0x399f
  rbuf = i2c.wr_rd(slv, wbuf, 2)
  logging.info("001: i2c read of slv=0x%02x reg=0x%02x == 0x%02x%02x" %
               (slv, wbuf[0], rbuf[0], rbuf[1]))

  # same read of cfg (0x399f) using ina219 module
  adc = ina219.ina219(i2c, slv, 'foo', 0.010)

  adc.calibrate()
  testit("POR  ", adc)
  adc.sleep()
  testit("SLEEP", adc)
  adc.wake()
  testit("WAKE ", adc)

if __name__ == "__main__":
  test()
