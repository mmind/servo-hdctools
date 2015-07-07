# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk

SUBDIRS		=
SUBDIRS_INSTALL	=
XML_SRC		= $(notdir $(wildcard $(HDCTOOLS_SOURCE_DIR)/*.xml))
XML_DST		= $(addprefix $(THIS_BUILD_DIR)/,$(XML_SRC))
INA219		= wario.xml waluigi.xml servo_loc.xml link_dvt.xml link.xml    \
		  snow.xml daisy.xml mccroskey.xml spring_v0_r0.xml spring.xml \
		  pi.xml pit.xml falco.xml peppy.xml rambi.xml nyan.xml \
		  samus_p1.xml rambi_1v5_r0_loc.xml rambi_2v0_r0_loc.xml \
		  skate.xml big.xml whale_samus_larvae.xml storm.xml \
		  veyron_p0.xml veyron_p1.xml veyron_r2.xml samus_evt_v1.xml \
		  strago_proto.xml veyron_danger_p1.xml ryu_p0_loc.xml oak.xml \
		  veyron_brain_p1.xml ryu_p5_loc.xml ryu_evt2_loc.xml
INA231		= samus.xml whale_samus_dut.xml
INA3221		= glados_p1_inas.xml

# TODO(tbroch) should probably be added to setup.py if possible
all:	$(INA3221) $(INA231) $(INA219) $(XML_DST)

$(THIS_BUILD_DIR)/%.xml: $(HDCTOOLS_SOURCE_DIR)/%.xml
	$(MESSAGE) "Copying $(notdir $@)"
	$(CP) $< $@

$(INA219): %.xml:%.py
	$(MESSAGE) "Building $@"
	python2 -B "$(HDCTOOLS_SOURCE_DIR)/generate_ina_controls.py" \
		$(basename $(<F)) ina219

$(INA231): %.xml:%.py
	$(MESSAGE) "Building $@"
	python2 -B "$(HDCTOOLS_SOURCE_DIR)/generate_ina_controls.py" \
		$(basename $(<F)) ina231

$(INA3221): %.xml:%.py
	$(MESSAGE) "Building $@"
	python2 -B "$(HDCTOOLS_SOURCE_DIR)/generate_ina_controls.py" \
		$(basename $(<F)) ina3221

install:			# NOP
