// Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

/*    Toad Utility -- The USB micro dev companion.
 *
 * If you just want an EC or AP serial console, you do not need this tool.
 * The ftdi_sio module will expose the serial device which you can use normally.
 * Press the button on the device to switch between EC and AP consoles.
 *
 * This utility lets you control the additional capabilites of Toad.
 * You can:
 *   > Switch the console endpoint (EC or AP) via software and/or monitor it
 *   > Enable the EC boot mode and upload code (unless the RO screw is present)
 *   > Toggle the VBUS to the DUT to simulate connect/disconnect
 *   > Initialize Toad when it's fresh out of the factory
 *
 * Building is easy, just run "make", and optionally "sudo make install".
 * i386, x86_64, and 32-bit ARM architectures should all work with this tool.
 */

static const char *USAGE =
"command [options]\n"
"\n"
"Options:\n"
"    -s SN              - Specifies the Toad you want to communicate with, by\n"
"    --serialname=SN      serial. If unspecified, the tool will use the first\n"
"                         Toad found. If SN is left empty (long form only) or\n"
"                         set to \"all\", all connected Toads will be used in\n"
"                         batch operations.\n"
"    -f                 - Forces a command. Specify multiple times to apply\n"
"                         more force. Currently only used with initialize.\n"
"\n"
"Commands:\n"
"    list               - Prints out the serial.\n"
"    initialize         - Initializes the Toad EEPROM.\n"
"                         Use -f to re-program programmed Toad devices.\n"
"                         Use -f twice to re-program devices that are not\n"
"                         recognized as a Toad. (Use with -s; dangerous.)\n"
"    status             - Prints the full state: VBUS, EC/AP, boot states.\n"
"    setvbus STATE      - Sets or toggles VBUS, where STATE can be one of\n"
"                         on, off, or toggle.\n"
"    setecap STATE      - Sets the EC/AP target mode, where STATE can be one\n"
"                         of ec, ap, or toggle.\n"
"    setboot STATE      - Sets the boot override mode, where STATE can be one\n"
"                         of on, off, or toggle.\n"
"    getmode            - Gets the current effective mode: off, ec, ap, boot.\n"
"    setmode MODE       - Sets the effective mode, where MODE can be one of\n"
"                         off, ec, ap, or boot.\n"
"    boot [FILE]        - Boots the EC using the specified binary.\n"
"                         Uses stdin if FILE is left unspecified.\n";
static const char *CONSOLE =
"    console            - Opens a console to the DUT without switching modes.\n"
"    ec                 - Switches to EC mode and opens a console.\n"
"    ap                 - Switches to AP mode and opens a console.\n";
static const char *ESCAPES =
"Console escapes: prefix with ^X (Ctrl-X)\n"
"    h, H, ^H  (Ctrl-H) - Print out supported escapes (this message).\n"
"    ^X  (Ctrl-X)       - Send a literal ^X\n"
"    ^C  (Ctrl-C)       - Close the console. Returns a failure exit code.\n"
"    ^D  (Ctrl-D)       - Close the console.\n"
"    ^Z  (Ctrl-Z)       - Suspend the console into the background.\n"
"    e, E, ^E  (Ctrl-E) - Switch to monitoring the EC output.\n"
"    a, A, ^A  (Ctrl-A) - Switch to monitoring the AP output.\n"
"    p, P, ^P  (Ctrl-P) - Switch to monitoring the AP output.\n";


#include <errno.h>
#include <getopt.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>

#include "toad.h"

#if NEW_LIBFTDI
#   pragma GCC diagnostic ignored "-Wcast-align"
#   include <libusb.h>
#   pragma GCC diagnostic pop
#endif


/* Options for passing into getopt_long */
static const char *SHORT_OPTS = "s:f";
static const struct option LONG_OPTS[] = {
    { "serialname", required_argument, NULL, 's' },
    { NULL, 0, NULL, 0 }  // end-of-list sentinel
};

/* Commands and their dispatch functions */
static const struct cmd COMMAND_LIST[] = {
    { "list", cmdList },
    { "init", cmdInitialize },
    { "initialize", cmdInitialize },
    { "st", cmdStatus },
    { "status", cmdStatus },
    { "vbus", cmdSetVbus },
    { "setvbus", cmdSetVbus },
    { "ecap", cmdSetEcAp },
    { "setecap", cmdSetEcAp },
    { "setboot", cmdSetBoot },
    { "getmode", cmdGetMode },
    { "setmode", cmdSetMode },
    { "mode", cmdMode },
    { "boot", cmdBoot },
#if ENABLE_CONSOLE
    { "console", cmdConsole },
    { "ec", cmdEc },
    { "ap", cmdAp },
#endif
    { NULL, NULL }  // end-of-list sentinel
};


/* Config data at start of FT230X EEPROM for programming */
static const unsigned char TOAD_EEPROM_00[] = {
    /* 00 */ 0x00, 0x00,  // First two bytes must be zero
    /* 02 */ TOAD_VID & 0xFF, TOAD_VID >> 8,
    /* 04 */ TOAD_PID & 0xFF, TOAD_PID >> 8,
    /* 06 */ 0x00, 0x10,  // bcdDevice
    /* 08 */ 0x80,  // bus powered
    /* 09 */ 0xFA,  // 500 mA (2mA increments)
    /* 0A */ 0x08,  // Max packet size
    /* 0B */ 0x00, 0x00, 0x00,  // bDeviceClass/bDeviceSubClass/bDeviceProtocol
    /* 0E */ TOAD_EEPROM_MANUFACTURER_START, sizeof(TOAD_MANUFACTURER) * 2,
    /* 10 */ TOAD_EEPROM_DESC_START, sizeof(TOAD_DESC) * 2,
    /* 12 */ TOAD_EEPROM_SERIAL_START, 0,  // we don't know the size yet
    /* 14 */ 0x00, 0x00, 0x00,  // AC are normal skew, no schmitt, 4mA drive
    /* 17 */ 0x00, 0x00, 0x00,  // AD are normal skew, no schmitt, 4mA drive
    /* 20 */ CBUSH_IOMODE, CBUSH_IOMODE, CBUSH_IOMODE, CBUSH_IOMODE,  // Cbus0-3
    /* 24 */ CBUSH_TRISTATE, CBUSH_TRISTATE, CBUSH_TRISTATE,  // Cbus4-6
    /* 27 */ 0, 0, 0, 0,  // Do not invert TXD, RXD, RTS, CTS
    /* 2B */ 0, 0, 0, 0,  // Do not invert DTR, DSR, DCD, RI
    /* 2F */ 0, 0, 0,  // No battery charge detect, disable BCD pin, keep awake
    /* 32 */ 0, 0, 0,  // No I2C address, no device ID, no schmitt trigger
    /* 35 */ 0, 0, 0,  // Not an FT1248 (clock polarity, data endianness, flow)
    /* 38 */ 0, 0, 0,  // No RS485 echo suppression, no power save, D2XX driver
};


/* Entry-point.
 * Processes global options, determines the command, and hands off to the
 * command dispatcher (runCmd).
 *
 * returns: zero on success, non-zero on error.
 */
int main(int argc, char **argv) {
    const char *device = NULL, *command = NULL, *option = NULL;
    const struct cmd *curCmd = NULL;
    int force = 0;
    int c;

    if (argc == 1) {
        // Print usage and quit if there are no arguments.
        if (ENABLE_CONSOLE) {
            fprintf(stderr, "Usage: %s %s%s\n%s",
                    argv[0], USAGE, CONSOLE, ESCAPES);
        } else {
            fprintf(stderr, "Usage: %s %s", argv[0], USAGE);
        }
        return 1;
    }

    while ((c = getopt_long(argc, argv, SHORT_OPTS, LONG_OPTS, NULL)) != -1) {
        if (c == 's') {
            if (device) {
                ERR(1, "Only one serial may be specified at a time.");
            }
            // "all" is equivalent to an empty string.
            device = strcmp("all", optarg) ? optarg : "";
        } else if (c == 'f') {
            force++;
        } else {
            return 1;
        }
    }

    // Grab command
    if (optind < argc) {
        command = argv[optind++];
    } else {
        ERR(1, "Please specify a command.");
    }

    // Grab option
    if (optind < argc) {
        option = argv[optind++];
    }

    if (optind < argc) {
        ERR(1, "Too many parameters.");
    }

    // Hand off to the proper function.
    for (curCmd = COMMAND_LIST; curCmd->name; ++curCmd) {
        if (!strcmp(command, curCmd->name)) {
            return runCmd(curCmd->func, device, option, force);
        }
    }
    ERR(1, "Unrecognized command.");
}


/* Switches the TTY into raw mode and back (if it's a TTY)
 * In raw mode, characters are passed through as they are typed (instead of
 * line-based editing), and are not automatically echoed back out on the TTY.
 *
 * enable: non-zero to enable, zero to disable.
 * returns: zero on success, non-zero on error, or if stdin is not a TTY.
 */
int ttyRawMode(int enable) {
    static int rawmode = 0;
    static struct termios orig;
    if (!isatty(STDIN_FILENO)) {
        return -1;
    }

    if (enable == rawmode) {
        return 0;
    }

    if (enable) {
        struct termios raw;
        if (tcgetattr(STDIN_FILENO, &orig) < 0) {
            return -1;
        }
        raw = orig;
        cfmakeraw(&raw);
        raw.c_cc[VMIN] = 0;
        raw.c_cc[VTIME] = 0;
        if (tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw) < 0) {
            return -1;
        }
    } else {
        if (tcsetattr(STDIN_FILENO, TCSAFLUSH, &orig) < 0) {
            return -1;
        }
        // Ensure that the cursor is at a new line.
        fputc('\n', stderr);
    }
    rawmode = enable;
    return 0;
}


/* Configures UART settings, using the constants specified above.
 *
 * returns: zero on success; non-zero on error. */
int ftdiConfigure(struct ftdi_context *ftdi) {
    unsigned char latency;

    FTORDIE(ftdi_set_baudrate(ftdi, TOAD_BAUD));
    FTORDIE(ftdi_set_line_property(ftdi, TOAD_LINE_PROPERTY));
    FTORDIE(ftdi_setflowctrl(ftdi, TOAD_FLOW_CONTROL));

    /* HACK: After the FTDI chip comes out of reset, ftdi_read_pins doesn't
     * return sensible results until ftdi_set_bitmode has been called to set the
     * mode to bit-bang. Since we don't want to wipe the boot/vbus state every
     * time we run the tool, we store some state on the FT230X to see if we've
     * initialized it or not.  Unfortunately, the only volatile state accessible
     * is the latency timer, which is initially 16ms. Thus we check the latency
     * timer and call ftdi_set_bitmode if it is not our custom value. The custom
     * value can be anything (we don't care too much about the buffer timeout
     * latency), as long as it's not 16.
     */
    FTORDIE(ftdi_get_latency_timer(ftdi, &latency));
    if (latency != TOAD_LATENCY_TIMER) {
        FTORDIE(ftdi_set_bitmode(ftdi, 0x00, BITMODE_CBUS));
        FTORDIE(ftdi_set_latency_timer(ftdi, TOAD_LATENCY_TIMER));
    }
    return 0;
}


/* Opens FT230X devices and runs the specified command.
 *
 * If no device is specified, opens the first device with the correct
 * description; this is either the generic FT230X description (in the case of
 * the initialize command), or Toad's unique description.
 *
 * If device is specified but blank, operates on all devices that match the
 * appropriate description.
 *
 * If device is specified and non-empty, opens the first device with the
 * matching serial.
 *
 * cmd: the function to call on each device opened.
 * device: the device specified as a command line flag, or NULL if --device was
 *         not provided.
 * option: an additional parameter if provided by the user.
 * returns: zero on success, non-zero on error.
 */
int runCmd(cmd_func cmd, const char *device, const char *option, int force) {
    int ret = 0;
    struct ftdi_context *ftdi = ftdi_new();
    const char *desc = TOAD_DESC;
    struct ftdi_device_list *list, *cur;
    unsigned int i, count, num_valid = 0, num_failed_to_open = 0;
    int all = 0, check_desc = 1;

    // If we're initializing (and there's no force), look for generic parts.
    // If we are 2x forcing, don't even bother checking desc.
    if (cmd == cmdInitialize) {
        if (!force) {
            desc = FTDI_DESC;
        } else if (force >= 2) {
            check_desc = 0;
        }
    }

    // If device is provided but blank, process all devices.
    if (device && !*device) {
        all = 1;
    }

    // Get the list of devices
    FTORDIE(count = ftdi_usb_find_all(ftdi, &list, TOAD_VID, TOAD_PID));

    // Go through each one and operate on them individually.
    for (i = 0, cur = list; i < count && cur; ++i, cur = cur->next) {
        char cur_desc[64], cur_serial[64];
        int result;
        // If we've specified a device, make sure it matches that.
        // If the device doesn't match and we're operating on all, explain why.
        if (ftdi_usb_get_strings(ftdi, cur->dev, NULL, 0,
                                 cur_desc, sizeof(cur_desc),
                                 cur_serial, sizeof(cur_serial)) < 0) {
            if (all) {
                prn_error("%u: unable to query device.", i);
            }
        } else if (check_desc && strcmp(cur_desc, desc)) {
            if (all) {
                if (!strcmp(cur_desc, FTDI_DESC)) {
                    prn_error("%u (%s): unprogrammed, or generic part.",
                              i, cur_serial);
                } else if (!strcmp(cur_desc, TOAD_DESC)) {
                    prn_error("%u (%s): already programmed.", i, cur_serial);
                } else {
                    prn_error("%u: incorrect description (\"%s\").",
                              i, cur_desc);
                }
            }
        } else if (!all && device && strcmp(cur_serial, device)) {
            // Didn't match the specified device serial.
        } else if ((result = ftdi_usb_open_dev(ftdi, cur->dev)) < 0) {
            num_failed_to_open++;
            if (all) {
                prn_error("%u (%s): %s",
                          i, cur_serial, ftdi_get_error_string(ftdi));
            }
        } else {
            // Matched! Do the proccessing.
            num_valid++;
            if (all) {
                prn_info("%u (%s): processing...", i, cur_serial);
            }
            result = ftdiConfigure(ftdi);
            if (!result) result = (*cmd)(ftdi, option, force);
            ftdi_usb_close(ftdi);
            if (all && !result) {
                prn_info("%u (%s): success.", i, cur_serial);
            } else if (!ret) {
                ret = result;
            }
            if (!all) {
                break;
            }
        }
    }
    // Clean up, and notify the user if there were no devices
    ftdi_list_free(&list);
    ftdi_free(ftdi);
    if (!num_valid) {
        if (!ret) ret = 2;
        if (num_failed_to_open) {
            prn_error("Failed to open %u devices.", num_failed_to_open);
        } else {
            prn_error("No valid devices found.");
        }
    } else if (all) {
        prn_info("Processed %u devices.", num_valid);
    }

    return ret;
}


/* Sets the CBUS pins to the specified values, keeping others the same.
 *
 * For boot_mode and vbus_en, the special value SET_CBUS_KEEP can be specified
 * to keep the value at the same state that it presently is.
 * WARNING: passing SET_CBUS_KEEP to mode_sw is unsafe (since the user may be
 *          pressing the button), so this is not allowed.
 *
 * boot_mode: set to 1 to enable EC boot mode. This has higher precedence than
 *            EC/AP mode, but lower precedence than disabling VBUS.
 * vbus_en: set to 1 to enable VBUS to the DUT. If VBUS is disabled, all modes
 *          are overridden with "off".
 * mode_sw: set to 1 to assert the mode switch button, toggling the EC/AP mode.
 *          This is the same line that the user uses (via a physical button), so
 *          be sure to de-assert it once the mode switches.
 * returns: zero on success, non-zero on error.
 */
int setCbus(struct ftdi_context *ftdi, int boot_mode,
            int vbus_en, int mode_sw) {
    unsigned char mode, mask;
    FTORDIE(ftdi_read_pins(ftdi, &mode));
    if (vbus_en == SET_CBUS_KEEP) {
        vbus_en = ((mode & BIT_VBUS_EN_MASK) != 0);
    }
    if (boot_mode == SET_CBUS_KEEP) {
        boot_mode = !(mode & BIT_BOOT_MODE_L_MASK);
    }
    if (mode_sw == SET_CBUS_KEEP) {
        ERR(254, "mode_sw should never be set to SET_CBUS_KEEP in setCbus");
    }
    mask = (vbus_en ? BIT_VBUS_EN_ASSERT : BIT_VBUS_EN_DEASSERT)
         | (boot_mode ? BIT_BOOT_MODE_L_ASSERT : BIT_BOOT_MODE_L_DEASSERT)
         | (mode_sw ? BIT_MODE_SW_L_ASSERT : BIT_MODE_SW_L_DEASSERT)
         | BIT_AP_MODE_EC_MODE_L_INPUT;
    FTORDIE(ftdi_set_bitmode(ftdi, mask, BITMODE_CBUS));
    return 0;
}


/* Sets the ec/ap mode by pressing the button and checking the result.
 * Does not affect boot or vbus states.
 *
 * ec: set to 1 to change to EC mode, 0 to change to AP mode, or
 *     SET_EC_AP_TOGGLE to toggle the current mode.
 * returns: zero on success, non-zero on error.
 */
int setEcAp(struct ftdi_context *ftdi, int ec) {
    int ret;
    unsigned char mode;
    FTORDIE(ftdi_read_pins(ftdi, &mode));
    // Check if the button is held down. If so, make sure we're not the ones
    // holding it down, then alert the user and wait for it to be released.
    if (!(mode & BIT_MODE_SW_L_MASK)) {
        ret = setCbus(ftdi, SET_CBUS_KEEP, SET_CBUS_KEEP, 0);
        if (ret) return ret;
        FTORDIE(ftdi_read_pins(ftdi, &mode));
        if (!(mode & BIT_MODE_SW_L_MASK)) {
            prn_warn("The mode button is pressed. Please release it.");
            while (!(mode & BIT_MODE_SW_L_MASK)) {
                FTORDIE(ftdi_read_pins(ftdi, &mode));
            }
            prn_info("The mode button has been released. Thank you.");
        }
    }
    // If we requested a toggle, update ec to our target value.
    if (ec == SET_EC_AP_TOGGLE) {
        ec = ((mode & BIT_AP_MODE_EC_MODE_L_MASK) != 0);
    }
    // See if the mode even needs to be toggled.
    if (!(mode & BIT_AP_MODE_EC_MODE_L_MASK) != ec) {
        // Press the button and wait for the mode to switch.
        ret = setCbus(ftdi, SET_CBUS_KEEP, SET_CBUS_KEEP, 1);
        if (ret) return ret;
        // Wait for mode to change.
        while (!(mode & BIT_AP_MODE_EC_MODE_L_MASK) != ec) {
            FTORDIE(ftdi_read_pins(ftdi, &mode));
        }
        // Release the button.  All done!
        return setCbus(ftdi, SET_CBUS_KEEP, SET_CBUS_KEEP, 0);
    } else {
        // We're already in the right state.
        return 0;
    }
}


/* Rewrites the EEPROM of the FT230X with the settings for Toad.
 *
 * option: no options allowed.
 * force: the user-specified force; non-zero forces operation by ignoring some
 *        sanity checks. >=1 allows rewriting an already-programmed Toad, and
 *        >=2 allows rewriting something totally unrecognized.
 * returns: zero on success, non-zero on error.
 */
int cmdInitialize(struct ftdi_context *ftdi UNUSED_ON_OLD_LIBFTDI,
                  const char *option UNUSED_ON_OLD_LIBFTDI,
                  int force UNUSED_ON_OLD_LIBFTDI) {
#if NEW_LIBFTDI
    struct libusb_device_descriptor desc;
    int detected;
    unsigned char serial[16];
    int serial_size;
    unsigned char data[TOAD_EEPROM_SIZE];
    size_t i;
    uint16_t checksum;

    NO_OPTIONS(option);

    // Determine device type; assume the device doesn't match
    detected = 2;
    FTORDIE(libusb_get_device_descriptor(
                libusb_get_device(ftdi->usb_dev), &desc));
    if (desc.idVendor == TOAD_VID && desc.idProduct == TOAD_PID) {
        unsigned char product[64];
        FTORDIE(libusb_get_string_descriptor_ascii(
                    ftdi->usb_dev, desc.iProduct, product, sizeof(product)));
        if (!strcmp((char*)product, FTDI_DESC)) {
            detected = 0;
        } else if (!strcmp((char*)product, TOAD_DESC)) {
            detected = 1;
        }
    }

    // Stop if we have insufficient force.
    if (detected > force) {
        if (detected == 1) {
            ERR(2, "Avoiding re-programming part; specify -f to force.");
        } else {
            ERR(2, "Avoiding programming random device; specify -ff to force.");
        }
    }

    // Get serial and print it out
    FTORDIE(serial_size = libusb_get_string_descriptor_ascii(
                ftdi->usb_dev, desc.iSerialNumber, serial, sizeof(serial)));
    // Make sure that our serial_size counts the null byte, like sizeof
    if (serial[serial_size - 1])
        serial_size++;
    // Update the manufacturer ID
    serial[0] = TOAD_MANUFACTURER_ID[0];
    serial[1] = TOAD_MANUFACTURER_ID[1];
    prn_info("Initializing device %s", serial);

    // Initialize the EEPROM part of libftdi. We don't actually use the stuff it
    // initializes, but without this initialization, ftdi_eeprom_write will not
    // function.
    FTORDIE(ftdi_eeprom_initdefaults(ftdi, NULL, NULL, NULL));

    // Grab the EEPROM data
    FTORDIE(ftdi_read_eeprom(ftdi));
    FTORDIE(ftdi_get_eeprom_buf(ftdi, data, sizeof(data)));

    // Overwrite the header information
    memcpy(data, TOAD_EEPROM_00, sizeof(TOAD_EEPROM_00));

    // Fix up the serial size
    data[TOAD_EEPROM_00_SERIAL_SIZE_OFFSET] = serial_size * 2;

    // Rewrite the manufacturer descriptor
    data[TOAD_EEPROM_MANUFACTURER_START + 0] = sizeof(TOAD_MANUFACTURER) * 2;
    data[TOAD_EEPROM_MANUFACTURER_START + 1] = TOAD_EEPROM_STRING_DESCRIPTOR;
    for (i = 1; i < sizeof(TOAD_MANUFACTURER); ++i) {
        data[TOAD_EEPROM_MANUFACTURER_START + i*2 + 0] = TOAD_MANUFACTURER[i-1];
        data[TOAD_EEPROM_MANUFACTURER_START + i*2 + 1] = 0;
    }

    // Rewrite the description descriptor
    data[TOAD_EEPROM_DESC_START + 0] = sizeof(TOAD_DESC) * 2;
    data[TOAD_EEPROM_DESC_START + 1] = TOAD_EEPROM_STRING_DESCRIPTOR;
    for (i = 1; i < sizeof(TOAD_DESC); ++i) {
        data[TOAD_EEPROM_DESC_START + i*2 + 0] = TOAD_DESC[i-1];
        data[TOAD_EEPROM_DESC_START + i*2 + 1] = 0;
    }

    // Rewrite the serial descriptor
    data[TOAD_EEPROM_SERIAL_START + 0] = serial_size * 2;
    data[TOAD_EEPROM_SERIAL_START + 1] = TOAD_EEPROM_STRING_DESCRIPTOR;
    for (i = 1; i < (size_t)serial_size; ++i) {
        data[TOAD_EEPROM_SERIAL_START + i*2 + 0] = serial[i-1];
        data[TOAD_EEPROM_SERIAL_START + i*2 + 1] = 0;
    }

    // Zero out everything afterwards
    i = TOAD_EEPROM_SERIAL_START + serial_size * 2;
    memset(&data[i], 0, sizeof(data) - i);

    // Calculate and fill in the checksum (algorithm from libftdi's ftdi.c)
    checksum = TOAD_EEPROM_CHECKSUM_SEED;
    for (i = 0; i < TOAD_EEPROM_CHECKSUM_OFFSET; i+=2) {
        checksum = (data[i] | (data[i+1] << 8)) ^ checksum;
        checksum = (checksum << 1) | (checksum >> 15);
    }
    data[TOAD_EEPROM_CHECKSUM_OFFSET + 0] = checksum & 0xFF;
    data[TOAD_EEPROM_CHECKSUM_OFFSET + 1] = checksum >> 8;

    // Write back to the device
    FTORDIE(ftdi_set_eeprom_buf(ftdi, data, sizeof(data)));
    FTORDIE(ftdi_write_eeprom(ftdi));

    // Reset the port to reload the configuration
    libusb_reset_device(ftdi->usb_dev);

    return 0;
#else  // if NEW_LIBFTDI
    ERR(1, "initialize command is not supported with libftdi 0.x");
#endif  // if NEW_LIBFTDI
}


/* Prints out the serial on stdout, in a format compatible with "eval".
 *
 * option: no options allowed.
 * force: not applicable.
 * returns: zero on success, non-zero on error.
 */
int cmdList(struct ftdi_context *ftdi, const char *option, int force UNUSED) {
    unsigned char serial[16];
    struct libusb_device_descriptor desc;

    NO_OPTIONS(option);

    FTORDIE(libusb_get_device_descriptor(
                libusb_get_device(ftdi->usb_dev), &desc));
    FTORDIE(libusb_get_string_descriptor_ascii(
                ftdi->usb_dev, desc.iSerialNumber, serial, sizeof(serial)));
    fprintf(stdout, "serial='%s'\n", serial);
    return 0;
}


/* Prints full device state, in a format compatible with "eval".
 *
 * option: no options allowed.
 * force: not applicable.
 * returns: zero on success, non-zero on error.
 * */
int cmdStatus(struct ftdi_context *ftdi, const char *option, int force UNUSED) {
    unsigned char mode;

    NO_OPTIONS(option);

    FTORDIE(ftdi_read_pins(ftdi, &mode));
    fprintf(stdout, "vbus='%s'\necap='%s'\nboot='%s'\nmodesw='%s'\n",
            (mode & BIT_VBUS_EN_MASK) ? "on" : "off",
            (mode & BIT_AP_MODE_EC_MODE_L_MASK) ? "ap" : "ec",
            (mode & BIT_BOOT_MODE_L_MASK) ? "off" : "on",
            (mode & BIT_MODE_SW_L_MASK) ? "off" : "pushed");
    return 0;
}


/* Processes option parameter string for "on"/"off"/"toggle".
 * Returns whether the new state should be asserted or deasserted.
 * Properly handles inversion of the active-low inputs in toggle mode.
 *
 * option: the user-supplied option string, either "on", "off", or "toggle".
 * mask: a single BIT_*_MASK value that denotes the option to be set.
 * enable: returns the new value for the output.
 * returns: zero on success, non-zero on error.
 */
int parseOnOffToggle(struct ftdi_context *ftdi, const char *option,
                     unsigned char mask, int *enable) {
    NEEDS_OPTION(option);
    if (!strcmp(option, "on")) {
        *enable = 1;
    } else if (!strcmp(option, "off")) {
        *enable = 0;
    } else if (!strcmp(option, "toggle")) {
        unsigned char mode;
        FTORDIE(ftdi_read_pins(ftdi, &mode));
        *enable = !(mode & mask);
        // The other masks are active low, so invert.
        if (mask != BIT_VBUS_EN_MASK) {
            *enable = !*enable;
        }
    } else {
        ERR(1, "Unrecognized option.");
    }
    return 0;
}


/* Sets or toggles vbus.
 *
 * option: the user-supplied option string, either "on", "off", or "toggle".
 * force: not applicable.
 * returns: zero on success, non-zero on error.
 */
int cmdSetVbus(struct ftdi_context *ftdi, const char *option,
               int force UNUSED) {
    int enable;
    int ret = parseOnOffToggle(ftdi, option, BIT_VBUS_EN_MASK, &enable);
    return ret ? ret : setCbus(ftdi, SET_CBUS_KEEP, enable, 0);
}


/* Sets or toggles the ec/ap mode.
 *
 * option: the user-supplied option string, either "ec", "ap", or "toggle".
 * force: not applicable.
 * returns: zero on success, non-zero on error.
 */
int cmdSetEcAp(struct ftdi_context *ftdi, const char *option,
               int force UNUSED) {
    NEEDS_OPTION(option);
    if (!strcmp(option, "ec")) {
        return setEcAp(ftdi, 1);
    } else if (!strcmp(option, "ap")) {
        return setEcAp(ftdi, 0);
    } else if (!strcmp(option, "toggle")) {
        return setEcAp(ftdi, SET_EC_AP_TOGGLE);
    } else {
        ERR(1, "Unrecognized option.");
    }
}


/* Sets or toggles boot mode.
 *
 * option: the user-supplied option string, either "on", "off", or "toggle".
 * force: not applicable.
 * returns: zero on success, non-zero on error.
 */
int cmdSetBoot(struct ftdi_context *ftdi, const char *option,
               int force UNUSED) {
    int enable;
    int ret = parseOnOffToggle(ftdi, option, BIT_BOOT_MODE_L_MASK, &enable);
    return ret ? ret : setCbus(ftdi, enable, SET_CBUS_KEEP, 0);
}


/* Sets or gets the effective mode.
 *
 * option: if empty, outputs the current mode on stdout. Otherwise, it is the
 *         mode to change to; see cmdSetMode.
 * force: passed to cmdSetMode/cmdGetMode.
 * returns: zero on success, non-zero on error.
 */
int cmdMode(struct ftdi_context *ftdi, const char *option, int force) {
    if (option && *option) {
        return cmdSetMode(ftdi, option, force);
    } else {
        return cmdGetMode(ftdi, option, force);
    }
}


/* Prints the effective mode to stdout, in a format compatible with "eval".
 *
 * option: no options allowed.
 * force: not applicable.
 * returns: zero on success, non-zero on error.
 */
int cmdGetMode(struct ftdi_context *ftdi, const char *option,
               int force UNUSED) {
    unsigned char mode;
    const char *name;

    NO_OPTIONS(option);

    FTORDIE(ftdi_read_pins(ftdi, &mode));
    if (!(mode & BIT_VBUS_EN_MASK)) {
        name = "off";
    } else if (!(mode & BIT_BOOT_MODE_L_MASK)) {
        name = "boot";
    } else if (!(mode & BIT_AP_MODE_EC_MODE_L_MASK)) {
        name = "ec";
    } else {
        name = "ap";
    }
    fprintf(stdout, "mode='%s'\n", name);
    return 0;
}


/* Sets the effective mode explicitly.
 * Changes VBUS_EN, BOOT_MODE, and toggles the MODE_SW as appropriate.
 *
 * option: the user-supplied option string, either "off", "boot", "ec", or "ap".
 * force: not applicable.
 * returns: zero on success, non-zero on error.
 */
int cmdSetMode(struct ftdi_context *ftdi, const char *option,
               int force UNUSED) {
    NEEDS_OPTION(option);
    if (!strcmp(option, "off")) {
        return setCbus(ftdi, SET_CBUS_KEEP, 0, 0);
    } else if (!strcmp(option, "boot")) {
        return setCbus(ftdi, 1, 1, 0);
    } else if (!strcmp(option, "ec")) {
        int ret = setCbus(ftdi, 0, 1, 0);
        return ret ? ret : setEcAp(ftdi, 1);
    } else if (!strcmp(option, "ap")) {
        int ret = setCbus(ftdi, 0, 1, 0);
        return ret ? ret : setEcAp(ftdi, 0);
    } else {
        ERR(1, "Unrecognized option.");
    }
}


#if NEW_LIBFTDI
/* Grabs all available input from FTDI and outputs on stdout without blocking.
 * We start a one-byte asynchronous transfer. libftdi's chunking system will
 * make this efficient. If data's already there, completed will be set to 1, and
 * we can immediately print it out and loop. Otherwise, it will start an
 * asynchronous request that we can then wait on using poll elsewhere, or
 * revisit when we want to.
 *
 * read_tc: a state pointer that gets updated with the current read transaction.
 * returns: zero on success, non-zero on error.
 */
int printAvailableFtdiOutput(struct ftdi_context *ftdi,
                             struct ftdi_transfer_control **read_tc) {
    unsigned char *buffer = NULL;
    struct timeval zero = { 0, 0 };
    int written = 0;
    // Make sure libusb has a chance to process events
    libusb_handle_events_timeout(ftdi->usb_ctx, &zero);
    // Loop until there's no data available and we've initiated a read
    while (!*read_tc || (*read_tc)->completed) {
        // There's data available if we've looped and there's a read
        if (*read_tc) {
            // Grab the buffer pointer, since ftdi_transfer_data_done frees
            // the structure
            buffer = (*read_tc)->buf;
            if (ftdi_transfer_data_done(*read_tc) > 0) {
                // Output our byte
                if (fputc(*buffer, stdout) == EOF) {
                    free(buffer);
                    ttyRawMode(0);
                    ERR(2, "Failed write to stdout");
                }
                written++;
            }
            *read_tc = NULL;
            // We don't have to free buffer since we can immediately reuse it.
        }
        // If we didn't just finish a read, then we won't have a buffer.
        // This will only happen once per ftdi_transfer_control* variable.
        if (!buffer) {
            buffer = malloc(1);
        }
        // Initialize the read
        if (!(*read_tc = ftdi_read_data_submit(ftdi, buffer, 1))) {
            free(buffer);
            ttyRawMode(0);
            ERR(2, "Failed to communicate with Toad");
        }
    }
    if (written) {
        fflush(stdout);
    }
    return 0;
}
#else  // NEW_LIBFTDI
/* We can't check how much data is available on the old libftdi, so no-op.
 */
int printAvailableFtdiOutput(struct ftdi_context *ftdi,
                             struct ftdi_transfer_control **read_tc) {
    if (ftdi || read_tc) {}
    return 0;
}
#endif  // NEW_LIBFTDI


/* Writes the buffer to the FTDI, receiving FTDI output at each step.
 *
 * buffer: data to write to the FTDI.
 * length: length of the data pointed to by buffer.
 * read_tc: a state pointer that gets updated with the current read transaction.
 * returns: zero on success, non-zero on error.
 */
int ftdiWrite(struct ftdi_context *ftdi, unsigned char *buffer, size_t length,
              struct ftdi_transfer_control **read_tc) {
    while (length) {
        int written = ftdi_write_data(ftdi, buffer, length);
        if (written < 0) {
            ttyRawMode(0);
            ERR(2, "Failed writing to Toad\n");
        }
        buffer += written;
        length -= written;
        if (printAvailableFtdiOutput(ftdi, read_tc)) {
            return 2;
        }
    }
    return 0;
}


/* Sets the system to boot mode, dumps code, and resets the mode.
 * Will also print any messages that appear over UART out to stdout.
 *
 * option: if NULL, reads from stdin. Otherwise, a path to the file to write.
 * force: not applicable.
 * returns: zero on success, non-zero on error.
 */
int cmdBoot(struct ftdi_context *ftdi, const char *option, int force UNUSED) {
    struct ftdi_transfer_control *read_tc = NULL;
    unsigned char mode;
    FILE *file;
    int ret;
    unsigned char buffer[1024];
    size_t received;

    // Save the VBUS state
    FTORDIE(ftdi_read_pins(ftdi, &mode));
    // Open the file
    file = option ? fopen(option, "rb") : stdin;
    if (!file) {
        ERR(2, "Unable to open file for reading.");
    }
    // Set boot mode
    ret = setCbus(ftdi, 1, 1, 0);
    // Wait a second for EC to be ready
    if (!ret) sleep(1);
    // Dump the file
    while (!ret) {
        received = fread(buffer, 1, sizeof(buffer), file);
        if (!received) break;
        ret = ftdiWrite(ftdi, buffer, received, &read_tc);
    }
    // Return to non-boot mode
    if (!ret) ret = setCbus(ftdi, 0, (mode & BIT_VBUS_EN_MASK) != 0, 0);
    // Close the file.
    if (option) fclose(file);
    return ret;
}


/* Processes stdin input for console mode. Assumes there is input available.
 *
 * escaped: state variable for escapes, both read and written.
 *          Set to NULL if escapes are disabled (e.g. not a TTY).
 * returns: zero if the user quit, 1 upon EOF, and anything else on error.
 */
int processConsoleInput(struct ftdi_context *ftdi, int *escaped,
                        struct ftdi_transfer_control **read_tc) {
    // stdin input is available. Grab what's there
    unsigned char buffer[1024];
    size_t available = read(STDIN_FILENO, buffer, sizeof(buffer));
    size_t start = 0, current;
    if (available == 0) {
        // EOF
        return 1;
    } else if (escaped != NULL) {
        // Search for and process escape characters.
        for (current = 0; current < available; ++current) {
            if (*escaped) {
                *escaped = 0;
                start = current + 1;
                switch (buffer[current]) {
                    case TOAD_CONSOLE_HELP1:
                    case TOAD_CONSOLE_HELP2:
                    case TOAD_CONSOLE_HELP3:
                        // Print out console help.
                        ttyRawMode(0);
                        fputs(ESCAPES, stderr);
                        ttyRawMode(1);
                        break;
                    case TOAD_CONSOLE_ESCAPE:
                        // Send the escape character.
                        start = current;
                        break;
                    case TOAD_CONSOLE_BREAK:
                        // Exit out, return failure.
                        return 2;
                    case TOAD_CONSOLE_EOF:
                        // Exit out, return success.
                        return 1;
                    case TOAD_CONSOLE_SUSPEND:
                        // Suspend by calling SIGTSTP on ourselves.
                        ttyRawMode(0);
                        kill(0, SIGTSTP);
                        ttyRawMode(1);
                        break;
                    case TOAD_CONSOLE_EC_SWITCH1:
                    case TOAD_CONSOLE_EC_SWITCH2:
                    case TOAD_CONSOLE_EC_SWITCH3:
                        // Switch to EC console
                        ttyRawMode(0);
                        if (cmdSetMode(ftdi, "ec", 0) == 0) {
                            puts("*** Switched to EC console ***");
                        } else {
                            puts("*** FAILED to switch to EC console ***");
                        }
                        ttyRawMode(1);
                        break;
                    case TOAD_CONSOLE_AP_SWITCH1:
                    case TOAD_CONSOLE_AP_SWITCH2:
                    case TOAD_CONSOLE_AP_SWITCH3:
                    case TOAD_CONSOLE_AP_SWITCH4:
                    case TOAD_CONSOLE_AP_SWITCH5:
                    case TOAD_CONSOLE_AP_SWITCH6:
                        // Switch to AP console
                        ttyRawMode(0);
                        if (cmdSetMode(ftdi, "ap", 0) == 0) {
                            puts("*** Switched to AP console ***");
                        } else {
                            puts("*** FAILED to switch to AP console ***");
                        }
                        ttyRawMode(1);
                        break;
                    default:
                        // Consume it
                        break;
                }
            } else if (buffer[current] == TOAD_CONSOLE_ESCAPE) {
                *escaped = 1;
                // Print out what we have so far
                if (start < current) {
                    int ret = ftdiWrite(ftdi, &buffer[start], current - start,
                                        read_tc);
                    if (ret) return ret;
                }
                // Don't spit out this and the next character
                start = current + 2;
            }
        }
    } else {
        // Request to out everything
        current = available;
    }
    // Print out what we have left
    if (start < current) {
        int ret = ftdiWrite(ftdi, &buffer[start], current - start, read_tc);
        if (ret) return ret;
    }
    return 0;
}


#if ENABLE_CONSOLE
/* Monitors the current UART console.
 * If stdin is a TTY, changes it to raw mode and provides an interactive
 * console with escapes.
 *
 * option: no options allowed.
 * force: not applicable.
 * returns: zero on success, non-zero on error.
 */
int cmdConsole(struct ftdi_context *ftdi, const char *option,
               int force UNUSED) {
    int escaped = 0;
    int *pescaped = NULL;

    // Monitor for STDIN input and USB events
    int ret = 0;
    const char *poll_err = NULL;
    struct pollfd *fds = NULL;
    int num_fds = 0;
    struct ftdi_transfer_control *read_tc = NULL;
    struct timeval tv;

    NO_OPTIONS(option);

    // Switch to raw mode, and set pescaped if we should handle escapes
    if (!ttyRawMode(1)) {
        pescaped = &escaped;
    }

    // Main IO loop
    while (1) {
        const struct libusb_pollfd** libusb_fds;
        int cur_fds, i;

        // Print any available FTDI output, and start input monitoring.
        // NOTE: calls libusb_handle_events_timout for async stuff.
        if ((ret = printAvailableFtdiOutput(ftdi, &read_tc)))
            break;

        // Prepare the poll; lock libusb events
        libusb_lock_events(ftdi->usb_ctx);

        // Make sure a transfer completion didn't sneak in on us
        if (read_tc && read_tc->completed) {
            // Whoops! Loop around so that the events are handled.
            libusb_unlock_events(ftdi->usb_ctx);
            continue;
        }

        // Make a list of all the fds we should poll on
        if (!(libusb_fds = libusb_get_pollfds(ftdi->usb_ctx))) {
            poll_err = "Unable to query libusb file descriptors.";
            break;
        }
        // Count the libusb fds
        for (cur_fds = 0; libusb_fds[cur_fds]; ++cur_fds) {
        }
        // Add one for stdin
        cur_fds += 1;

        // Make sure our structure is big enough for all the fds
        if (cur_fds > num_fds) {
            num_fds = cur_fds;
            if (!(fds = realloc(fds, sizeof(struct pollfd) * num_fds))) {
                poll_err = "Realloc failed when polling file descriptors.";
                break;
            }
        }

        // Fill the structure with fds, starting with stdin
        fds[0].fd = STDIN_FILENO;
        fds[0].events = POLLIN;
        // Poll all of the libusb fds
        for (i = 1; i < cur_fds; ++i) {
            fds[i].fd = libusb_fds[i-1]->fd;
            fds[i].events = libusb_fds[i-1]->events;
        }

        // We're done with the list
        free(libusb_fds);

        // libusb might want a timeout, so query it
        if (!libusb_get_next_timeout(ftdi->usb_ctx, &tv)) {
            // No timeouts. Specifying a negative timeout waits forever.
            tv.tv_sec = -1;
        }

        // Poll
        ret = poll(fds, cur_fds, tv.tv_usec / 1000 + tv.tv_sec * 1000);
        if (ret < 0 && errno != EINTR) {
            poll_err = "Call to poll() failed.";
            break;
        }

        // Allow for other threads to do event handling
        libusb_unlock_events(ftdi->usb_ctx);

        // Handle user input if there is some available
        if (fds[0].revents) {
            if ((ret = processConsoleInput(ftdi, pescaped, &read_tc))) {
                // ret == 1 means EOF, which is not an error.
                if (ret == 1)
                    ret = 0;
                break;
            }
        }
    }

    // Clean up
    ttyRawMode(0);
    free(fds);

    // Print poll-related error messages AFTER ttyRawMode has been deactivated.
    if (poll_err) {
        ret = 2;
        prn_error("%s", poll_err);
    }

    return ret;
}
#endif  // if ENABLE_CONSOLE


#if ENABLE_CONSOLE
/* Sets EC mode and monitors the UART console.
 *
 * option: no options allowed.
 * force: passed to cmdSetMode and cmdConsole.
 * returns: zero on success, non-zero on error.
 */
int cmdEc(struct ftdi_context *ftdi, const char *option, int force) {
    int ret = cmdSetMode(ftdi, "ec", force);
    return ret ? ret : cmdConsole(ftdi, option, force);
}
#endif  // if ENABLE_CONSOLE


#if ENABLE_CONSOLE
/* Sets AP mode and monitors the UART console
 *
 * option: no options allowed.
 * force: passed to cmdSetMode and cmdConsole.
 * returns: zero on success, non-zero on error.
 */
int cmdAp(struct ftdi_context *ftdi, const char *option, int force) {
    int ret = cmdSetMode(ftdi, "ap", force);
    return ret ? ret : cmdConsole(ftdi, option, force);
}
#endif  // if ENABLE_CONSOLE
