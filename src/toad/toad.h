// Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef __TOAD_H__
#define __TOAD_H__

#include "ftdi_common.h"

#ifdef __cplusplus
extern "C" {
#endif


/* libftdi version handling:
 * We need the 1.x version of libftdi for its asynchronous read interface.
 * If we don't have it, disable the features that depend on it.
 * There is no official method to detect the old version, but the 1.x version
 * makes the EEPROM structure opaque; thus, we can detect 0.x by checking for
 * the FTDI_DEFAULT_EEPROM_SIZE define.
 */
#ifndef FTDI_DEFAULT_EEPROM_SIZE
#   define NEW_LIBFTDI 1
#   ifndef ENABLE_CONSOLE
#       define ENABLE_CONSOLE 1
#   endif
#else
#   define NEW_LIBFTDI 0
#   undef ENABLE_CONSOLE
#   define ENABLE_CONSOLE 0

    // Some defines are missing in the old libftdi
#   define CBUSH_IOMODE 0x08
#   define CBUSH_TRISTATE 0x00

    // We don't use this if console mode is disabled, but predeclare it for
    // code simplicity.
    struct ftdi_transfer_control;

    // This version doesn't use libusb, but we don't use many libusb functions,
    // so we can define equivalents easily.
#   define libusb_device_descriptor usb_device_descriptor
#   define libusb_get_device_descriptor(usb_dev, desc) \
            usb_get_descriptor(usb_dev, USB_DT_DEVICE, 0, desc, sizeof(*desc))
#   define libusb_get_string_descriptor_ascii(usb_dev, index, buf, buflen) \
            usb_get_string_simple(usb_dev, index, (char*)buf, buflen)
#   define libusb_get_device(usb_dev) usb_dev
#endif


/* Types */
typedef int (*cmd_func)(struct ftdi_context *, const char *, int);
struct cmd {
    const char *name;
    cmd_func func;
};


/* Constants */
#define FTDI_DESC "FT230X Basic UART"
#define TOAD_DESC "Toad UART Adapter"
#define TOAD_MANUFACTURER "Google Inc"
#define TOAD_MANUFACTURER_ID "GG"  // Must be two characters
#define TOAD_VID 0x0403
#define TOAD_PID 0x6015
#define TOAD_BAUD 115200
#define TOAD_FLOW_CONTROL SIO_DISABLE_FLOW_CTRL
#define TOAD_LINE_PROPERTY BITS_8, STOP_BIT_1, NONE
#define TOAD_LATENCY_TIMER 17  // Cannot be 16; see ftdiConfigure in toad.c

/* Programming data for the FT230X */
#define TOAD_EEPROM_SIZE 0x100
#define TOAD_EEPROM_CHECKSUM_OFFSET (TOAD_EEPROM_SIZE - 2)
/* Each string descriptor is 2 bytes (size, type) plus the text in UTF16, sans
 * null terminator. This means the string descriptor size is equal to
 * sizeof(stringbuffer) * 2, since sizeof includes the null character, which we
 * count as the two header bytes.
 */
#define TOAD_EEPROM_STRING_DESCRIPTOR 0x03
#define TOAD_EEPROM_STRING_START 0xA0
#define TOAD_EEPROM_MANUFACTURER_START (TOAD_EEPROM_STRING_START)
#define TOAD_EEPROM_DESC_START \
    (TOAD_EEPROM_MANUFACTURER_START + sizeof(TOAD_MANUFACTURER) * 2)
#define TOAD_EEPROM_SERIAL_START \
    (TOAD_EEPROM_DESC_START + sizeof(TOAD_DESC) * 2)
// Offset of the length of the serial in the header
#define TOAD_EEPROM_00_SERIAL_SIZE_OFFSET 0x13
// Initial value for the FT230X checksum. Used to be 0xAAAA on older devices.
#define TOAD_EEPROM_CHECKSUM_SEED 0x7557

/* Console escapes */
#define TOAD_CONSOLE_HELP1      'h'
#define TOAD_CONSOLE_HELP2      'H'
#define TOAD_CONSOLE_HELP3       8  // ^H
#define TOAD_CONSOLE_ESCAPE     24  // ^X
#define TOAD_CONSOLE_BREAK       3  // ^C
#define TOAD_CONSOLE_EOF         4  // ^D
#define TOAD_CONSOLE_SUSPEND    26  // ^Z
#define TOAD_CONSOLE_EC_SWITCH1 'e'
#define TOAD_CONSOLE_EC_SWITCH2 'E'
#define TOAD_CONSOLE_EC_SWITCH3  5  // ^E
#define TOAD_CONSOLE_AP_SWITCH1 'a'
#define TOAD_CONSOLE_AP_SWITCH2 'A'
#define TOAD_CONSOLE_AP_SWITCH3  1  // ^A -- might be used by screen/tmux
#define TOAD_CONSOLE_AP_SWITCH4 'p'
#define TOAD_CONSOLE_AP_SWITCH5 'P'
#define TOAD_CONSOLE_AP_SWITCH6 16  // ^P

/* For parsing the ftdi_read_pins response */
#define BIT_MODE_SW_L_MASK 0x01
#define BIT_AP_MODE_EC_MODE_L_MASK 0x02
#define BIT_BOOT_MODE_L_MASK 0x04
#define BIT_VBUS_EN_MASK 0x08

/* For setting mask for ftdi_set_bitmode */
#define BIT_MODE_SW_L_ASSERT 0x10
#define BIT_MODE_SW_L_DEASSERT 0x00
#define BIT_AP_MODE_EC_MODE_L_INPUT 0x00
#define BIT_BOOT_MODE_L_ASSERT 0x40
#define BIT_BOOT_MODE_L_DEASSERT 0x00
#define BIT_VBUS_EN_ASSERT 0x00
#define BIT_VBUS_EN_DEASSERT 0x80

/* Special parameters */
#define SET_CBUS_KEEP 2
#define SET_EC_AP_TOGGLE 2

/* Parameter declaration modifiers */
#define UNUSED __attribute__((unused))
#if NEW_LIBFTDI
#    define UNUSED_ON_OLD_LIBFTDI
#else
#    define UNUSED_ON_OLD_LIBFTDI UNUSED
#endif


/* Function declarations */
#define ERR(n, s) \
    do { \
        prn_error(s); \
        return (n); \
    } while (0)
#define FTORDIE(x) \
    do { \
        int __ret; \
        if ((__ret = (x)) < 0) \
            ERR(__ret, #x " failed"); \
    } while (0)
#define NO_OPTIONS(x) \
    do { \
        if (x && *x) \
            ERR(1, "Unrecognized option."); \
    } while (0)
#define NEEDS_OPTION(x) \
    do { \
        if (!x || !*x) \
            ERR(1, "Option required."); \
    } while (0)
int ttyRawMode(int enable);
int runCmd(cmd_func cmd, const char *device, const char *option, int force);
int ftdiConfigure(struct ftdi_context *ftdi);
int ftdiWrite(struct ftdi_context *ftdi, unsigned char *buffer, size_t length,
              struct ftdi_transfer_control **read_tc);
int setCbus(struct ftdi_context *ftdi, int boot_mode, int vbus_en, int mode_sw);
int setEcAp(struct ftdi_context *ftdi, int ec);
int parseOnOffToggle(struct ftdi_context *ftdi, const char *option,
                     unsigned char mask, int *enable);
int printAvailableFtdiOutput(struct ftdi_context *ftdi,
                             struct ftdi_transfer_control **read_tc);
int processConsoleInput(struct ftdi_context *ftdi, int *escaped,
                        struct ftdi_transfer_control **read_tc);
int cmdList(struct ftdi_context *ftdi, const char *option, int force);
int cmdInitialize(struct ftdi_context *ftdi, const char *option, int force);
int cmdStatus(struct ftdi_context *ftdi, const char *option, int force);
int cmdSetVbus(struct ftdi_context *ftdi, const char *option, int force);
int cmdSetEcAp(struct ftdi_context *ftdi, const char *option, int force);
int cmdSetBoot(struct ftdi_context *ftdi, const char *option, int force);
int cmdMode(struct ftdi_context *ftdi, const char *option, int force);
int cmdGetMode(struct ftdi_context *ftdi, const char *option, int force);
int cmdSetMode(struct ftdi_context *ftdi, const char *option, int force);
int cmdBoot(struct ftdi_context *ftdi, const char *option, int force);
int cmdConsole(struct ftdi_context *ftdi, const char *option, int force);
int cmdEc(struct ftdi_context *ftdi, const char *option, int force);
int cmdAp(struct ftdi_context *ftdi, const char *option, int force);


#ifdef __cplusplus
}
#endif
#endif  // __TOAD_H__
