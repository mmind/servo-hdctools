// Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#define _BSD_SOURCE
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

#define MAX_BUF 512
#define CLIENT_FIELDS 2

static void usage(char *progname) {
  printf("%s [common ftdi args]\n\n", progname);
  exit(-1);
}

// parse_buffer - parse buffer from client
//
// fmt is <direction>,<value>
// ex)    0xff,0xff  -- sets all to output '1'
static int parse_buffer(char *buf, struct gpio_s *gpio) {
  char *eptr = NULL;
  
  gpio->direction = strtoul(buf, &eptr, 0);
  if (eptr[0] != ',') {
    prn_error("Malformed direction argument\n");
    return 1;
  }
  eptr++;
  char *bptr = eptr;
  gpio->value = strtoul(bptr, &eptr, 0);
  if (((eptr[0] != '\r') && (eptr[0] != '\n')) ||
      (bptr == eptr)) {
    prn_error("Malformed value argument %c\n", eptr[0]);
    return 1;
  }
  prn_dbg("Done parsing buffer m:0x%02x d:0x%02x v:0x%02x\n",
          gpio->mask, gpio->direction, gpio->value);
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
static int process_client(struct fgpio_context *fgc, int client) {

  char buf[MAX_BUF];
  int blen, bcnt;
  struct gpio_s new_gpio;
  uint8_t rd_val;

  memset(buf, 0, MAX_BUF);
  if ((blen = read(client,buf,MAX_BUF-1)) <= 0) {
    if (blen == 0) {
      prn_info("client connection (fd=%d) hung up\n", client);
      return 1;
    } else {
      perror("reading from client");
      exit(1);
    }
  }

  prn_dbg("client (fd=%d) cmd: %s",client, buf);

  new_gpio.mask = fgc->gpio.mask;
  if (parse_buffer(buf, &new_gpio)) {
    snprintf(buf, MAX_BUF,
             "E:parsing client request.  Should be <dir>,<val>.\n");
    goto CLIENT_RSP;
  }
  if (fgpio_wr_rd(fgc, &new_gpio, &rd_val, GPIO)) {
    snprintf(buf, MAX_BUF, "E:writing/reading gpio\n");
    goto CLIENT_RSP;
  }
  snprintf(buf, MAX_BUF, "I:0x%02x\nA:\n", rd_val);

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

static void run_server(struct fgpio_context *fgc, int server_fd) {
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
	  if (process_client(fgc, i)) {
	    close(i);
	    FD_CLR(i, &master_fds);
	  }
	}
      }
    }
  }
}

int main(int argc, char **argv) {
  int sock;

  struct ftdi_context fc;
  struct fgpio_context fgc;
  struct fuart_context fcc;

  struct ftdi_common_args fargs = {
    .interface = 0,
    .vendor_id = 0x18d1,
    .product_id = 0x5000,
    .speed = 115200,
    .bits = BITS_8,
    .parity = NONE,
    .sbits = STOP_BIT_1
  };
 
  int args_consumed;
  if ((args_consumed = fcom_args(&fargs, argc, argv)) < 0) {
    usage(argv[0]);
  }

  if (ftdi_init(&fc) < 0) {
    ERROR_FTDI("Initializing ftdi context", &fc);
    return 1;
  }

  if (fgpio_init(&fgc, &fc)) {
    prn_error("fgpio_init\n");
    return FCOM_ERR;
  }
  if (fgpio_open(&fgc, &fargs)) {
    prn_error("fgpio_open\n");
    return FCOM_ERR;
  }
  if (fuart_init(&fcc, &fc)) {
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

  // TODO(tbroch) this should be configurable
  sock = init_server(9999);
  run_server(&fgc, sock);
  return 0;
}
