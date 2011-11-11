// Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <ftdi.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <termios.h>
#include <unistd.h>
#include <usb.h>

#include "ftdi_common.h"
#include "ftdiuart.h"


// TODO(tbroch) Where are these protos and under what conditions do they
//              exist across lin/mac/win
int grantpt(int fd);
int unlockpt(int fd);

#ifdef DARWIN
static int ptsname_r(int fd, char *buf, size_t buflen) {
  char *name = ptsname(fd);
  if (name == NULL) {
    errno = EINVAL;
    return -1;
  }
  if (strlen(name) + 1 > buflen) {
    errno = ERANGE;
    return -1;
  }
  strncpy(buf, name, buflen);
  return 0;
}
#endif


static void fuart_get_lock(struct fuart_context *fuartc) {
  pthread_mutex_lock(fuartc->lock);
}

static void fuart_release_lock(struct fuart_context *fuartc) {
  pthread_mutex_unlock(fuartc->lock);
}

static int fuart_init_locked(struct fuart_context *fuartc,
                             struct ftdi_context *fc) {
  fuartc->fc = fc;
  // init all inputs
  fuartc->gpio.direction = 0;
  fuartc->gpio.value = 0;
  // TODO(tbroch) NO OOB signal support (CTS,RTS,DCR,DTR)
  fuartc->gpio.mask = ~(TX_POS | RX_POS);

  fuartc->is_open = 0;
  fuartc->usecs_to_sleep = 0;
  fuartc->error = FUART_ERR_NONE;
  return FUART_ERR_NONE;
}

int fuart_init(struct fuart_context *fuartc, struct ftdi_context *fc) {
  assert(fuartc);
  memset(fuartc, 0, sizeof(*fuartc));
  fuartc->lock = malloc(sizeof(pthread_mutex_t));
  pthread_mutex_init(fuartc->lock, NULL);

  fuart_get_lock(fuartc);
  int rv = fuart_init_locked(fuartc, fc);
  fuart_release_lock(fuartc);
  return rv;
}

static int fuart_open_locked(struct fuart_context *fuartc,
                             struct ftdi_common_args *fargs) {
  int rv;

  struct ftdi_context *fc = fuartc->fc;
  assert(fc);

  ftdi_set_interface(fc, fargs->interface);
  if (!IS_FTDI_OPEN(fc)) {
    rv = ftdi_usb_open_desc(fc, fargs->vendor_id, fargs->product_id,
                            NULL, fargs->serialname);
    if (rv < 0) {
      ERROR_FTDI("Opening usb connection", fc);
      prn_error("vid:0x%02x pid:0x%02x serial:%s\n", fargs->vendor_id,
                fargs->product_id, fargs->serialname);
      return FUART_ERR_FTDI;
    }
  }
  if (fcom_num_interfaces(fc) > 1) {
    if ((rv = ftdi_set_interface(fc, fargs->interface))) {
      ERROR_FTDI("setting interface", fc);
      return FUART_ERR_FTDI;
    }
  }
  CHECK_FTDI(ftdi_set_bitmode(fc, TX_POS, BITMODE_RESET),
             "uart mode", fc);

  // TODO(tbroch) Do some checking of reasonable cfg/buadrate
  CHECK_FTDI(ftdi_set_line_property(fc, fargs->bits, fargs->sbits,
                                    fargs->parity), "line props", fc);
  CHECK_FTDI(ftdi_set_baudrate(fc, fargs->speed), "baudrate", fc);

  if (fc->type == TYPE_R) {
    int gpio_cfg = fargs->direction<<4 | fargs->value;
    CHECK_FTDI(ftdi_set_bitmode(fc, gpio_cfg, BITMODE_CBUS),
               "uart mode", fc);
  }

  int fd;
  if ((fd = posix_openpt(O_RDWR | O_NOCTTY)) == -1) {
    perror("opening pty master");
    return FUART_ERR_OPEN;
  }
  if (grantpt(fd) == -1) {
    perror("grantpt");
    return FUART_ERR_OPEN;
  }
  if (unlockpt(fd) == -1) {
    perror("unlockpt");
    return FUART_ERR_OPEN;
  }
  if (fcntl(fd, F_SETFL, O_NONBLOCK) == -1) {
    perror("fcntl setfl -> nonblock");
    return FUART_ERR_OPEN;
  }
  if (ptsname_r(fd, fuartc->name, FUART_NAME_SIZE) != 0) {
    perror("getting name of pty");
    return FUART_ERR_OPEN;
  }
  if (chmod(fuartc->name, (S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP | S_IROTH |
                           S_IWOTH))) {
    perror("chmod of pty");
    return FUART_ERR_OPEN;
  }
  prn_dbg("pty name = %s\n", fuartc->name);
  if (!isatty(fd)) {
    prn_error("Not a TTY device.\n");
    return FUART_ERR_OPEN;
  }
  struct termios tty_cfg;
  cfmakeraw(&tty_cfg);
  tcsetattr(fd, TCSANOW, &tty_cfg);

  fuartc->fd = fd;
  fuartc->is_open = 1;

  return FUART_ERR_NONE;
}

int fuart_open(struct fuart_context *fuartc,
                     struct ftdi_common_args *fargs) {
  fuart_get_lock(fuartc);
  int rv = fuart_open_locked(fuartc, fargs);
  fuart_release_lock(fuartc);
  return rv;
}

static int fuart_wr_rd_locked(struct fuart_context *fuartc) {

  int rv = FUART_ERR_NONE;
  int bytes, bytes_written;
  struct ftdi_context *fc = fuartc->fc;

  if ((bytes = read(fuartc->fd, fuartc->buf, sizeof(fuartc->buf))) > 0) {
#ifdef DEBUG
    fuartc->buf[bytes] = '\0';
    printf("about to write %d bytes to ftdi %s\n", bytes, fuartc->buf);
#endif
    bytes_written = ftdi_write_data(fc, fuartc->buf, bytes);
    if (bytes_written != bytes) {
      ERROR_FTDI("writing to uart", fc);
      rv = FUART_ERR_WR;
   }
  }
  rv = FUART_ERR_NONE;
  // guarantee at least a usec for yielding
  usleep(fuartc->usecs_to_sleep | 1);
  // TODO(tbroch) is there a lower cost way to interrogate ftdi for data.  How
  // does the event/error_char factor into things?
  bytes = ftdi_read_data(fc, fuartc->buf, sizeof(fuartc->buf));
  if (bytes > 0) {
    int bytes_remaining = bytes;
    while ((bytes = write(fuartc->fd, fuartc->buf, bytes_remaining)) > 0) {
      bytes_remaining -= bytes;
    }
    if (bytes == -1) {
      perror("writing ftdi data to pty");
    }

  } else if (bytes < 0) {
    perror("failed ftdi_read_data");
    ERROR_FTDI("reading ftdi data", fuartc->fc);
    rv = FUART_ERR_RD;
  }

  // TODO(tbroch) How do we guarantee no data loss for tx/rx
  return rv;
}

int fuart_wr_rd(struct fuart_context *fuartc) {
  fuart_get_lock(fuartc);
  int rv = fuart_wr_rd_locked(fuartc);
  fuart_release_lock(fuartc);
  return rv;
}

// thread start routine for uart interation/polling
static void *_fuart_run(void *ptr) {
  int error;
  struct fuart_context *fuartc = (struct fuart_context *)ptr;

  while (1) {
    if ((error = fuart_wr_rd(fuartc))) {
      prn_error("fuart_wr_rd error = %d", error);
      break;
    }
  }
  // should never reach
  return NULL;
}

// creates a thread to poll read/write to/from ftdi uart and pty
// returns FUART_ERR_NONE for success or error code for failure
static int fuart_run_locked(struct fuart_context *fuartc, int usecs_to_sleep) {
  int rv = FUART_ERR_NONE;
  pthread_t fuart_thread;

  if (!fuartc->is_open) {
    prn_error("Can't thread uart it isn't open\n");
    rv = FUART_ERR_THREAD;
  }

  fuartc->usecs_to_sleep = usecs_to_sleep;

  if (pthread_create(&fuart_thread, NULL, _fuart_run, (void *)fuartc)) {
    perror("threading fuart");
    rv = errno;
  }

  return rv;
}

int fuart_run(struct fuart_context *fuartc, int usecs_to_sleep) {
  fuart_get_lock(fuartc);
  int rv = fuart_run_locked(fuartc, usecs_to_sleep);
  fuart_release_lock(fuartc);
  return rv;
}

static int fuart_close_locked(struct fuart_context *fuartc) {
  int rv = FUART_ERR_NONE;

  close(fuartc->fd);
  fuartc->is_open = 0;
  CHECK_FTDI(ftdi_usb_close(fuartc->fc), "fuart close", fuartc->fc);
  ftdi_deinit(fuartc->fc);

  return rv;
}

int fuart_close(struct fuart_context *fuartc) {
  fuart_get_lock(fuartc);
  int rv = fuart_close_locked(fuartc);
  fuart_release_lock(fuartc);
  return rv;
}
