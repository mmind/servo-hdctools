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
#include "ftdiuart.h"

static void usage(char *progname) {
  printf("\n\n%s [switch args]\n", progname);
  exit(-1);
}

int main(int argc, char **argv) {
  int rv = 0;

  struct ftdi_context fc;
  struct fuart_context fuartc;

  int args_consumed = 0;
  struct ftdi_common_args fargs = {
    // default for servo
    .interface = INTERFACE_C,
    .vendor_id = 0x0403,
    .product_id = 0x6011,
    .serialname = NULL,
    // most used defaults
    .uart_cfg = {
      .baudrate = 115200,
      .bits = BITS_8,
      .parity = NONE,
      .sbits = STOP_BIT_1
    }
  };

  if ((args_consumed = fcom_args(&fargs, argc, argv)) < 0) {
    usage(argv[0]);
  }
  if (ftdi_init(&fc) < 0) {
    ERROR_FTDI("Initializing ftdi context", &fc);
    return 1;
  }
  if (fuart_init(&fuartc, &fc)) {
    prn_fatal("fuart_init\n");
  }
  if (fuart_open(&fuartc, &fargs)) {
    prn_fatal("fuart_open\n");
  }
  prn_info("ftdi uart connected to %s\n", fuartc.name);
  if ((rv = fuart_run(&fuartc, FUART_USECS_SLEEP))) {
    prn_fatal("fuart_run");
  }
  while (1) {
    // ours sleeps to eleven!
    sleep(11);
  }
  // never reached
  fuart_close(&fuartc);
  return rv;
}
