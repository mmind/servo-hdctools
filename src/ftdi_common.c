// Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include <stdio.h>
#include <string.h>
#include "ftdi_common.h"

// return number of interfaces, -1 for error
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
  }
  return -1;
}

int fcom_cfg(struct ftdi_context *fc, int interface, 
                   enum ftdi_mpsse_mode mode, int direction) {

  if (fcom_num_interfaces(fc) > 1) {
    prn_dbg("setting interface to %d\n", interface);
    if (ftdi_set_interface(fc, interface)) {
      ERROR_FTDI("setting interface", fc);
      return FCOM_ERR_SET_INTERFACE;
    }
  }
  CHECK_FTDI(ftdi_set_latency_timer(fc, FCOM_USB_LATENCY_TIMER),
             "Set latency timer", fc);
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
  puts("       -d <num>            : device id if >1 ftdi with same vid:pid");
  USG_DEFAULT("%d\n", fargs->dev_id);
  puts("       -i <interface>      : interface id for FTDI port");
  USG_DEFAULT("%d\n", fargs->interface);
  puts("       -s <num>             : speed ( buadrate ) in hertz");
  USG_DEFAULT("%d\n", fargs->speed);
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
  while ((c = getopt(argc, argv, "v:p:i:s:g:h")) != -1) {
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
      case 's':
        fargs->speed = strtoul(optarg, NULL, 0);
        args_consumed += 2;
        break;
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
  prn_fatal("not implemented\n");
}

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

