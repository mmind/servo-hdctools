// Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <inttypes.h>
#include <assert.h>

#include <ftdi.h>
#include "ftdi_common.h"
#include "ftdigpio.h"

void usage(char *progname) {
  printf("\n\n%s [switch args]\n", progname);
  printf("\nOnce started input value and direction when prompted.\n");
  printf("<cr> to exit\n");
  exit(-1);
}

int main(int argc, char **argv) {
  int rv = 0;

  struct ftdi_context fc;
  struct fgpio_context fgc;

  int args_consumed = 0;
  struct ftdi_common_args fargs = {
    .interface = INTERFACE_D,
    .vendor_id = 0x0403,
    .product_id = 0x6011,
    .serialname = NULL,
    // default is inputs
    .direction = 0,
    .value = 0,
  };

  if ((args_consumed = fcom_args(&fargs, argc, argv)) < 0) {
    usage(argv[0]);
  }
  if (ftdi_init(&fc) < 0) {
    ERROR_FTDI("Initializing ftdi context", &fc);
    return 1;
  }
  if (fgpio_init(&fgc, &fc)) {
    prn_fatal("fgpio_init\n");
  }
  if (fgpio_open(&fgc, &fargs)) {
    prn_fatal("fgpio_open\n");
  }

  struct gpio_s gpio;
  uint8_t rd_val;
  // just default to allowable maximum
  gpio.mask = fgc.gpio.mask;
  
  if (fargs.direction) {
    gpio.direction = fargs.direction;
    gpio.value = fargs.value;
    if ((rv = fgpio_wr_rd(&fgc, &gpio, &rd_val, GPIO))) {
      prn_error("fgpio_wr_rd (%d)\n", rv);
    } else {
      prn_info("Initialized gpio dir = 0x%02x, val = 0x%02x\n",
               gpio.direction, gpio.value);
    }
  }
  while (1) {
    char in_str[128];
    printf("DIR:");
    if ((fgets(in_str, sizeof(in_str) - 1, stdin) == NULL) ||
        (in_str[0] == '\n')) {
      break;
    }
    gpio.direction = strtoul(in_str, NULL, 0);

    printf("VAL:");

    if ((fgets(in_str, sizeof(in_str) - 1, stdin) == NULL) ||
        (in_str[0] == '\n')) {
      break;
    }
    gpio.value = strtoul(in_str, NULL, 0);

    if ((rv = fgpio_wr_rd(&fgc, &gpio, &rd_val, GPIO))) {
      prn_error("fgpio_wr_rd (%d)\n", rv);
      break;
    }
    printf("RD:0x%02x\n", rd_val);
  }
  fgpio_close(&fgc);
  return rv;
}
