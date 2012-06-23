// Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef __FTDI_UTILS_H__
#define __FTDI_UTILS_H__

#include <ftdi.h>
#include <sys/time.h>
#include <stdint.h>
#include <time.h>

#ifdef __cplusplus
extern "C" {
#endif

#define FCOM_USB_LATENCY_TIMER 16   // in msecs

#define FCOM_OK 0

#define FCOM_ERR_NONE 0
#define FCOM_ERR 1
#define FCOM_ERR_SET_INTERFACE 1

#define FTDI_ERR_USB_UNAVAIL -666

#define FTDI_CLK_MAX_X5 30000000    // max clock (hz) for FTDI high speed dev
#define FTDI_CLK_MAX_X1  6000000    // max clock (hz) for FTDI dev
#define FTDI_CLK_MIN         100    // min clock (hz) for FTDI dev

// global clock setup commands
#define FTDI_CMD_X5_OFF      0x8a   // disable clock div 5 for 60mhz master clk
#define FTDI_CMD_3PHASE      0x8c   // 3 phase clocking needed for i2c
#define FTDI_CMD_NO_ADAP_CLK 0x97   // turn off adaptive clocking
#define FTDI_CMD_3PH_CLK     0x8d   // enable 3 phase clocking

// MPSSE clocking control commands
// M(F|R)E == MSB Falling|Rising Edge
// L(F|R)E == LSB Falling|Rising Edge
#define FTDI_CMD_MRE_CLK_BYTE_OUT 0x10
#define FTDI_CMD_MFE_CLK_BYTE_OUT 0x11
#define FTDI_CMD_MRE_CLK_BIT_OUT  0x12
#define FTDI_CMD_MFE_CLK_BIT_OUT  0x13
#define FTDI_CMD_MRE_CLK_BYTE_IN  0x20
#define FTDI_CMD_MFE_CLK_BYTE_IN  0x24
#define FTDI_CMD_LRE_CLK_BIT_IN   0x2a
#define FTDI_CMD_LFE_CLK_BIT_IN   0x2e

#define IS_FTDI_OPEN(context) (context->usb_dev != NULL)

#define ERROR_FTDI(msg, context)                                \
  prn_error("%s: %s", msg, ftdi_get_error_string(context))

#define CHECK_FTDI(fx, msg, context)                \
  do {                                              \
    prn_dbg("CHECK_FTDI err:%d for %s\n", fx, msg); \
    if (fx < 0) {                                   \
      ERROR_FTDI(msg, context);                     \
    }                                               \
  } while (0)

struct gpio_s {
  uint8_t value;
  uint8_t direction;
  uint8_t mask;
};

struct uart_cfg {
  unsigned int baudrate;
  unsigned int bits;
  unsigned int parity;
  unsigned int sbits;
};

struct ftdi_common_args {
  unsigned int vendor_id;
  unsigned int product_id;
  unsigned int dev_id;
  enum ftdi_interface interface;
  char *serialname;
  struct uart_cfg uart_cfg;
  uint8_t value;
  uint8_t direction;
};

enum ftdi_interface_type {
  ANY,
  GPIO,
  I2C,
  JTAG,
  SPI,
  UART
};

struct ftdi_itype {
  enum ftdi_interface_type type;
  void *context;
};

int fcom_cfg(struct ftdi_context *, int, enum ftdi_mpsse_mode, int);
int fcom_args(struct ftdi_common_args *, int, char **);
int fcom_lookup_serial(struct ftdi_context *, char *);
int fcom_num_interfaces(struct ftdi_context *);
int fcom_is_mpsse(struct ftdi_context *, struct ftdi_common_args *);
struct ftdi_itype *fcom_lookup_interface(struct ftdi_itype *, unsigned int,
                                         unsigned int,
                                         enum ftdi_interface_type itype);

#define PRINTF_ATTR(_str, _chk) __attribute__((format(printf, _str, _chk)))

void prn_fatal(const char *fmt, ...) PRINTF_ATTR(1, 2) __attribute__((noreturn));
void prn_error(const char *fmt, ...) PRINTF_ATTR(1, 2);
void prn_warn(const char *fmt, ...) PRINTF_ATTR(1, 2);
void prn_info(const char *fmt, ...) PRINTF_ATTR(1, 2);
void prn_perror(const char *fmt, ...) PRINTF_ATTR(1, 2);
void prn_dbg(const char *fmt, ...) PRINTF_ATTR(1, 2);
void prn_ftdi_error(int rv, struct ftdi_context *context,
                    const char *fmt, ...) PRINTF_ATTR(3, 4);
void prn_ftdi_warn(int rv, struct ftdi_context *context,
                   const char *fmt, ...) PRINTF_ATTR(3, 4);
#ifdef __cplusplus
}
#endif
#endif // __FTDI_UTILS_H__
