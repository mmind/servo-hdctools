# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Interface to power measurement capabilities of TPS65090 PMIC.

Device contains 14 seperate ADCs allowing 12 power measurements of:
  1. Main AC input (via ADC VAC(0) & IAC(2))
  2. Battery Charging (via ADCs VBAT(1) & IBAT(3))
  3-5. Current measurement of 3 DC->DC converters.  Voltage must be provided.
  6-12. Current measurement of 7 power fets.  Voltage must be provided.

Module provides interface to register and read these power sources.

For example:

    i2c = TPS65090I2c(4)
    pwr = TPS65090Power(i2c)

    pwr_names = []
    pwr.register('ac', new_name='ac_mw')
    pwr_names.append('ac_mw')
    pwr.register('bat', new_name='bat_mw')
    pwr_names.append('bat_mw')

    voltages = [5, 3.3, 1.35, 40, 5, 3.3, 3.3, 3.3, 3.3, 5]
    for i,name in enumerate(AD_OUT_DEFAULT_NAMES[4:]):
        new_name = new_name='%s_mw' % name,
        pwr.register(name, new_name=name, voltage=voltages[i])
        pwr_names.append(new_name)

    for name in new_names:
        print '%s = %2.f\n' % (name, pwr.read_mw(name))

TODO(tbroch) Work with vendor to resolve discrepancies in measurements
"""
import commands
import logging
import numpy
import sys
import time

# TODO(tbroch) maybe this should be optarg
MAX_STATS = 20

# Lower 2bits configureable via Texas Instruments
I2C_SLV_DEFAULT = 0x48

REG_IDX_AD_CTRL = 0x16
# OUT1 is lower byte, OUT2 is upper byte of 10-bit ADC
REG_IDX_AD_OUT1 = 0x17
REG_IDX_AD_OUT2 = 0x18

# AD_CTRL POR value
# TODO(tbroch): Verify why <7> (reserved) != '1' despite datasheet POR
AD_CTRL_POR = 0x20

# Start a conversion measurement.  ~1mA of additional load to TPS65090 Vin
AD_CTRL_START = 0x40
# Latest conversion is completed
AD_CTRL_EOC   = 0x20
# ADC conversion vref is enabled.  ~.5mA of additional load to TPS65090 Vin
AD_CTRL_EN    = 0x10

AD_OUT_RANGE = 2**10 - 1
AD_OUT_LSB = [17./AD_OUT_RANGE,
              17./AD_OUT_RANGE,
              3./AD_OUT_RANGE,
              4./AD_OUT_RANGE,
              5./AD_OUT_RANGE,
              5./AD_OUT_RANGE,
              5./AD_OUT_RANGE,
              1.1/AD_OUT_RANGE,
              0.22/AD_OUT_RANGE,
              3.3/AD_OUT_RANGE,
              1.1/AD_OUT_RANGE,
              1.1/AD_OUT_RANGE,
              1.1/AD_OUT_RANGE,
              1.1/AD_OUT_RANGE]

AD_OUT_DEFAULT_NAMES = ['vac', 'vbat', 'ac', 'bat', 'dcdc1', 'dcdc2',
                        'dcdc3', 'fet1', 'fet2', 'fet3', 'fet4', 'fet5',
                        'fet6', 'fet7']


class TPS65090Error(Exception):
    """Exception class for TPS65090."""


class TPS65090I2c(object):
    """Class for TPS65090 I2c communication."""
    # -f to force, -y to respond 'yes' to interactive queries
    _GET_CMD = 'i2cget -f -y'
    _SET_CMD = 'i2cset -f -y'
    # TODO(tbroch) deprecate retry once there are no reports of errors on i2c
    _RETRY_MAX = 1


    def __init__(self, bus, slv=I2C_SLV_DEFAULT):
        """Constructor."""
        self._bus = bus
        self._slv = slv


    def _do_cmd(self, cmd):
        """Run command and return results.

        Args:
          cmd: string, i2c command to run

        Returns:
          string, output from shell command

        Raises:
          TPS65090Error: Bad status returned from shell command after retries
            exhausted

        """
        retry = self._RETRY_MAX
        status = 1
        while status and retry:
            (status, output) = commands.getstatusoutput(cmd)
            logging.debug('cmd: %s :: status: %d :: output %s',
                          cmd, status, output)
            retry -= 1
        if status:
            raise TPS65090Error('Non-zero status from i2c get returned '
                                'status:%d' % status)
        return output


    def get(self, index):
        """Get I2c value.

        Args:
          index: integer, register index to write byte to

        """
        cmd = '%s %d 0x%x 0x%x b' % (self._GET_CMD, self._bus, self._slv, index)
        output = self._do_cmd(cmd)
        return int(output, 0)


    def set(self, index, val):
        """Set I2c value.

        Args:
          index: integer, register index to write byte to
          val: integer, byte value to writ to index
        """
        cmd = '%s %d 0x%x 0x%x 0x%x' % \
            (self._SET_CMD, self._bus, self._slv, index, val)
        self._do_cmd(cmd)


class TPS65090ADC(object):
    """Class for TPS65090 ADC."""
    # Number of times to retry read of AD_CTRL for EOC
    _RETRY_MAX = 10


    def __init__(self, i2c, sensor_id):
        """."""
        self._i2c = i2c
        self._sensor_id = sensor_id


    def read_adc(self):
        """Read value for ADC.

        Steps required:
          1. Write ADC value into AD_CTRL[3:0]
          2. Enable measurement
          3. Poll conversion ready
          4. Read AD_OUT1
          5. Read AD_OUT2
          6. merge AD_OUT2[1:0] << 8 | AD_OUT1
          7. return 10bit * units_per_lsb

        Raises:
          TPS65090Error: if ADC conversion fails to complete
        """
        wr_val = AD_CTRL_EN | self._sensor_id
        self._i2c.set(REG_IDX_AD_CTRL, wr_val)
        wr_val |= AD_CTRL_START
        self._i2c.set(REG_IDX_AD_CTRL, wr_val)
        time.sleep(.01)

        rd_val = self._i2c.get(REG_IDX_AD_CTRL)
        retry = self._RETRY_MAX
        while retry and not (rd_val & AD_CTRL_EOC):
            time.sleep(.01)
            rd_val = self._i2c.get(REG_IDX_AD_CTRL)
            retry -= 1

        if not retry:
            raise TPS65090Error('Failed to see ADC conversion complete')

        rd_val1 = self._i2c.get(REG_IDX_AD_OUT1)
        rd_val2 = self._i2c.get(REG_IDX_AD_OUT2)
        adc_val = ((rd_val2 << 8) | rd_val1) * AD_OUT_LSB[self._sensor_id]
        logging.debug('adc%02d = %f', self._sensor_id, adc_val)
        return adc_val



class TPS65090Power(object):
    """Class for TPS65090 PMIC Power.

    Attributes:
      _i2c: object, TPS65090I2c instance to communicate to PMIC over I2c
      _voltage: list of voltages.  Either float or TPS65090ADC instances (for
        AC & battery)
      _current: list of currents.  All are TPS65090ADC instances
    """
    def __init__(self, i2c):
        """Constructor.

        Args:
          i2c: object, TPS65090I2c instance to communicate to PMIC over I2c
        """
        self._i2c = i2c
        self._voltage = {}
        self._current = {}

        val = self._i2c.get(REG_IDX_AD_CTRL)
        if val != AD_CTRL_POR:
            raise TPS65090Error('Unable to read POR value for AD_CTRL')
        self._i2c.set(REG_IDX_AD_CTRL, AD_CTRL_EN)


    def __del__(self):
        self._i2c.set(REG_IDX_AD_CTRL, AD_CTRL_POR)


    def register(self, default_current_name, new_name=None, voltage=None):
        """Register a power measurement.

        The TPS65090 provides two built-in power measurements by way
        of voltage and current measurements for the AC input and the
        battery charge.  The remaining 10 current sensors can be made
        to measure power with voltage provided.

        Args:
        default_current_name: string, current sensor default name per datasheet.
        new_name: string, name to call power measurement.  Defaults to
          default_current_name.
        voltage: float, value for potential of rail

        Raises:
          TPS65090Error: if voltage isn't provided for DCDC or FET sensors
        """
        sensor_id = AD_OUT_DEFAULT_NAMES.index(default_current_name)
        if not new_name:
            new_name = default_current_name

        if voltage is None:
            if sensor_id not in [2, 3]:
                raise TPS65090Error('Must provide nominal voltage')
            if sensor_id == 2:
                self._voltage[new_name] = TPS65090ADC(self._i2c, 0)
            else:
                self._voltage[new_name] = TPS65090ADC(self._i2c, 1)
        else:
            self._voltage[new_name] = float(voltage)

        self._current[new_name] = TPS65090ADC(self._i2c, sensor_id)
        logging.info('registered %s ( %s ) @ sensor %d', new_name,
                     default_current_name, sensor_id)



    def read_mw(self, name):
        """Read power in milliwatts.

        Returns:
          float, power in milliwatts

        Raises:
          TPS65090Error: if current ADC is unable to be found
        """
        if name not in self._current:
            raise TPS65090Error('Unable to measure current.  Did you '
                                'register the power?')

        if type(self._voltage[name]) is float:
            voltage = self._voltage[name]
        else:
            voltage = self._voltage[name].read_adc()
        current = self._current[name].read_adc()
        return current * voltage * 1000


def main():
    """main loop to read power."""
    logging.basicConfig(level=logging.INFO)
    logging.info('start')

    i2c = TPS65090I2c(4)
    pwr = TPS65090Power(i2c)

    pwr_names = []
    pwr.register('ac', new_name='ac_mw')
    pwr_names.append('ac_mw')
    pwr.register('bat', new_name='bat_mw')
    pwr_names.append('bat_mw')

    voltages = [5, 3.3, 1.35, 12, 5, 3.3, 3.3, 3.3, 3.3, 5]
    names = ['pp5000_aux', 'pp3300_aux', 'pp1350_ddr', 'bl', 'pp5000_video',
              'pp3300_wwan', 'pp3300_sdcard', 'pp3300_cam', 'pp3300_lcd',
              'pp5000_ts']

    for i, name in enumerate(AD_OUT_DEFAULT_NAMES[4:]):
        new_name = '%s_mw' % names[i]
        pwr.register(name, new_name=new_name, voltage=voltages[i])
        pwr_names.append(new_name)

    rails = pwr_names
    if len(sys.argv) > 1:
        rails = sys.argv[1:]

    stats = {}
    for name in rails:
        stats[name] = numpy.array([])

    while True:
        for name in rails:
            mw_val = pwr.read_mw(name)
            if len(stats[name]) == MAX_STATS:
                stats[name] = numpy.delete(stats[name], 0)
            stats[name] = numpy.append(stats[name], mw_val)
            print '%s:%.f' % (name, stats[name].mean())
        # delay in order to not raise power via the script
        # TODO(tbroch) sleep should be configureable
        time.sleep(2)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
