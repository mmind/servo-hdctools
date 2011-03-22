// Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef __FTDIGPIO_H__
#define __FTDIGPIO_H__

#include <ftdi.h>
#include <unistd.h>
#include <string.h>
#include <stdint.h>
#include <stdio.h>

#ifdef __cplusplus
extern "C" {
#endif

#define FGPIO_ERR_NONE   0
#define FGPIO_ERR_WR     1
#define FGPIO_ERR_RD     2
#define FGPIO_ERR_MASK   3
#define FGPIO_ERR_NOIMP  4
  
#define ERROR_FGPIO(ecode, ...)                 \
  fprintf(stderr, "-E- (%d) ", ecode);          \
  fprintf(stderr, __VA_ARGS__)                 
  
#ifndef DEBUG
#define DEBUG_FGPIO(...)
#else
#define DEBUG_FGPIO(...)                                        \
  fprintf(stderr, "DEBUG: %s:%u ", __FILE__, __LINE__);		\
  fprintf(stderr, __VA_ARGS__)
#endif
  
#define CHECK_FGPIO(fgpioc, fx, ...) do {           \
    DEBUG_FGPIO(__VA_ARGS__);                       \
    if ((fgpioc->error = fx) < 0) {                 \
      ERROR_FGPIO(fgpioc->error,__VA_ARGS__);       \
    }                                               \
  } while (0)

enum fgpio_type {
  TYPE_STANDARD,
  TYPE_CBUS
};

struct fgpio_context { 
  // v--- DO NOT REORDER ---v
  struct ftdi_context *fc;
  struct gpio_s gpio;
  // ^--- DO NOT REORDER ---^
  int error;
};

int fgpio_init(struct fgpio_context *, struct ftdi_context *);
int fgpio_open(struct fgpio_context *, struct ftdi_common_args *);
int fgpio_wr_rd(struct fgpio_context *, struct gpio_s *, uint8_t *,
                enum ftdi_interface_type);
int fgpio_close(struct fgpio_context *);

#ifdef __cplusplus
}
#endif

#endif //__FTDIGPIO_H__
