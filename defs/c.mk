# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file contains definitions which control the C compiler.
ifndef CC
$(warning CC not defined; assuming gcc.)
CC	= $(GCC)
endif

COPTIONS =					\
	-g					\
	-O2


# # Compiler is too old to support
# #
# #	-Wframe-larger-than=256
# #	-Wlarger-than=4096
# #	-Wsync-nand

# # Enable GC on unused functions and data
# CGC	=					\
# 	-ffunction-sections			\
# 	-fdata-sections

# Also need to link with '-Xlinker --library=pthread'.
PTHREAD	= 					\
	-pthread

# LDGC	=					\
# 	-Xlinker --gc-sections


#  TBD: These need code changes to enable.
#	-Wconversion				\
#	-Wdeclaration-after-statement		\
#	-Wmissing-noreturn			\
#	-Wsign-conversion			\
#	-Wtraditional-conversion		\

# CWARN_MAC, CWARN_LINUX:
#
#  Handle warning options which are specific to Mac or Linux.  This is
#  normally necessary because different compiler versions are used on
#  different systems.
#
#  If we end up needing more granularity than this, we should list &
#  use the newer options based on the compiler version being used.
ifeq ($(HDCTOOLS_OS_NAME),Darwin) # Mac
  CWARN_MAC	=
else
  ifeq ($(HDCTOOLS_OS_NAME),Linux)
    # Warning options supported only by Linux.
    CWARN_LINUX	=				\
	-Waddress				\
	-Warray-bounds				\
	-Wclobbered				\
	-Wempty-body				\
	-Wignored-qualifiers			\
	-Wlogical-op				\
	-Wmissing-parameter-type		\
	-Wold-style-declaration			\
	-Woverlength-strings			\
	-Woverride-init				\
	-Wstrict-overflow			\
	-Wstrict-overflow=5			\
	-Wtype-limits				\
	-Wunsafe-loop-optimizations		\
	-Wvla					\
	-Wvolatile-register-var
  else
    # NOP: No warnings for unsupported build, which fails below.
  endif
endif
CWARN	=					\
	$(CWARN_MAC)				\
	$(CWARN_LINUX)				\
	-Waggregate-return			\
	-Wall					\
	-Wbad-function-cast			\
	-Wcast-align				\
	-Wcast-qual				\
	-Wchar-subscripts			\
	-Wcomment				\
	-Wdisabled-optimization			\
	-Werror					\
	-Wextra					\
	-Wfloat-equal				\
	-Wformat				\
	-Wformat-nonliteral			\
	-Wformat-security			\
	-Wformat-y2k				\
	-Wimplicit				\
	-Winit-self				\
	-Winline				\
	-Wmain					\
	-Wmissing-braces			\
	-Wmissing-declarations			\
	-Wmissing-field-initializers		\
	-Wmissing-format-attribute		\
	-Wmissing-include-dirs			\
	-Wmissing-prototypes			\
	-Wnested-externs			\
	-Wold-style-definition			\
	-Wpacked				\
	-Wparentheses				\
	-Wpointer-arith				\
	-Wpointer-sign				\
	-Wredundant-decls			\
	-Wreturn-type				\
	-Wsequence-point			\
	-Wshadow				\
	-Wsign-compare				\
	-Wstack-protector			\
	-Wstrict-aliasing			\
	-Wstrict-aliasing=3			\
	-Wstrict-prototypes			\
	-Wswitch				\
	-Wswitch-default			\
	-Wswitch-enum				\
	-Wtrigraphs				\
	-Wundef					\
	-Wuninitialized				\
	-Wunknown-pragmas			\
	-Wunused-function			\
	-Wunused-label				\
	-Wunused-parameter			\
	-Wunused-value				\
	-Wunused-variable			\
	-Wvariadic-macros			\
	-Wwrite-strings				\
	-pedantic-errors

INCLUDES	=				\
		-I$(HDCTOOLS_DIR)/include	\
		-I$(HDCTOOLS_SOURCE_DIR)

ifeq ($(DEBUG),1)
  CDEBUG	= -DDEBUG
endif

ifeq ($(HDCTOOLS_OS_NAME),Darwin) # Mac
  LD_LIB = -dynamiclib
  LIB_EXT = dylib
  OS_CFLAGS += -DDARWIN
else
  ifeq ($(HDCTOOLS_OS_NAME),Linux)
    LD_LIB = -shared
    LIB_EXT = so
    OS_CFLAGS += -fPIC
  else
    $(error '$(HDCTOOLS_OS_NAME)' is not supported by the hdctools build.)
  endif
endif

CDEFINES	=				\
	-D_GNU_SOURCE=1

CFLAGS 	=					\
	-std=gnu99				\
	-MD					\
	$(CDEFINES)				\
	$(COPTIONS)				\
	$(INCLUDES)				\
	$(PTHREAD)				\
	$(CWARN)				\
	$(CGC)					\
	$(LDGC)					\
	$(CDEBUG)				\
	$(OS_CFLAGS)
