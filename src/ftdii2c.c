// Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include <assert.h>
#include <ftdi.h>
#include <stdio.h>

#include "ftdi_common.h"
#include "ftdii2c.h"

static int fi2c_start_bit_cmds(struct fi2c_context *fic) {
  int i;

  // for now don't allow starts in middle of a command buffer
  assert(fic->bufcnt == 0);

  // TODO(tbroch) factor in whether its high speed dev or not
  // guarantee minimum setup time between SDA -> SCL transistions
  for (i = 0; i < 4; i++) {
    // SCL & SDA high
    FI2C_CFG_IO(fic, 0, 0);
  }
  
  for (i = 0; i < 4; i++) {
    // SCL high, SDA low
    FI2C_CFG_IO(fic, 0, (SDA_POS));
   }
  
  // SCL & SDA low
  FI2C_CFG_IO(fic, 0, (SCL_POS | SDA_POS));
  
  return FI2C_ERR_NONE;
}

static int fi2c_stop_bit_cmds(struct fi2c_context *fic) {
  int i;

  // guarantee minimum setup time between SDA -> SCL transistions
  for (i = 0; i < 4; i++) {
    // SCL high, SDA low
    FI2C_CFG_IO(fic, 0, (SDA_POS));
  }
  
  for (i = 0; i < 4; i++) {
    // SCL & SDA high
    FI2C_CFG_IO(fic, 0, 0);
  }

  // SCL & SDA release
  FI2C_CFG_IO(fic, 0, 0);

  return FI2C_ERR_NONE;
}

static int fi2c_write_cmds(struct fi2c_context *fic) {
  int bytes_wrote = 0;
  int bufcnt = fic->bufcnt;

  fic->bufcnt = 0;
  bytes_wrote = ftdi_write_data(fic->fc, fic->buf, bufcnt);

  if (bytes_wrote < 0) {
    ERROR_FTDI("fi2c_write_cmds", fic->fc);
    return FI2C_ERR_FTDI;
  } else if (bytes_wrote != bufcnt) {
    return FI2C_ERR_WRITE;
  }
  return FI2C_ERR_NONE;
}

// TODO(tbroch) can we use the WAIT_ON_x cmds to postpone checking and increase
//              the payload to/from ftdi queues.  At the very least use 
//              WAIT_ON to h/w check the ack for speeds sake
static int fi2c_send_byte_and_check(struct fi2c_context *fic, uint8_t data) {
  int bytes_read;
  uint8_t rdbuf[1];

  // clk the single byte out
  FI2C_WBUF(fic, FTDI_CMD_MFE_CLK_BIT_OUT);
  FI2C_WBUF(fic, 0x07);
  FI2C_WBUF(fic, data);

  // SCL low, SDA release for Ack
  FI2C_CFG_IO(fic, 0, SCL_POS);
  
  // read of the ack (cmd,num of bits)
  FI2C_WBUF(fic, FTDI_CMD_LRE_CLK_BIT_IN);
  FI2C_WBUF(fic, 0x00);

  // force rx buffer back to host so you can see ack/noack
  FI2C_WBUF(fic, SEND_IMMEDIATE);

  CHECK_FI2C(fic, fi2c_write_cmds(fic), "write cmds for ack check\n");
  prn_dbg("bufcnt after write = %d\n", fic->bufcnt);

  // TODO(tbroch) this is s/w ACK should be doable via h/w WAIT_ON_x
  bytes_read = ftdi_read_data(fic->fc, rdbuf, 1);
  if (bytes_read < 0) {
    ERROR_FTDI("read of ack", fic->fc);
    return FI2C_ERR_FTDI;
  }
  if (bytes_read != 1) {
    prn_error("bytes read %d != 1\n", bytes_read);
    return FI2C_ERR_READ;
  } else {
    if ((rdbuf[0] & 0x80) != 0x0) {
      prn_error("ack read 0x%02x != 0x0\n", (rdbuf[0] & 0x80));
      return FI2C_ERR_ACK;
    }
    prn_dbg("saw the ack 0x%02x\n", rdbuf[0]);
  }

  // TODO(tbroch) : shouldn't need to pull SDA high here but get strange results
  // otherwise.  Needs investigation
  // SCL low, SDA high
  FI2C_CFG_IO(fic, SDA_POS, (SCL_POS | SDA_POS));
  return FI2C_ERR_NONE;
}

static int fi2c_send_slave(struct fi2c_context *fic, int read) {
  return fi2c_send_byte_and_check(fic, (fic->slv<<1) | (read ? 0x1 : 0x0));
}

static int fi2c_wr(struct fi2c_context *fic, uint8_t *wbuf, int wcnt) {
  int i;

  for (i = 0; i < wcnt; i++) {
    CHECK_FI2C(fic, fi2c_send_byte_and_check(fic, wbuf[i]), 
               "wr byte look for ack\n");
    if (fic->error)
      return fic->error;
  }
  return FI2C_ERR_NONE;
}

static int fi2c_rd(struct fi2c_context *fic, uint8_t *rbuf, int rcnt) {
  int i;

  for (i = 0; i < rcnt; i++) {
    // SCL low
    FI2C_CFG_IO(fic, 0, SCL_POS);
    
    FI2C_WBUF(fic, FTDI_CMD_MRE_CLK_BYTE_IN);
    FI2C_WBUF(fic, 0x00);
    FI2C_WBUF(fic, 0x00);
    
    if (i == rcnt - 1) {
      // last byte ... send NACK
      FI2C_CFG_IO(fic, 0, (SCL_POS));
      FI2C_WBUF(fic, FTDI_CMD_MFE_CLK_BIT_OUT);
      FI2C_WBUF(fic, 0x0);
      FI2C_WBUF(fic, 0xff);
    } else {
      // send ACK
      FI2C_CFG_IO(fic, 0, (SCL_POS | SDA_POS ));
      FI2C_WBUF(fic, FTDI_CMD_MFE_CLK_BIT_OUT);
      FI2C_WBUF(fic, 0x0);
      FI2C_WBUF(fic, 0x0);
    }
  }
  FI2C_WBUF(fic, SEND_IMMEDIATE);
  CHECK_FI2C(fic, fi2c_write_cmds(fic), "FTDI cmd write for read\n");
  if (fic->error) 
    return fic->error;

  int bytes_read;
  if ((bytes_read = ftdi_read_data(fic->fc, rbuf, rcnt)) != rcnt) {
    if (bytes_read < 0) {
      ERROR_FTDI("FTDI read bytes", fic->fc);
    } else {
      prn_error("ftdi bytes_read %d != %d expected\n", bytes_read, rcnt);
    }
    return FI2C_ERR_READ;
  }
  return FI2C_ERR_NONE;
}

int fi2c_init(struct fi2c_context *fic, struct ftdi_context *fc) {
  assert(fic);
  memset(fic, 0, sizeof(*fic));

  fic->fc = fc;
  fic->fc->usb_read_timeout = 10000;
  if ((fic->buf = malloc(FI2C_BUF_SIZE)) != NULL) {
    fic->bufsize = FI2C_BUF_SIZE;
  }
  fic->bufcnt = 0;

  // init all inputs
  fic->gpio.direction = 0;
  fic->gpio.value = 0;
  fic->gpio.mask = ~(SCL_POS | SDA_POS | SDB_POS);
  fic->error = FI2C_ERR_NONE;

  return FI2C_ERR_NONE;
}

int fi2c_open(struct fi2c_context *fic, struct ftdi_common_args *fargs) {

  ftdi_set_interface(fic->fc, fargs->interface);
  if (!IS_FTDI_OPEN(fic->fc)) {
    int rv = ftdi_usb_open_desc(fic->fc, fargs->vendor_id, fargs->product_id,
                                NULL, fargs->serialname);
    if (rv < 0 && rv != -5) {
      ERROR_FTDI("Opening usb connection", fic->fc);
      prn_error("vid:0x%02x pid:0x%02x serial:%s\n", fargs->vendor_id,
                fargs->product_id, fargs->serialname);
      return rv;
    }
  }
  if (!fcom_is_mpsse(fic->fc, fargs)) {
    prn_error("ftdi device / interface doesn't support MPSSE\n");
    return FI2C_ERR_FTDI;
  }
  return fcom_cfg(fic->fc, fargs->interface, BITMODE_MPSSE, 0);
}

int fi2c_setclock(struct fi2c_context *fic, uint32_t clk) {
  uint8_t  buf[3] = { 0, 0, 0 };



  buf[0] = FTDI_CMD_3PHASE;
  CHECK_FTDI(ftdi_write_data(fic->fc, buf, 1), "Set 3-phase clocking",
             fic->fc);
  if (clk > FTDI_CLK_MAX_X5 || clk < FTDI_CLK_MIN) {
    return FI2C_ERR_CLK;
  }
  if (clk > FTDI_CLK_MAX_X5) {
    buf[0] = FTDI_CMD_X5_OFF;
    CHECK_FTDI(ftdi_write_data(fic->fc, buf, 1), "Set master clock 60mhz",
               fic->fc);
  }
  // 1.5 due to 3-phase requirement
  int div = DIV_VALUE((clk*1.5));
  if (!div) {
    prn_error("Unable to determine clock divisor\n");
    return FI2C_ERR_CLK;
  }
  buf[0] = TCK_DIVISOR;
  buf[1] = (div >> 0) & 0xFF;
  buf[2] = (div >> 8) & 0xFF;
  CHECK_FTDI(ftdi_write_data(fic->fc, buf, 3), "Set clk div", fic->fc);
  return FI2C_ERR_NONE;
}

int fi2c_reset(struct fi2c_context *fic) {
  CHECK_FI2C(fic, fi2c_start_bit_cmds(fic), "Start sent as reset\n");
  CHECK_FI2C(fic, fi2c_write_cmds(fic), "FTDI write cmds\n");
  fic->error = FI2C_ERR_NONE;
  return fic->error;
}

int fi2c_wr_rd(struct fi2c_context *fic, uint8_t *wbuf, int wcnt,
                     uint8_t *rbuf, int rcnt) {
  int err;
  static int retry_count = 0;

 retry:
  // flush both buffers to guarantee clean restart
  if (retry_count) {
    CHECK_FTDI(ftdi_usb_purge_buffers(fic->fc), "Purge rx/tx buf", fic->fc);
  }
  if (wcnt && wbuf) {
#ifdef DEBUG
    printf("begin write of: ");
    int i;
    for (i = 0; i < wcnt; i++) {
      printf("0x%02x ", wbuf[i]);
    } 
    printf("\n");
#endif
    CHECK_FI2C(fic, fi2c_start_bit_cmds(fic), "(WR) Start bit\n");
    err = fi2c_send_slave(fic, 0);
    if (err == FI2C_ERR_READ) {
          retry_count++;
          goto retry;
    }
    if (!fic->error && !err) {
      err = fi2c_wr(fic, wbuf, wcnt);
      if (err == FI2C_ERR_READ) {
          retry_count++;
          goto retry;
    }
      CHECK_FI2C(fic, fi2c_stop_bit_cmds(fic), "(WR) Stop bit\n");
      CHECK_FI2C(fic, fi2c_write_cmds(fic), "(WR) FTDI write cmds\n");
    }
  }
  if (rcnt && rbuf && !fic->error) {
    prn_dbg("begin read\n");
    CHECK_FI2C(fic, fi2c_start_bit_cmds(fic), "(RD) Start bit\n");
    err = fi2c_send_slave(fic, 1);
      if (err == FI2C_ERR_READ) {
          retry_count++;
          goto retry;
    }
    CHECK_FI2C(fic, fi2c_rd(fic, rbuf, rcnt), "(RD) Payload\n");
#ifdef DEBUG
    printf("end read: ");
    int i;
    for (i = 0; i < rcnt; i++) {
      printf("0x%02x ", rbuf[i]);
    } 
    printf("\n");
#endif
  }
  // TODO(tbroch) debug why this is necessary.  W/o I get sporadic
  // ftdi_usb_read_data failures.  Might be able to remedy by looking at 
  // error codes from ftdi_read/write ( -666 ) or errno -16 (EBUSY)
  // NOTE, removing exposes bug on linux w/ bad results
  CHECK_FTDI(ftdi_usb_purge_tx_buffer(fic->fc), "Purge tx buf", fic->fc);
  prn_dbg("done.  Error = %d, Retry count = %d\n", fic->error, retry_count);
  return fic->error;
}

int fi2c_close(struct fi2c_context *fic) {
  CHECK_FTDI(ftdi_usb_close(fic->fc), "fic close", fic->fc);
  ftdi_deinit(fic->fc);
  return FI2C_ERR_NONE;
}

