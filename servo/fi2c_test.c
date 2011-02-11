// Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <inttypes.h>
#include <assert.h>

#include <ftdi.h>
#include "ftdi_common.h"
#include "ftdii2c.h"

#define MAX_BUF_SIZE 128

void usage(char *progname) {
  printf("%s [switch args] <slv> [<reg0> [ <reg1> ] ] rd <cnt>\n", progname);
  puts("\tor");
  printf("%s [switch args] <slv> wr <b0> [<b1> ... <bn>]\n", progname);
  puts("\nWhere:");
  puts("        <slv>      : slave device ( 1 byte )");
  puts("        <regX>     : index register into slave.  Can be 1 || 2 bytes");
  puts("        rd|wr      : read or write");
  puts("        <cnt>      : bytes to read");
  puts("        <b1>..<bn> : bytes to write");
  exit(-1);
}

void prn_output(uint8_t *buf, int cnt) {
  int i;

  for (i = 0; i < cnt; i++) {
    if (i && (i % 16) == 0) { printf("\n"); }
    if (cnt > 4) {
      printf("0x%02x ", buf[i]);
    } else if (i == 0) {
      printf("0x%02x", buf[i]);
    } else {
      printf("%02x", buf[i]);
    }
  }
  printf("\n");
}

int parse_i2c_args(uint8_t *wbuf, int *wcnt, int *rcnt, uint8_t *slv, 
                   int argc, char **argv) {
  int i;
  int cnt = 0;
  unsigned long int slv_ul;

  if (argc < 4) {
    prn_error("More arguments please\n\n");
    usage(argv[0]);
  }
  slv_ul = strtoul(argv[1], NULL, 0);
  // 7-bit i2c has 112 valid slaves from 0x8 -> 0x77 only
  if ((slv_ul < 0x8) || (slv_ul > 0x77)) {
    prn_error("Invalid slave address 0x%lx\n", slv_ul);
    return -1;
  }
  *slv = (uint8_t)slv_ul;

  /* argc[2] == rd|wr :: raw read|write */
  /* argc[3:4] == rd :: registered read */
  if (!strcmp(argv[2], "rd")) {
    *rcnt = strtoul(argv[3], NULL, 0);
  } else if (!strcmp(argv[3], "rd")) {
    wbuf[cnt++] = strtoul(argv[2], NULL, 0);
    *rcnt = strtoul(argv[4], NULL, 0);
  } else if (!strcmp(argv[4], "rd")) {
    wbuf[cnt++] = strtoul(argv[2], NULL, 0);
    wbuf[cnt++] = strtoul(argv[3], NULL, 0);
    *rcnt = strtoul(argv[5], NULL, 0);
  } else if (!strcmp(argv[2], "wr")) {
    if ((argc - 3) > MAX_BUF_SIZE) {
      goto INPUT_ERROR;
    }
    for (i = 3; i < argc; i++) {
      wbuf[cnt++] = strtoul(argv[i], NULL, 0);
    }
  } else {
    goto INPUT_ERROR;
  }
  if ((*rcnt > MAX_BUF_SIZE) || (cnt > MAX_BUF_SIZE)) {
    goto INPUT_ERROR;
  }
  *wcnt = cnt;
  return FCOM_ERR_NONE;
 INPUT_ERROR:
  prn_error("Unrecognized input.  See %s -h\n", argv[0]);
  return FCOM_ERR;
}

int main (int argc, char **argv) {

  uint8_t wbuf[MAX_BUF_SIZE];
  uint8_t rbuf[MAX_BUF_SIZE];
  uint8_t slv;

  int wcnt = 0;
  int rcnt = 0;
  int rv = 0;

  struct ftdi_context fc;
  struct fi2c_context fic;
  struct ftdi_common_args fargs;
  memset(&fargs, 0, sizeof(fargs));
  // defaults for servo 
  fargs.vendor_id = 0x0403;
  fargs.product_id = 0x6011;
  fargs.interface = INTERFACE_B;
  fargs.serialname = NULL;
  fargs.speed = 100000;

  int args_consumed;
  if ((args_consumed = fcom_args(&fargs, argc, argv)) < 0) {
    usage(argv[0]);
  }
  parse_i2c_args(wbuf, &wcnt, &rcnt, &slv, (argc - args_consumed), 
                 &argv[args_consumed]);
  
  if (!rcnt && !wcnt) {
    prn_error("No writes or reads to perform\n");
    return -1;
  }
  
  if ((rv = ftdi_init(&fc)) < 0) {
    ERROR_FTDI("Initializing ftdi context", &fc);
    return rv;
  }
  fi2c_init(&fic, &fc);
  
  if ((rv = fi2c_open(&fic, &fargs)))
    return rv;
  
  if ((rv = fi2c_setclock(&fic, fargs.speed)))
    return rv;
  fic.slv = slv;
  
  if ((rv = fi2c_wr_rd(&fic, wbuf, wcnt, rbuf, rcnt))) {
    prn_error("Problem reading/writing i2c\n");
    return rv;
  }
  if (rcnt) 
    prn_output(rbuf, rcnt);

  rv = fi2c_close(&fic);
  return rv;
}
