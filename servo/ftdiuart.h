// Copyright (c) 2010 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef __FTDIUART_H__
#define __FTDIUART_H__

#include <ftdi.h>
#include <unistd.h>
#include <string.h>
#include <stdint.h>
#include <stdio.h>

#ifdef __cplusplus
extern "C" {
#endif

#define FUART_BUF_SIZE 128
  
// bit positions various signals in interface
#define TX_POS  0x01
#define RX_POS  0x02
#define GPX_POS 0xfc

#define FUART_ERR_NONE   0
#define FUART_ERR_FTDI  -1 
#define FUART_ERR_OPEN  -2
#define FUART_ERR_WR    -3
#define FUART_ERR_RD    -4
  
#define ERROR_FUART(ecode, ...)                 \
  fprintf(stderr, "-E- (%d) ", ecode);          \
  fprintf(stderr, __VA_ARGS__)                 
  
#ifndef DEBUG
#define DEBUG_FUART(...)
#else
#define DEBUG_FUART(...)                                        \
  fprintf(stderr, "DEBUG: %s:%u ", __FILE__, __LINE__);		\
  fprintf(stderr, __VA_ARGS__)
#endif
  
#define CHECK_FUART(fuartc, fx, ...) do {           \
    DEBUG_FUART(__VA_ARGS__);                       \
    if ((fuartc->error = fx) < 0) {                 \
      ERROR_FUART(fuartc->error,__VA_ARGS__);       \
    }                                               \
  } while (0)

struct fuart_cfg {
  int baudrate;
  enum ftdi_bits_type bits;
  enum ftdi_stopbits_type sbits;
  enum ftdi_parity_type parity;
};

struct fuart_context { 
  char name[PATH_MAX];
  int fd;
  struct ftdi_context *fc;
  uint8_t buf[FUART_BUF_SIZE];
  struct gpio_s gpio;
  int error;
};

int fuart_init(struct fuart_context *, struct ftdi_context *);
int fuart_open(struct fuart_context *, struct ftdi_common_args *);
int fuart_wr_rd(struct fuart_context *, int);
int fuart_close(struct fuart_context *);

#ifdef __cplusplus
}
#endif

#endif //__FTDIUART_H__
