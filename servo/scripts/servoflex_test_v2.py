#!/usr/bin/env python
# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Script to test servoflex_v2 50 pin -> 42 pin flexes."""


import logging
import optparse
import os
import select
import subprocess
import sys
import time


def do_cmd(cmd, timeout, plist=None, flist=None):
    """Executes a shell command

    Method uses subprocess.Popen and select to provide a capture of stdout &
    stderr and non-blocking parsing of it for <timeout> seconds.  If <plist> or
    <flist> strings are seen command is deemed as passed or failed respectively.

    Args:
        cmd: string, command to execute
        timeout: float, time in seconds until command assumed to have timed out.
        plist:  list of strings, If one of these strings is found while parsing
          stdout | stderr, command deemed to have passed.
        flist:  list of strings, If one of these strings is found while parsing
          stdout | stderr, command deemed to have failed.

    Returns, 3 item tuple:
        retval: None|False|True, whether command passed, failed or wasn't
          determined
        obj: subprocess instance create by calling Popen.  This provides
          capabilities to keep daemons (servod, openocd) for more interaction
        str: string, of stdout + stderr which is determined by presence of
        absence of plist & flist.
    """
    logging.debug("cmd = %s", cmd)
    if type(cmd) is str:
        cmd = cmd.split()
    cmd_obj = subprocess.Popen(cmd, 0, None, None,
                               subprocess.PIPE, subprocess.PIPE)
    assert cmd_obj.stderr and cmd_obj.stdout, 'Failed to get stdout & stderr'
    start_time = time.time()
    all_str = ''
    while (time.time() - start_time) < timeout:
        if plist or flist:
            (rfds, _, _) = select.select([cmd_obj.stdout,
                                          cmd_obj.stderr], [], [], 0.01)
            if len(rfds) > 0:
                log_str = rfds[0].readline().rstrip()
                all_str = all_str + log_str + '\n'
                if len(log_str) > 0:
                    logging.debug("CMD_LOG: = %s", log_str)
                if flist:
                    for fail_str in flist:
                        if fail_str in log_str:
                            logging.error("FOUND: %s in %s", fail_str, log_str)
                            return (False, cmd_obj, log_str)
                if plist:
                    for pass_str in plist:
                        if pass_str in log_str:
                            logging.debug("FOUND: %s in %s", pass_str,
                                         log_str)
                            return (True, cmd_obj, log_str)
    if flist:
        return (True, cmd_obj, all_str)
    return (None, cmd_obj, all_str)


def set_ctrls(controls, timeout=0.2):
    """Set various servod controls.

    Returns retval output from do_cmd
    """
    cmd = 'dut-control %s' % controls
    (retval, _, _) = do_cmd(cmd, timeout, flist=['- ERROR -'])
    return retval


def get_ctrls(controls, timeout=0.2):
    """Get various servod controls."""
    get_dict = {}
    cmd = 'dut-control %s' % controls
    (retval, _, out) = do_cmd(cmd, timeout, flist=['- ERROR -'])
    if retval:
        for ctrl_line in out.split('\n'):
            ctrl_line = ctrl_line.strip()
            if len(ctrl_line):
                logging.debug('ctrl_line=%s', ctrl_line)
                (name, value) = ctrl_line.strip().split(':')
                get_dict[name] = value
        return (True, get_dict)
    return (False, get_dict)


# write the openocd cfg file
OPENOCD_PASS = ['tap/device found: 0xd5044093']
OPENOCD_FAIL = ['Error:']
OPENOCD_CFG = """
telnet_port 4444

interface ft2232
ft2232_layout jtagkey
ft2232_vid_pid 0x18d1 0x5002
jtag_khz 1000
# Xilinx XCF01S.  Note MSB nibble (0xd) is device revision and can change.
jtag newtap auto0 tap -irlen 16 -expected-id 0xd5044093
"""


# TODO(tbroch) Must sudo USE=ftdi emerge openocd
def test_jtag():
    """ Test JTAG interface.

    Returns True if passes, Fail otherwise
    """

    errors = 0
    on_ctrls = 'spi2_vref:pp3300 jtag_buf_en:on jtag_buf_on_flex_en:on'
    off_ctrls = 'spi2_vref:off jtag_buf_en:off jtag_buf_on_flex_en:off'

    if not set_ctrls(on_ctrls):
        logging.error('Enabling access to JTAG')
        set_ctrls(off_ctrls)
        return False

    fname = '/tmp/servoflex_test_openocd.cfg'
    fd = os.open(fname, os.O_WRONLY|os.O_CREAT)
    os.write(fd, OPENOCD_CFG)
    os.close(fd)
    cmd = 'sudo openocd -f %s' % fname
    (retval, openocd, _) = do_cmd(cmd, 10, plist=OPENOCD_PASS,
                              flist=OPENOCD_FAIL)

    if not retval:
        logging.error('Testing JTAG')
        errors += 1

    cmd = 'sudo kill %d' % openocd.pid
    subprocess.call(cmd, shell=True)
    # TODO(tbroch) should we stress jtag here?  Currently only get TAP's IDCODE

    if not set_ctrls(off_ctrls):
        logging.error('Disabling access to JTAG')
        errors += 1
    return (errors == 0)


FLASHROM_PASS = ['probe_spi_rems: id1 0xbf, id2 0x48']
FLASHROM_FAIL = None


def test_spi(dev_id):
    """ Test SPI interface.

    TODO(tbroch) actual part is SST25VF512A.  See about adding it
    officially to flashrom so we can do more than probe for it below

    Args:
      dev_id: integer, number corresponding to servod controls that operate this
        SPI interface.  Should be 1 | 2

    Returns True if passes, Fail otherwise
    """
    assert dev_id == 1 or dev_id == 2, 'SPI dev_id should be 1 | 2'
    errors = 0
    ctrls = 'spi%d_vref:pp3300 spi%d_buf_en:on ' % (dev_id, dev_id)
    ctrls += 'spi%d_buf_on_flex_en:on spi_hold:off' % (dev_id)

    if not set_ctrls(ctrls):
        logging.error('enabling access to spi %d', dev_id)
        return False

    cmd = 'sudo flashrom -V -p ft2232_spi:type=servo-v2'
    if dev_id == 1:
        cmd += ',port=b'
    cmd += ' -c SST25VF040'
    (retval, flash, _) = do_cmd(cmd, 5, plist=FLASHROM_PASS,
                            flist=FLASHROM_FAIL)
    if not retval:
        logging.error('reading eeprom for spi %d', dev_id)
        errors += 1

    ctrls = 'spi%d_vref:off spi%d_buf_en:off ' % (dev_id, dev_id)
    ctrls += 'spi%d_buf_on_flex_en:off spi_hold:off' % (dev_id)

    if not set_ctrls(ctrls):
        logging.error("disabling access to spi %d", dev_id)
        errors += 1

    flash.terminate()
    return (errors == 0)


def test_uart(dev_id):
    """ Test UART interface.

    Args:
      dev_id: integer, number corresponding to servod controls that operate this
        UART interface.  Should be 1 | 2

    Returns True if passes, Fail otherwise
    """
    errors = 0
    assert dev_id == 1 or dev_id == 2, 'UART dev_id should be 1 | 2'
    ctrls = "uart%d_en:on" % (dev_id)
    if not set_ctrls(ctrls):
        logging.error('Enabling access to UART %d', dev_id)
        return False

    ctrls = "uart%d_pty" % (dev_id)
    (retval, get_dict) = get_ctrls(ctrls)
    if not retval:
        logging.error('Retrieving pty to UART %d', dev_id)
        errors += 1

    if not errors:
        fd = os.open(get_dict['uart%d_pty' % dev_id], os.O_RDWR)
        send_str = 'hello %d' % dev_id
        os.write(fd, send_str)
        (rfds, _, _) = select.select([fd], [], [], 1)
        if len(rfds) > 0:
            rsp_str = os.read(fd, len(send_str))
            if rsp_str != send_str:
                logging.error('Sent != received for UART %d', dev_id)
                errors += 1
        else:
            logging.error('Nothing received for UART %d', dev_id)
            errors += 1
        os.close(fd)

    ctrls = "uart%d_en:off" % (dev_id)
    if not set_ctrls(ctrls):
        logging.error("Disabling access to UART %d", dev_id)
        errors += 1
    return (errors == 0)


GPIO_MAPS = {'off': 'on', 'on': 'off', 'press': 'release',
             'release': 'press', 'yes': 'no', 'no': 'yes'}

KBD_MUX_COL_IDX = ['kbd_m2_a', 'kbd_m1_a']

def test_kbd_gpios():
    """Test keyboard row & column GPIOs.

    Note, test only necessary on 50pin -> 50pin flex

    These must be tested differently than average GPIOs as the servo side logic,
    a 4to1 mux, is responsible for shorting colX to rowY where X == 1|2 and Y
    = 1|2|3.  To test the flex traces I'll set the row to both high and low
    and examine that the corresponding column gets shorted correctly.

    Returns:
      errors: integer, number of errors encountered while testing
    """
    errors = 0
    # disable everything initially
    kbd_off_cmd = 'kbd_m1_a0:1 kbd_m1_a1:1 kbd_m2_a0:1 kbd_m2_a1:1 kbd_en:off'
    for col_idx in xrange(2):
        if not set_ctrls(kbd_off_cmd):
            logging.error('Disabling all keyboard rows/cols')
            errors += 1
            break
        mux_ctrl = KBD_MUX_COL_IDX[col_idx]
        kbd_col = 'kbd_col%d' % (col_idx + 1)
        for row_idx in xrange(3):
            kbd_row = 'kbd_row%d' % (row_idx + 1)
            cmd = '%s1:%d %s0:%d ' % (mux_ctrl, row_idx>>1, mux_ctrl,
                                        row_idx & 0x1)
            cmd += 'kbd_en:on %s' % (kbd_col)
            (retval, ctrls) = get_ctrls(cmd)
            if not retval:
                logging.error('ctrls = %s', ctrls)
                errors += 1
            for set_val in [GPIO_MAPS[ctrls[kbd_col]], ctrls[kbd_col]]:
                cmd = '%s:%s sleep:0.2 %s' % (kbd_row, set_val, kbd_col)
                (retval, ctrls) = get_ctrls(cmd, timeout=1)
                if not retval:
                    logging.error('ctrls = %s', ctrls)
                    errors += 1
                if ctrls[kbd_col] != set_val:
                    logging.error('After setting %s, %s != %s', kbd_row,
                                  kbd_col, set_val)
                    errors += 1

    return errors


def test_gpios(pins):
    """Test GPIO's across the servoflex connector.

    The GPIO's are routed from the servo through the servoflex to the test
    fixture which has its own GPIOE expander to sense the values.  Test trys
    both the assertion and de-assertion of the GPIO

    Note,
      1. GPIO's pch_disable, lid_open, dev_mode kbd ctrls can only be tested
        if/when a test fixture w/ 50p connector is built.
      2. Testing sd_detect requires sd_vref_sel:pp3300 sd_en:on
      3. Testing mfg_mode requires spi2_vref:pp3300 fw_wp_en:on
      4. The GPIOE on test fixture has built-in pull-ups to correctly provide
      emulation of OD style GPIO's.

    Args:
      pins:  Number of pins flex has on DUT side

    Returns, True if passes, Fail otherwise
    """
    assert (pins == 50) or (pins == 42), 'Pins must be 42 | 50'
    gpio_prefix = ['test_']
    if (pins == 50):
      gpio_prefix.append('test50_')

    errors = 0
    cmd = 'i2c_mux_en:on i2c_mux:rem '
    cmd += 'sd_vref_sel:pp3300 sd_en:on '
    cmd += 'spi2_vref:pp3300 fw_wp_en:on '
    if not set_ctrls(cmd):
        logging.error('Steering i2c mux to remote')
        return False
    (retval, all_ctrls) = get_ctrls('', timeout=1)
    if not retval:
        logging.error('Getting all ctrls')
        return False
    gpios_to_test = {}
    for ctrl_name in all_ctrls:
        for prefix in gpio_prefix:
            if ctrl_name.startswith(prefix):
                (_, real_gpio) = ctrl_name.split(prefix)
                gpios_to_test[real_gpio] = ctrl_name

    for _ in xrange(2):
        for set_name, get_name in gpios_to_test.iteritems():
            set_val = GPIO_MAPS[all_ctrls[set_name]]
            logging.debug("%s %s -> %s", set_name,
                          all_ctrls[set_name], set_val)
            (retval, ctrl) = get_ctrls('%s:%s %s' % (set_name, set_val,
                                                     get_name))
            if not retval:
                logging.error('Getting GPIO %s', get_name)
                errors += 1
            else:
                if ctrl[get_name] != set_val:
                    logging.error('GPIO %s from %s -> %s', set_name,
                                  all_ctrls[set_name], set_val)
                    errors += 1
                else:
                    logging.info('GPIO %s from %s -> %s', set_name,
                                 all_ctrls[set_name], set_val)

            all_ctrls[set_name] = set_val

    if pins == 50:
        errors += test_kbd_gpios()

    cmd = 'i2c_mux_en:off i2c_mux:rem '
    cmd += 'sd_vref_sel:off sd_en:off '
    cmd += 'spi2_vref:off fw_wp_en:off'
    if not set_ctrls(cmd):
        logging.error('Disabling i2c mux to remote')
        errors += 1

    return (errors == 0)


# TODO(tbroch) determine version string methodology.
VERSION = "0.0.1"


def parse_args():
    description = ('')
    examples = ('')
    parser = optparse.OptionParser(version="%prog "+VERSION)
    parser.description = description
    parser.add_option("-d", "--debug", action="store_true", default=False,
                      help="enable debug messages")
    parser.add_option("-p", "--pins", type=int, default=42,
                      help="Pin width of flex on DUT side.  Either 42 | 50")
    parser.set_usage(parser.get_usage() + examples)
    return parser.parse_args()


def main():
    errors = 0
    (options, _) = parse_args()
    loglevel = logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s'
    if options.debug:
        loglevel = logging.DEBUG
        log_format += " - %(filename)s:%(lineno)d:%(funcName)s"

    log_format += " - %(message)s"
    logging.basicConfig(level=loglevel, format=log_format)

    cmd = 'sudo pkill servod'
    subprocess.call(cmd, shell=True)
    # launch servod
    cmd = 'sudo servod -c servoflex_test_v2.xml'
    (retval, servod, _) = do_cmd(cmd, 3, plist=['Listening'])
    if retval:
        logging.info('Started servod')
        for test in ['gpios(%d)' % options.pins, 'jtag()', 'uart(1)', 'uart(2)',
                     'spi(1)', 'spi(2)']:
            logging.info("Start  Test -> %s", test)

            retval = eval('test_%s' % test)
            if not retval:
                logging.error('%s FAILED', test)
                errors += 1
            logging.info("Finish Test -> %s", test)
    else:
        logging.error('Servod launch failed')
        errors += 1

    cmd = 'sudo kill %d' % servod.pid
    subprocess.call(cmd, shell=True)
    return (errors == 0)


if __name__ == '__main__':
    try:
        if not main():
            sys.exit(-1)
    except KeyboardInterrupt:
        sys.exit(0)
