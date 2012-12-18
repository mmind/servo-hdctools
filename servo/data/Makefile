# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk

SUBDIRS		=
SUBDIRS_INSTALL	=
XML_SRC		= $(notdir $(wildcard $(HDCTOOLS_SOURCE_DIR)/*.xml))
XML_DST		= $(addprefix $(THIS_BUILD_DIR)/,$(XML_SRC))
INAS		= wario.xml waluigi.xml servo_loc.xml link.xml snow.xml \
		  daisy.xml spring.xml

# TODO(tbroch) should probably be added to setup.py if possible
all:	$(INAS) $(XML_DST)

$(THIS_BUILD_DIR)/%.xml: $(HDCTOOLS_SOURCE_DIR)/%.xml
	$(MESSAGE) "Copying $(notdir $@)"
	$(CP) $< $@

$(INAS): %.xml:%.py
	$(MESSAGE) "Building $@"
	python -B "$(HDCTOOLS_SOURCE_DIR)/ina219.py" $(basename $(<F))

install:			# NOP
