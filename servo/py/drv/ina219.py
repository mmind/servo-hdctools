# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Access to Texas Instruments INA219.  

A zero-drift, bi-directional current/power monitor with I2C interface.
"""
import drv.hw_driver
import logging
import numpy


import ftdi_utils


# TODO(tbroch) Need to investigate modal uses and need to change configuration
# register.  As it stands we capture samples continuously w/ 12-bit samples
# averaged across 532usecs
# TODO(tbroch) For debug, provide shuntv readings

# Register indexes of various INA219 registers
REG_CFG = 0
REG_SHV = 1
REG_BUSV = 2
REG_PWR = 3
REG_CUR = 4
REG_CALIB = 5

# 800mA range, ~12.5uA/lsb for a 50mOhm rsense.  Note lsb is SBZ
MAX_CALIB = 0xfffe

# maximum number of re-reads of bus voltage to do before raising exception for
# failing to see a data conversion
BUSV_READ_RETRY = 10
# millivolts per lsb of bus voltage register
BUSV_MV_PER_LSB = 4
# offset of 13-bit bus voltage measurement.  
# <2> reserved
# <1> CNVR: conversion ready bit
# <0> OVF: overflow bit
BUSV_MV_OFFSET = 3
# Bit <1> of Bus voltage register signals conversion is ready.  Meaning the
# device has successfully converted a sample to the output registers
BUSV_CNVR = 0x2
# Bit <0> of Bus voltage register signals overflow has occurred during
# calculation of current or power calculations and those output registers data
# is meaningless
BUSV_OVF  = 0x1
# bus voltage can measure up to 32V
BUSV_MAX = 32000

# sign bit of current output register
CUR_SIGN = 0x8000
# maximum value of current output register.
CUR_MAX = 0x7fff
# coefficient for determining current per lsb.  See datasheet for details
CUR_LSB_COEFFICIENT = 40.96
# maximum number of re-reads of current register to do before raising exception
# because current reading is still saturated
CUR_READ_RETRY = 10

# coefficient for determining power per lsb.  See datasheet for details
PWR_LSB_COEFFICIENT = 20
# maximum value of power output register.
PWR_MAX = 0x7fff

# mask ( 3-bits ) for ina219 configuration modes
CFG_MODE_MASK = 0x7
# continuous mode
CFG_MODE_CONT = 0x7
# sleep mode
CFG_MODE_SLEEP = 0


class Ina219Error(Exception):
  """Error occurred accessing INA219."""


class ina219(drv.hw_driver.HwDriver):
  """Object to access drv=ina219 controls."""
  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: FTDI interface object to handle low-level communication to
          control
      params: dictionary of params needed to perform operations on ina219
          devices.  All items are strings initially but should be cast to types
          detailed below.

    Mandatory Params:
      slv: integer, 7-bit i2c slave address
    Optional Params:
      reg: integer, raw register index [0:5] to read / write.  
      rsense: float, sense resistor size for adc in ohms.  Needed to properly
        compute current and power measurements
      subtype: string, used by get method to decide retrieval of millivolts |
          milliamps | milliwatts
    """
    super(ina219, self).__init__(interface, params)
    self._logger.debug("")
    self._slave = int(self._params['slv'], 0)
    self._i2c_obj = drv.i2c_reg.I2cReg.get_device(self._interface, self._slave,
                                                  addr_len=1, reg_len=2,
                                                  msb_first=True,
                                                  use_reg_cache=True)
    if 'subtype' not in self._params:
      raise Ina219Error("Unable to find subtype param")
    subtype = self._params['subtype']
    try:
      self._rsense = float(self._params['rsense'])
    except Exception:
      if (subtype == 'milliamps') or (subtype == 'milliwatts'):
        raise Ina219Error("No sense resistor in params")
      self._rsense = None
    # base class 
    self._msb_first = True
    self._reg_len = 2
    self._mode = None
    self._reset()

  def _reset(self):
    """Reset object state when device is transistioned to certain modes."""
    # TODO(tbroch) Not clear from data sheet what power-down makes IC forget
    # so I'm whacking everything stateful
    self._calib_reg = None
    self._reg_cache = None

  def get(self):
    """Get requested value from INA219 adc.

    Value can be milliamps, millivolts, milliwatts and raw register reads
    presently.  Actual get depends on 'subtype' in params
    
    Returns:
      float value read from INA219 in requested units.
    
    Raises:
      Ina219Error: Errors pertaining to this class
    """
    self._logger.debug("")
    subtype = self._params['subtype']
    try:
      func = getattr(self, '_Get_%s' % subtype)
    except AttributeError:
      raise Ina219Error("subtype %s has no function" % subtype)
    try:
      value = func()
    except Exception:
      raise Ina219Error("Unknown failure calling subtype %s" % subtype)
    return value

  def set(self, value):
    """Set value on INA219 device.

    TODO(tbroch) Implement some limited setting.  Device presently functions in
    default mode (continuous, 12b samples) but should offer some ability to
    change the mode (sleep).  In addition may want to add raw register writing
    for debugging or advanced uses.
    
    Args:
      value: integer value to write to device
    """
    self._logger.debug("value = %s" % str(value))
    raise NotImplementedError("Setting ina219 values not implemented")

  def _read_busv(self):
    """Read the bus voltage register.
    
    Conversion ready bit(<1>), CNVR, signifies that there is a new sample in the
    output registers. Per datasheet, page 15 (SBOS448C-AUGUST 2008-REVISED MARCH
    2009) this bit is cleared when:

      1. Writing config register (CFG_REG) except when power-down or off
      2. Reading status register (CFG_BUSV)
      3. Triggering with convert pin.  Not applicable to INA219 (only INA209)

    Overflow bit(<0>), OVF, has occurred during calculation of current or power
    and those output registers are meaningless.

    The bus voltage itself is stored in bits <15:3>.
 
    Returns:
      tuple (is_cnvr, is_ovf, voltage) where:
        is_cnvr: boolean True if conversion ready else False
        is_ovf: boolean True if math overflow occurred else False
        voltage: integer value of bus voltage in millivolts
    """
    is_cnvr = False
    is_ovf = False
    busv = self._i2c_obj._read_reg(REG_BUSV)
    if BUSV_CNVR & busv:
      is_cnvr = True
    if BUSV_OVF & busv:
      is_ovf = True
    millivolts = (busv >> BUSV_MV_OFFSET) * BUSV_MV_PER_LSB
    assert millivolts < BUSV_MAX, \
        "bus voltage measurement exceeded maximum"
    if millivolts >= BUSV_MAX:
      self._logger.error("bus voltage measurement exceeded maximum %x" %
                         millivolts)
    return (is_cnvr, is_ovf, millivolts)

  def _get_next_ovf(self):
    """Watch conversion ready bit assertion then return overflow status

    Note datasheet doesn't spell this out but it seems logical.

    Raises:
      Ina219Error: if conversion didn't assert after BUSV_READ_RETRY times
    """
    for _ in xrange(BUSV_READ_RETRY):
      (is_cnvr, is_ovf, millivolts) = self._read_busv()
      if is_cnvr:
        break
    # if we didn't _break_ from for loop  
    else:
      raise Ina219Error("Failed to see conversion (CNVR) while calibrating")
    return is_ovf

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
      Ina219Error: If calibration failed
    """
    self._logger.debug("")
    #TODO(tbroch): should look at re-calibrating to increase precision if
    # there's plenty of headroom in result

    # for first calibrate after instance object created
    if self._calib_reg is None:
      self._i2c_obj._write_reg(REG_CALIB, MAX_CALIB)
      self._calib_reg = MAX_CALIB
      is_ovf = self._get_next_ovf()
    else:
      (_, is_ovf, _) = self._read_busv()

    while is_ovf:
      calib_reg = (self._calib_reg >> 1) & MAX_CALIB
      if calib_reg == 0:
        raise Ina219Error("Failed to calibrate for lowest precision")
      self._logger.debug("writing calibrate to 0x%04x" % (calib_reg))
      self._i2c_obj._write_reg(REG_CALIB, calib_reg)
      self._calib_reg = calib_reg
      if not self._watch_cnvr():
        break

  def _Get_millivolts(self):
    """Retrieve voltage measurement for INA219 in millivolts.

    Returns:
      integer of potential in millivolts
    """
    self._logger.debug("")
    (_, _, millivolts) = self._read_busv()
    return millivolts

  def _Get_milliamps(self):
    """Retrieve current measurement for INA219 in milliamps.  

    Note may trigger calibration which will increase latency.  This calibration
    occurs when math overflow is detected from the OVF bit in the BUSV
    register.  If OVF asserts, software will attempt to adjust the calibration
    register until overflow is gone.  
    
    Returns:
      float of current in milliamps
      
    Raises:
      Ina219Error: when unable to (re)calibrate
    """
    self._logger.debug("")
    milliamps_per_lsb = self._milliamps_per_lsb()
    raw_cur = self._i2c_obj._read_reg(REG_CUR)
    assert raw_cur != CUR_MAX, "current saturated"
    if raw_cur == CUR_MAX:
      self._logger.error("current saturated %x\n" % raw_cur)
    raw_cur = int(numpy.int16(raw_cur))
    return raw_cur * milliamps_per_lsb

  def _Get_milliwatts(self):
    """Retrieve power measurement for INA219 in milliwatts.

    Note may trigger calibration which will increase latency 

    Returns:
      float of power in milliwatts
    """
    self._logger.debug("")
    # call first to force compulsory calibration 
    milliwatts_per_lsb = self._milliwatts_per_lsb()
    raw_pwr = self._i2c_obj._read_reg(REG_PWR)
    assert not (raw_pwr & 0x8000), \
        "Unknown whether power register is signed or unsigned"
    if raw_pwr & 0x8000:
      self._logger.error("Power may be signed %x\n" % raw_pwr)
    assert raw_pwr != PWR_MAX, "power saturated"
    if raw_pwr == PWR_MAX:
      self._logger.error("power saturated %x\n" % raw_pwr)
    raw_pwr = int(numpy.int16(raw_pwr))
    return raw_pwr * milliwatts_per_lsb

  def _Get_readreg(self):
    """Read raw register value from INA219.

    Returns:
      Integer value of register

    Raises:
      Ina219Error: If error with register access
    """
    if 'reg' not in self._params:
      raise Ina219Error("no register defined in paramters")
    reg = int(self._params['reg'])
    if reg > REG_CALIB or reg < REG_CFG:
      raise Ina219Error("register index %d, out of range" % reg)
    return self._i2c_obj._read_reg(reg)

  def _wake(self):
    """Wake up the INA219 adc from sleep."""
    self._logger.debug("")
    if self._mode is None or (self._mode != CFG_MODE_CONT):
      self._set_cfg_mode(CFG_MODE_CONT)

  def _sleep(self):
    """Place device in low-power ( no measurement state )."""
    self._logger.debug("")
    if self._mode is None or (self._mode != CFG_MODE_SLEEP):
      self._reset()
      self._set_cfg_mode(CFG_MODE_SLEEP)

  def _set_cfg_mode(self, mode):
    """Set the configuration mode of the INA219.

    Setting the configuration mode allows device to operate in different modes.
    Presently only plan to implemented sleep & continuous.  By default, the
    device powers on in continuous mode.

    Args:
      mode: integer value to write to configuration register to change the mode.
    """
    self._logger.debug("")
    assert (mode & CFG_MODE_MASK) == mode, "Invalid mode: %d" % mode
    cfg_reg = self._i2c_obj._read_reg(REG_CFG)
    self._i2c_obj._write_reg(REG_CFG, (cfg_reg & ~CFG_MODE_MASK) | mode)
    self._mode = mode
                        
  def _milliamps_per_lsb(self):
    """Calculate milliamps per least significant bit of the current register.
    
    Returns:
      float of current per lsb value in milliamps.
    """
    self._logger.debug("")
    self._calibrate()
    assert self._calib_reg, "Calibration reg not calibrated"
    lsb = CUR_LSB_COEFFICIENT / (self._calib_reg * self._rsense)
    self._logger.debug("lsb = %f" % lsb)
    return lsb

  def _milliwatts_per_lsb(self):
    """Calculate milliwatts per least significant bit of the power register.
    
    Returns:
      float of power per lsb value in milliwatts.
    """
    self._logger.debug("")
    lsb = PWR_LSB_COEFFICIENT * self._milliamps_per_lsb()
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
  adc = drv.ina219.ina219(i2c, slv, 'foo', 0.010)

  adc.calibrate()
  testit("POR  ", adc)
  adc.sleep()
  testit("SLEEP", adc)
  adc.wake()
  testit("WAKE ", adc)

if __name__ == "__main__":
  test()
