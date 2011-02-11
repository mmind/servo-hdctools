// Copyright (c) 2010 The Chromium OS Authors. All rights reserved.
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
  prn_error("%s: %s\n", msg, ftdi_get_error_string(context))

#define CHECK_FTDI(fx, msg, context) \
  do {                               \
    if (fx < 0) {                    \
      ERROR_FTDI(msg, context);      \
    }                                \
  } while (0)
    
struct gpio_s {
  uint8_t value;
  uint8_t direction;
  uint8_t mask;
};

struct ftdi_common_args {
  unsigned int vendor_id;
  unsigned int product_id;
  unsigned int dev_id;
  enum ftdi_interface interface;
  char *serialname;
  unsigned int speed;
  enum ftdi_bits_type bits;
  enum ftdi_parity_type parity;
  enum ftdi_stopbits_type sbits;
  uint8_t value;
  uint8_t direction;
};

enum ftdi_interface_type {
  GPIO,
  I2C,
  JTAG,
  SPI,
  UART
};

#ifdef WITH_TIME
// TODO(tbroch) switch to clock_gettime

/*
struct timezone {
  int tz_minuteswest;     // minutes west of Greenwich 
  int tz_dsttime;         // type of DST correction 
};
*/

struct timeval tv;
struct timezone tz;
struct tm *tm;

#define _prn_time()                                                 \
  gettimeofday(&tv, &tz);                                           \
  tm=localtime(&tv.tv_sec);                                         \
  fprintf(stderr, "(%02d:%02d:%02d.%u)", tm->tm_hour, tm->tm_min,   \
          tm->tm_sec, (unsigned int)tv.tv_usec)
#else
#define _prn_time()
#endif

#define _prn_common(type, ...)                               \
  fprintf(stderr, "%s %s:%u :: ", type, __FILE__, __LINE__); \
  fprintf(stderr, __VA_ARGS__)

#define prn_fatal(...)             \
  _prn_common("-F-", __VA_ARGS__); \
  exit(-1);
#define prn_error(...)                          \
  _prn_common("-E-", __VA_ARGS__)
#define prn_warn(...)                           \
  _prn_common("-W-", __VA_ARGS__)
#define prn_info(...)                          \
  _prn_time();                                 \
  _prn_common("-I-", __VA_ARGS__)

#define prn_perror(...)                                 \
  prn_error("%s (%d): ", strerror(errno), errno);       \
  fprintf(stderr, __VA_ARGS__)

#ifdef DEBUG
#define prn_dbg(...)                            \
  _prn_time();                                  \
  _prn_common("-D-", __VA_ARGS__)
#else
#define prn_dbg(...)
#endif

#define _prn_ftdi_common(type, rv, context, ...)                         \
  fprintf(stderr, "%s:", type);                                          \
  fprintf(stderr, __VA_ARGS__);                                          \
  fprintf(stderr, " : %d (%s)\n", rv, ftdi_get_error_string(context))

#define prn_ftdi_error(rv, context, ...)               \
  _prn_ftdi_common("ERROR", rv, context, __VA_ARGS__)
#define prn_ftdi_warn(rv, context, ...)                \
  _prn_ftdi_common("WARN", rv, context, __VA_ARGS__)

int fcom_cfg(struct ftdi_context *, int, enum ftdi_mpsse_mode, int);
int fcom_args(struct ftdi_common_args *, int, char **);
int fcom_lookup_serial(struct ftdi_context *, char *);
int fcom_num_interfaces(struct ftdi_context *);
int fcom_is_mpsse(struct ftdi_context *, struct ftdi_common_args *);

#ifdef __cplusplus
}
#endif
#endif // __FTDI_UTILS_H__
