# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Definitions which control the C compiler on Mac OS.
#
# Please keep this file sorted to facilitate comparisons against other
# operating systems.

HOSTOS_CWARN	=				\
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

HOSTOS_LD_LIB	= -dynamiclib
HOSTOS_LIB_EXT	= dylib
HOSTOS_CFLAGS	= -DDARWIN

