# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Definitions which control the C compiler on Linux.
#
# Please keep this file sorted to facilitate comparisons against other
# operating systems.

# TODO(tbroch) Return strict prototypes if/when failures like below remedied
#   in libftdi1.
#   /usr/include/libftdi1/ftdi.h:438:12: error: function declaration isn't a
#   prototype [-Werror=strict-prototypes]
#	-Wstrict-prototypes			\
#	-pedantic-errors			\

ifndef HOSTOS_STACK_PROTECTOR
# -Wstack-protector breaks the build on Beaglebone boards, so we
# need to be able to omit it there.
HOSTOS_STACK_PROTECTOR =	-Wstack-protector
endif

HOSTOS_CWARN	=				\
	-Waddress				\
	-Waggregate-return			\
	-Wall					\
	-Warray-bounds				\
	-Wbad-function-cast			\
	-Wcast-align				\
	-Wcast-qual				\
	-Wchar-subscripts			\
	-Wclobbered				\
	-Wcomment				\
	-Wdeclaration-after-statement		\
	-Wdisabled-optimization			\
	-Wempty-body				\
	-Werror					\
	-Wextra					\
	-Wfloat-equal				\
	-Wformat				\
	-Wformat-nonliteral			\
	-Wformat-security			\
	-Wformat-y2k				\
	-Wignored-qualifiers			\
	-Wimplicit				\
	-Winit-self				\
	-Winline				\
	-Wlogical-op				\
	-Wmain					\
	-Wmissing-braces			\
	-Wmissing-declarations			\
	-Wmissing-field-initializers		\
	-Wmissing-format-attribute		\
	-Wmissing-include-dirs			\
	-Wmissing-parameter-type		\
	-Wmissing-prototypes			\
	-Wnested-externs			\
	-Wold-style-declaration			\
	-Wold-style-definition			\
	-Woverlength-strings			\
	-Woverride-init				\
	-Wpacked				\
	-Wparentheses				\
	-Wpointer-arith				\
	-Wpointer-sign				\
	-Wredundant-decls			\
	-Wreturn-type				\
	-Wsequence-point			\
	-Wshadow				\
	-Wsign-compare				\
	-Wstrict-aliasing			\
	-Wstrict-aliasing=3			\
	-Wstrict-overflow			\
	-Wstrict-overflow=5			\
	-Wswitch				\
	-Wswitch-default			\
	-Wtrigraphs				\
	-Wtype-limits				\
	-Wundef					\
	-Wuninitialized				\
	-Wunknown-pragmas			\
	-Wunsafe-loop-optimizations		\
	-Wunused-function			\
	-Wunused-label				\
	-Wunused-parameter			\
	-Wunused-value				\
	-Wunused-variable			\
	-Wvariadic-macros			\
	-Wvla					\
	-Wvolatile-register-var			\
	-Wwrite-strings				\
	$(HOSTOS_STACK_PROTECTOR)

HOSTOS_LD_LIB	= -shared -Wl,-soname,$@
HOSTOS_LIB_EXT	= so
HOSTOS_CFLAGS	= -fPIC
