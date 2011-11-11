// Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.
#include <arpa/inet.h>
#include <assert.h>
#include <errno.h>
#include <ftdi.h>
#include <inttypes.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <unistd.h>

#include "ftdi_common.h"
#include "ftdigpio.h"
#include "ftdiuart.h"
#include "ftdii2c.h"

#define MAX_BUF 512
#define GPIO_FIELDS 3

static void usage(char *progname) {
  printf("%s [common ftdi args]\n\n", progname);
  exit(-1);
}

// parse_ul_element - parse element return non-zero for error else properly
// converted value returned in value and buf set to character beyond delimeter
static char *parse_ul_element(unsigned long *value, char *buf, char delim) {
  char *eptr;
  *value = strtoul(buf, &eptr, 0);
  if (!delim) {
    return eptr;
  } else if (eptr[0] != delim) {
    return NULL;
  }
  return eptr + 1;
}

// parse_buffer_gpio - parse gpio command from client
// <interface>,<direction>,<value>[,<mask>]
// ex)    1,0xff,0xff  -- set all gpios to output '1' on interface 1
static int parse_buffer_gpio(char *buf, struct gpio_s *gpio,
                      unsigned int *interface) {

  char *bptr = buf;
  unsigned long tmp_ul;

  if (((bptr = parse_ul_element(&tmp_ul, bptr, ',')) == NULL) ||
      (!tmp_ul || (tmp_ul > 4))) {
    prn_error("Malformed interface argument\n");
    return 1;
  }
  *interface = (unsigned int)tmp_ul;

  if (((bptr = parse_ul_element(&tmp_ul, bptr, ',')) == NULL) ||
      (tmp_ul > 0xff)) {
    prn_error("Malformed direction argument\n");
    return 1;
  }
  gpio->direction = (uint8_t)tmp_ul;
  if (((bptr = parse_ul_element(&tmp_ul, bptr, 0)) == NULL) ||
      (tmp_ul > 0xff)) {
    prn_error("Malformed value argument\n");
    return 1;
  }
  gpio->value = (uint8_t)tmp_ul;
  if (bptr[0] == ',') {
    bptr++;
    // there's a mask
    if (((bptr = parse_ul_element(&tmp_ul, bptr, 0)) == NULL) ||
        (tmp_ul > 0xff)) {
      prn_error("Malformed mask argument\n");
      return 1;
    }
    gpio->mask = (uint8_t)tmp_ul;
  } else {
    gpio->mask = 0xff;
  }
  prn_dbg("Done parsing gpio buffer i:%d d:0x%02x v:0x%02x m:0x%02x\n",
          *interface, gpio->direction, gpio->value, gpio->mask);
  return 0;
}
// parse_buffer_i2c - parse i2c command from client
// ex)    0x40,1,0x0,2 -- for i2c slave 0x40 write 1byte 0, read 2bytes
static int parse_buffer_i2c(char *buf, int *argc, uint8_t *argv) {
  int argcnt = 0;
  char *field;
  field = strtok(buf, ",");
  while (field) {
    argv[argcnt++] = strtoul(field,  NULL, 0);
    field = strtok(NULL, ",");
  }
  // do some checking
  if ((argcnt > 2) && (argcnt < argv[1] + 2)) {
    prn_error("looks like i2c write w/o enough data\n");
    return -1;
  } else if (argcnt < 2) {
    prn_error("Must have at least 2 arguments to i2c cmd=%s\n", buf);
    return -1;
  }
  *argc = argcnt;
  return 0;
}

// process_client - interact w/ client connection
//
// response to client looks like:
// I:<read value>
// A:
//
// or in case of error
// E:<msg>
//
// where:
//    read value == value read for that bank of 8 gpios
//    msg == detailed message of error condition
static int process_client(struct ftdi_itype *interfaces,
                          int int_cnt, int client) {

  char buf[MAX_BUF];
  char *rsp = buf;
  int blen, bcnt, err;
  struct gpio_s new_gpio;
  uint8_t rd_val;

  struct ftdi_itype *interface;

  memset(rsp, 0, MAX_BUF);
  if ((blen = read(client,buf,MAX_BUF-1)) <= 0) {
    if (blen == 0) {
      prn_info("client connection (fd=%d) hung up\n", client);
      return 1;
    } else {
      perror("reading from client ... guess he disappeared");
      return 1;
    }
  }

  prn_dbg("client cmd: %s",buf);
  if ((buf[0] == 'g') && (buf[1] == ',')) {
    unsigned int interface_num;
    if (parse_buffer_gpio(&buf[2], &new_gpio, &interface_num)) {
      snprintf(buf, MAX_BUF,
               "E:parsing client request.  Should be\n\t%s\n",
               "<interface>,<dir>,<val>[,<mask>]");
      goto CLIENT_RSP;
    }

    interface = fcom_lookup_interface(interfaces, int_cnt, interface_num, ANY);
    if (interface == NULL) {
      snprintf(rsp, MAX_BUF, "E:No gpio at interface %d\n", interface_num);
      goto CLIENT_RSP;
    }

    struct fgpio_context *fgc = NULL;
    fgc = (struct fgpio_context *)interface->context;
    assert(fgc);
    if ((err = fgpio_wr_rd(fgc, &new_gpio, &rd_val, interface->type))) {
      if (err == FGPIO_ERR_MASK) {
        snprintf(rsp, MAX_BUF, "E:Illegal gpio mask.  Bits avail are 0x%02x\n",
                 fgc->gpio.mask);
      } else {
        snprintf(rsp, MAX_BUF, "E:writing/reading gpio\n");
      }
      goto CLIENT_RSP;
    }
    snprintf(rsp, MAX_BUF, "I:0x%02x\nA:\n", rd_val);
  } else if ((buf[0] == 'i') && (buf[1] == ',')) {
    int argcnt = 0;

    uint8_t args[128];
    uint8_t rbuf[128];
    if (parse_buffer_i2c(&buf[2], &argcnt, args)) {
      snprintf(rsp, MAX_BUF, "E:parsing client request.  Should be\n\t%s\n",
               "<slv>,[<bytes to Wr>,<Wr0>,<Wr1>,<WrN>],[<bytes to Rd>]");
      goto CLIENT_RSP;
    }

    interface = fcom_lookup_interface(interfaces, int_cnt, 2, I2C);
    if (interface == NULL) {
      snprintf(rsp, MAX_BUF, "E:No i2c at interface 2\n");
      goto CLIENT_RSP;
    }
    struct fi2c_context *fic = NULL;
    fic = (struct fi2c_context *)interface->context;
    assert(fic);

    // defaults if read-only
    uint8_t *wbuf = NULL;
    int wcnt = 0;
    int rcnt = args[argcnt-1];
    fic->slv = args[0];
    if (argcnt > 2) {
      wbuf = &args[2];
      wcnt = args[1];
      if (argcnt != wcnt + 3) {
        // its just a write
        rcnt = 0;
      }
    }
    if (fi2c_wr_rd(fic, wbuf, wcnt, rbuf, rcnt)) {
      snprintf(rsp, MAX_BUF, "E:writing/reading i2c\n");
      goto CLIENT_RSP;
    }
    int bytes_remaining = MAX_BUF;
    if (rcnt) {
      snprintf(rsp, bytes_remaining, "I:0x");
      rsp = rsp + 4;
      bytes_remaining-=4;
      int i;
      for (i = 0; i < rcnt; i++) {
        if (i && !(i % 4)) {
          snprintf(rsp, bytes_remaining, "\nI:0x");
          rsp+=5;
          bytes_remaining-=5;
        }
        snprintf(rsp, bytes_remaining, "%02x", rbuf[i]);
        rsp+=2;
        bytes_remaining-=2;
        if (bytes_remaining < 5) {
          snprintf(buf, MAX_BUF, "E: i2c request too large.  See developer\n");
          goto CLIENT_RSP;
        }
      }
    }
    snprintf(rsp, bytes_remaining, "\nA:\n");
  } else {
      snprintf(rsp, MAX_BUF,
               "E:parsing client request.  Should be\n\t%s\n\t%s\n",
               "g,<interface>,<dir>,<val>",
               "i,<slv>,<bytes to write(4max)>,<write word>,<bytes to read>");
  }

CLIENT_RSP:
  blen = strlen(buf);
  bcnt = write(client, buf, blen);
  if (bcnt != blen)
    perror("writing to client");
  return 0;
}

static int init_socket(int port) {
  struct sockaddr_in server_addr;

  prn_dbg("Initializing server\n");
  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock < 0)
    perror("opening socket");

  memset(&server_addr, 0, sizeof(server_addr));

  server_addr.sin_family = AF_INET;
  server_addr.sin_addr.s_addr = INADDR_ANY;
  server_addr.sin_port = htons(port);

  int tr = 1;
  if (setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &tr, sizeof(int)) == -1) {
    perror("setting sockopt");
    exit(-1);
  }
  if (bind(sock, (struct sockaddr *) &server_addr, sizeof(server_addr)) < 0) {
    perror("binding socket");
    exit(-1);
  }

  return sock;
}

static int init_server(int port) {
  int sock = init_socket(port);

  assert(listen(sock, 5) == 0);
  prn_dbg("Server initialized\n");
  return sock;
}

static void run_server(struct ftdi_itype *interfaces, int int_cnt, int server_fd) {
  struct sockaddr_in client_addr;
  fd_set read_fds, master_fds;
  unsigned int client_len = sizeof(client_addr);

  FD_ZERO(&read_fds);
  FD_ZERO(&master_fds);
  int max_fd = server_fd;
  FD_SET(server_fd, &master_fds);

  prn_dbg("Running server fd=%d\n", server_fd);
  while (1) {
    read_fds = master_fds;

    if(select(max_fd+1, &read_fds, NULL, NULL, NULL) == -1) {
      perror("Select test failed");
      exit(1);
    }
    prn_dbg("select ok\n");

    int i;
    for (i = 0; i <= max_fd; i++) {
      if (FD_ISSET(i, &read_fds)) {
	if (i == server_fd) {
	  // add new clients
	  int new_client = accept(server_fd, (struct sockaddr *)&client_addr,
                                  &client_len);
	  if (new_client < 0) {
	    perror("accepting connection");
            exit(1);
	  } else {
	    prn_info("Client connected %s fd:%d\n",
                     inet_ntoa(client_addr.sin_addr), new_client);
	    FD_SET(new_client, &master_fds);
	    if (new_client > max_fd) {
	      max_fd = new_client;
	      prn_dbg("max_fd increased to %d\n", max_fd);
	    }
	  }
	} else {
	  // process connected clients
	  if (process_client(interfaces, int_cnt, i)) {
	    close(i);
	    FD_CLR(i, &master_fds);
	  }
	}
      }
    }
  }
}

#define NUM_GPIOS 2
#define NUM_INTERFACES 4

int main(int argc, char **argv) {
  int sock;

  struct ftdi_common_args fargs = {
    .interface = 0,
    //.vendor_id = 0x18d1,
    //.product_id = 0x5001,
    .vendor_id = 0x0403,
    .product_id = 0x6011,
    .speed = 115200,
    .bits = BITS_8,
    .parity = NONE,
    .sbits = STOP_BIT_1
  };

  int args_consumed;
  if ((args_consumed = fcom_args(&fargs, argc, argv)) < 0) {
    usage(argv[0]);
  }

  int i;
  struct ftdi_context fc[NUM_INTERFACES];
  struct fgpio_context fgs[NUM_GPIOS];

  for (i = 0; i < NUM_INTERFACES; i++) {
    if (ftdi_init(&fc[i]) < 0) {
      ERROR_FTDI("Initializing ftdi context", &fc[i]);
      return 1;
    }
  }

  struct ftdi_itype interfaces[NUM_INTERFACES];

  for (i = 0; i < NUM_GPIOS; i++) {
    if (fgpio_init(&fgs[i], &fc[i])) {
      prn_error("fgpio_init\n");
      return FCOM_ERR;
    }
  }

  // should be JTAG/SPI ... but GPIOs for now or use flashrom/openocd separately
  fargs.interface = 1;
  if (fgpio_open(&fgs[0], &fargs)) {
    prn_error("fgpio_open\n");
    return FCOM_ERR;
  }
  interfaces[fargs.interface - 1].context = (void *)&fgs[0];
  interfaces[fargs.interface - 1].type = GPIO;

  // i2c master
  struct fi2c_context fic;
  fargs.interface = 2;
  if (fi2c_init(&fic, &fc[3])) {
    prn_error("fi2c_init\n");
    return FCOM_ERR;
  }
  if (fi2c_open(&fic, &fargs)) {
    prn_error("fi2c_open\n");
    return FCOM_ERR;
  }
  // 100khz
  if (fi2c_setclock(&fic, 100000)) {
    prn_error("fi2c_setclock\n");
    return FCOM_ERR;
  }
  interfaces[fargs.interface - 1].context = (void *)&fic;
  interfaces[fargs.interface - 1].type = I2C;

  // DUT console uart
  fargs.interface = 3;
  struct fuart_context fcc;
  if (fuart_init(&fcc, &fc[2])) {
    prn_error("fuart_init\n");
    return FCOM_ERR;
  }
  if (fuart_open(&fcc, &fargs)) {
    prn_error("fuart_open\n");
    return FCOM_ERR;
  }
  printf("ftdi uart connected to pty at %s\n", fcc.name);
  if (fuart_run(&fcc, FUART_USECS_SLEEP)) {
    prn_error("fuart_run\n");
    return FCOM_ERR;
  }
  interfaces[fargs.interface - 1].context = (void *)&fcc;
  interfaces[fargs.interface - 1].type = UART;

  // legit gpios
  fargs.interface = 4;
  if (fgpio_open(&fgs[1], &fargs)) {
    prn_error("fgpio_open\n");
    return FCOM_ERR;
  }
  interfaces[fargs.interface - 1].context = (void *)&fgs[1];
  interfaces[fargs.interface - 1].type = GPIO;

  sock = init_server(9999);
  prn_info("%s running accepting connections at port %d\n", argv[0], 9999);
  run_server(interfaces, NUM_INTERFACES, sock);
  return 0;
}
