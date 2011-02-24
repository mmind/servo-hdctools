// Copyright (c) 2010 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef __FI2C_H__
#define __FI2C_H__

#include <ftdi.h>
#include <unistd.h>
#include <string.h>
#include <stdint.h>
#include <stdio.h>
#include "ftdi_common.h"

#ifdef __cplusplus
extern "C" {
#endif
  
// bit positions various signals in interface
#define SCL_POS 0x01
#define SDA_POS 0x02
// note, 0x04 has to be tied to SDA for I/O capabilities
#define SDB_POS 0x04

#define GP0_POS 0x08
#define GP1_POS 0x10
#define GP2_POS 0x20
#define GP3_POS 0x40
#define GP4_POS 0x80

#define FI2C_BUF_SIZE (1<<8)
#define FI2C_CHUNKSIZE (1<<12)

#define FI2C_ERR_NONE   0
#define FI2C_ERR_FTDI   1
#define FI2C_ERR_ACK    2
#define FI2C_ERR_CLK    3
#define FI2C_ERR_READ   4
#define FI2C_ERR_WRITE  5

  
#define ERROR_FI2C(ecode, ...)                  \
  fprintf(stderr, "-E- (%d) ", ecode);          \
  fprintf(stderr, __VA_ARGS__)                 
  
#ifndef DEBUG
#define DEBUG_FI2C(...)
#else
#define DEBUG_FI2C(...)	prn_dbg( __VA_ARGS__)
#endif
  
#define CHECK_FI2C(fic, fx, ...) do {           \
    DEBUG_FI2C(__VA_ARGS__);			\
    if ((fic->error = fx) < 0) {                \
      ERROR_FI2C(fic->error,__VA_ARGS__);       \
    }                                           \
  } while (0)
  
  
#define FI2C_WBUF(fic, val) \
  fic->buf[fic->bufcnt++] = val

// buf = { cmd, val, dir }
#define FI2C_CFG_IO(fic, val, dir) do {                                \
    FI2C_WBUF(fic, SET_BITS_LOW);                                      \
    FI2C_WBUF(fic, ((val) | fic->gpio.value));                         \
    FI2C_WBUF(fic, ((dir) | fic->gpio.direction));                     \
  } while (0)
  
struct fi2c_context { 
  // v--- DO NOT REORDER ---v
  struct ftdi_context *fc;
  struct gpio_s gpio;
  // ^--- DO NOT REORDER ---^
  unsigned int clk;
  int error;
  uint8_t slv;
  uint8_t *buf;
  int bufcnt;
  int bufsize;
};

int fi2c_init(struct fi2c_context *fic, struct ftdi_context *fc);
int fi2c_open(struct fi2c_context *fic, struct ftdi_common_args *fargs);
int fi2c_setclock(struct fi2c_context *fic, uint32_t clkhz);
int fi2c_reset(struct fi2c_context *fic);
int fi2c_wr_rd(struct fi2c_context *fic, uint8_t *wbuf, int wcnt,
               uint8_t *rbuf, int rcnt);
int fi2c_close(struct fi2c_context *fic);

#ifdef __cplusplus
}
#endif
#endif //__FI2C_H__
