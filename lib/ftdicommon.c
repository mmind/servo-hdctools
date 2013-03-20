// Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include <assert.h>
#include <errno.h>
#include <getopt.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <stdlib.h>

#include "ftdi_common.h"

// return number of interfaces, -1 for error
#pragma GCC diagnostic ignored "-Wswitch-enum"
int fcom_num_interfaces(struct ftdi_context *fc) {
  if (fc->usb_dev == NULL) {
    // no ftdi_usb_open so haven't contacted device yet ... fail
    return -1;
  }
  switch (fc->type) {
    case(TYPE_AM):
    case(TYPE_R):
    case(TYPE_BM):
      return 1;
      break;
    case(TYPE_2232C):
    case(TYPE_2232H):
      return 2;
      break;
    case(TYPE_4232H):
      return 4;
      break;
  default:
      assert(((void)"internal error", 0));
      break;
  }
  return -1;
}
#pragma GCC diagnostic pop


int fcom_cfg(struct ftdi_context *fc, int interface,
                   enum ftdi_mpsse_mode mode, int direction) {
  unsigned char latency;

  if (fcom_num_interfaces(fc) > 1) {
    prn_dbg("setting interface to %d\n", interface);
    if (ftdi_set_interface(fc, interface)) {
      ERROR_FTDI("setting interface", fc);
      return FCOM_ERR_SET_INTERFACE;
    }
  }
  CHECK_FTDI(ftdi_set_latency_timer(fc, FCOM_USB_LATENCY_TIMER),
             "Set latency timer", fc);
  CHECK_FTDI(ftdi_get_latency_timer(fc, &latency),
             "Get latency timer", fc);
  if (latency != FCOM_USB_LATENCY_TIMER)
    prn_error("Latency timer = %d but tried to set to %d",
              latency, FCOM_USB_LATENCY_TIMER);

  CHECK_FTDI(ftdi_set_bitmode(fc, 0, BITMODE_RESET),
  "Resetting", fc);
  CHECK_FTDI(ftdi_set_bitmode(fc, direction, mode),
             "setting mode", fc);
  CHECK_FTDI(ftdi_usb_purge_buffers(fc), "Purge buffers", fc);
  return FCOM_ERR_NONE;
}

#define USG_DEFAULT(...)                                \
  printf("                             DEFAULT=");      \
  printf(__VA_ARGS__)

static void usage(struct ftdi_common_args *fargs) {
  puts("Common ftdi args ::");
  puts("       -v <num>            : vendor id of device to connect to");
  USG_DEFAULT("0x%02x\n", fargs->vendor_id);
  puts("       -p <num>            : product id of device to connect to");
  USG_DEFAULT("0x%02x\n", fargs->product_id);
  puts("       -d <num>            : "
       "device serialname (use if >1 FTDI device with same vid:pid )");
  USG_DEFAULT("%d\n", fargs->dev_id);
  puts("       -i <interface>      : interface id for FTDI port");
  USG_DEFAULT("%d\n", fargs->interface);
  puts("       -g <dir>:<val>      : initial gpio configuration");
  puts("       -h                  : this message");
  puts("\nWhere:");
  puts("       <interface> : a|b|c|d|1|2|3|4.  Note '0' means 'Any' which is device dependent");
  puts("       <hz>        : number in hertz");
  puts("       <dir>       : mask for gpio direction.  1=output, 0=input");
  puts("       <val>       : mask for gpio value.  1=high, 0=low");
  puts("\n");

}

int fcom_args(struct ftdi_common_args *fargs, int argc, char **argv) {
  int c;
  char *ptr;
  int args_consumed = 0;

  // TODO(tbroch) add uart bits,sbits,parity arg parsing
  while ((c = getopt(argc, argv, "v:p:i:d:s:g:h")) != -1) {
    switch (c) {
      case 'v':
        fargs->vendor_id = strtoul(optarg, NULL, 0);
        args_consumed += 2;
        break;
      case 'p':
        fargs->product_id = strtoul(optarg, NULL, 0);
        args_consumed += 2;
        break;
      case 'i':
        switch(optarg[0]) {
          case '0':
            fargs->interface = INTERFACE_ANY;
            break;
          case '1':
          case 'a':
          case 'A':
              fargs->interface = INTERFACE_A;
              break;
          case '2':
          case 'b':
          case 'B':
              fargs->interface = INTERFACE_B;
              break;
          case '3':
          case 'c':
          case 'C':
              fargs->interface = INTERFACE_C;
              break;
          case '4':
          case 'd':
          case 'D':
              fargs->interface = INTERFACE_D;
              break;
          default:
            prn_fatal("Unknown interface value %c.  Should be [a|b|c|d]\n", c);
            break;
        }
        args_consumed += 2;
        break;
      case 'd':
        fargs->serialname = malloc(strlen(optarg)+1);
        strcpy(fargs->serialname, optarg);
      case 'g':
        fargs->direction = strtoul(optarg, &ptr, 0);
        if (ptr[0] != ':') {
          prn_fatal("Poorly formatted direction in -g <dir>:<val> string\n");
          break;
        }
        ptr++;
        fargs->value = strtoul(ptr, &ptr, 0);
        if (ptr[0] != '\0') {
          prn_fatal("Poorly formatted value in -g <dir>:<val> string\n");
          break;
        }

        args_consumed += 2;
        break;
      case 'h':
        usage(fargs);
        return -1;
      default:
        // remaining args parsed by caller
        break;
    }
  }
  return args_consumed;
}

int fcom_lookup_serial(struct ftdi_context *fc, char *name) {
  // TODO(tbroch) implement lookup of serial from eeprom
  long fc_dump  = (long)fc;               /* Silence compiler warning. */
  long name_dump = (long)name;            /* Silence compiler warning. */
  if (fc_dump > name_dump)                /* Silence compiler warning. */
    prn_fatal("not implemented\n");
  else
    prn_fatal("not implemented\n");
}

#pragma GCC diagnostic ignored "-Wswitch-enum"
int fcom_is_mpsse(struct ftdi_context *fc,
                        struct ftdi_common_args *fargs) {
  switch(fc->type) {
    case(TYPE_2232C):
      return (fargs->interface <= 1);
      break;
    case(TYPE_2232H):
    case(TYPE_4232H):
      return (fargs->interface <= 2);
      break;
    case(TYPE_AM):
    case(TYPE_R):
    case(TYPE_BM):
    default:
      return 0;
      break;
  }
}
#pragma GCC diagnostic pop

struct ftdi_itype *fcom_lookup_interface(struct ftdi_itype *interfaces,
                                         unsigned int cnt,
                                         unsigned int interface_num,
                                         enum ftdi_interface_type itype) {
  if (interface_num > cnt) {
    return NULL;
  }
  if ((itype != ANY) && (interfaces[interface_num-1].type != itype)) {
    return NULL;
  }
  return &interfaces[interface_num-1];
}

static unsigned debug_enabled(void) __attribute__((pure));
static unsigned debug_enabled(void)
{
    return getenv("SERVOD_DEBUG") != NULL;
}

static void _prn_time(void)
{
  struct timeval tv;
  struct timezone tz;
  struct tm *tm;

  gettimeofday(&tv, &tz);
  tm=localtime(&tv.tv_sec);
  fprintf(stderr, "(%02d:%02d:%02d.%u)", tm->tm_hour, tm->tm_min,
          tm->tm_sec, (unsigned int)tv.tv_usec);
}

static void _prn_common(const char *type,
                        const char *fmt,
                        va_list ap) __attribute__((format(printf, 2, 0)));
static void _prn_common(const char *type,
                        const char *fmt,
                        va_list ap)
{
  fprintf(stderr, "%s :: ", type);
  vfprintf(stderr, fmt, ap);
  fprintf(stderr, "\n");
}

void prn_fatal(const char *fmt, ...)
{
  va_list ap;

  va_start(ap, fmt);
  _prn_common("-F-", fmt, ap);
  va_end(ap);
  exit(-1);
}

void prn_error(const char *fmt, ...)
{
  va_list ap;

  va_start(ap, fmt);
  _prn_common("-E-", fmt, ap);
  va_end(ap);
}

void prn_warn(const char *fmt, ...)
{
  va_list ap;

  va_start(ap, fmt);
  _prn_common("-W-", fmt, ap);
  va_end(ap);
}

void prn_info(const char *fmt, ...)
{
  va_list ap;

  va_start(ap, fmt);
  _prn_time();
  _prn_common("-I-", fmt, ap);
  va_end(ap);
}

void prn_perror(const char *fmt, ...)
{
  va_list ap;

  va_start(ap, fmt);
  prn_error("%s (%d): ", strerror(errno), errno);
  vfprintf(stderr, fmt, ap);
  va_end(ap);
}

void prn_dbg(const char *fmt, ...)
{
  if (debug_enabled()) {
    va_list ap;

    va_start(ap, fmt);
    _prn_time();
    _prn_common("-D-", fmt, ap);
    va_end(ap);
  }
}


static void _prn_ftdi_common(const char *type,
                             int rv,
                             struct ftdi_context *context,
                             const char *fmt,
                             va_list ap) __attribute__((format(printf, 4, 0)));
static void _prn_ftdi_common(const char *type,
                             int rv,
                             struct ftdi_context *context,
                             const char *fmt,
                             va_list ap)
{
  fprintf(stderr, "%s:", type);
  vfprintf(stderr, fmt, ap);
  fprintf(stderr, " : %d (%s)\n", rv, ftdi_get_error_string(context));
  va_end(ap);
}

void prn_ftdi_error(int rv, struct ftdi_context *context, const char *fmt, ...)
{
  va_list ap;

  va_start(ap, fmt);
  _prn_ftdi_common("ERROR", rv, context, fmt, ap);
  va_end(ap);
}

void prn_ftdi_warn(int rv, struct ftdi_context *context, const char *fmt, ...)
{
  va_list ap;

  va_start(ap, fmt);
  _prn_ftdi_common("WARN", rv, context, fmt, ap);
  va_end(ap);
}
