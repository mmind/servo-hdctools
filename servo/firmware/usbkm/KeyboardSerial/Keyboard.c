// Copyright 2016 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

/*
             LUFA Library
     Copyright (C) Dean Camera, 2014.

  dean [at] fourwalledcubicle [dot] com
           www.lufa-lib.org
*/

/*
  Copyright 2014  Dean Camera (dean [at] fourwalledcubicle [dot] com)
  Copyright 2010  Denver Gingerich (denver [at] ossguy [dot] com)

  Permission to use, copy, modify, distribute, and sell this
  software and its documentation for any purpose is hereby granted
  without fee, provided that the above copyright notice appear in
  all copies and that both that the copyright notice and this
  permission notice and warranty disclaimer appear in supporting
  documentation, and that the name of the author not be used in
  advertising or publicity pertaining to distribution of the
  software without specific, written prior permission.

  The author disclaims all warranties with regard to this
  software, including all implied warranties of merchantability
  and fitness.  In no event shall the author be liable for any
  special, indirect or consequential damages or any damages
  whatsoever resulting from loss of use, data or profits, whether
  in an action of contract, negligence or other tortious action,
  arising out of or in connection with the use or performance of
  this software.
*/

/** \file
 *
 *  Main source file for the Keyboard Serial interface. This file contains the main tasks and
 *  is responsible for the initial application hardware configuration.
 */

#include "Keyboard.h"

/** Indicates what report mode the host has requested, true for normal HID reporting mode, \c false for special boot
 *  protocol reporting mode.
 */
static bool UsingReportProtocol = true;

/** Current Idle period. This is set by the host via a Set Idle HID class request to silence the device's reports
 *  for either the entire idle duration, or until the report status changes (e.g. the user presses a key).
 */
static uint16_t IdleCount = 500;

/** Current Idle period remaining. When the IdleCount value is set, this tracks the remaining number of idle
 *  milliseconds. This is separate to the IdleCount timer and is incremented and compared as the host may request
 *  the current idle period via a Get Idle HID class request, thus its value must be preserved.
 */
static uint16_t IdleMSRemaining = 0;


/** Circular buffer to hold data from the host before it is sent to the device via the serial port. */
static RingBuffer_t USBtoUSART_Buffer;

/** Underlying data buffer for \ref USBtoUSART_Buffer, where the stored bytes are located. */
static uint8_t      USBtoUSART_Buffer_Data[128];

/** Circular buffer to hold data from the serial port before it is sent to the host. */
static RingBuffer_t USARTtoUSB_Buffer;

/** Underlying data buffer for \ref USARTtoUSB_Buffer, where the stored bytes are located. */
static uint8_t      USARTtoUSB_Buffer_Data[128];

/** Mapping between USB-KM232 serial value and USB KB keycode. */
static uint8_t      KEYS[] = {
        0, // nothing
        HID_KEYBOARD_SC_NON_US_HASHMARK_AND_TILDE, //'`': 1,
        HID_KEYBOARD_SC_1_AND_EXCLAMATION, //'1': 2,
        HID_KEYBOARD_SC_2_AND_AT, //'2': 3,
        HID_KEYBOARD_SC_3_AND_HASHMARK, //'3': 4,
        HID_KEYBOARD_SC_4_AND_DOLLAR, //'4': 5,
        HID_KEYBOARD_SC_5_AND_PERCENTAGE, //'5': 6,
        HID_KEYBOARD_SC_6_AND_CARET, //'6': 7,
        HID_KEYBOARD_SC_7_AND_AMPERSAND, //'7': 8,
        HID_KEYBOARD_SC_8_AND_ASTERISK, //'8': 9,
        HID_KEYBOARD_SC_9_AND_OPENING_PARENTHESIS, //'9': 10,
        HID_KEYBOARD_SC_0_AND_CLOSING_PARENTHESIS, //'0': 11,
        HID_KEYBOARD_SC_MINUS_AND_UNDERSCORE, //'-': 12,
        HID_KEYBOARD_SC_EQUAL_AND_PLUS, //'=': 13,
        0, //'<undef1>': 14,
        HID_KEYBOARD_SC_BACKSPACE, //'<backspace>': 15,
        HID_KEYBOARD_SC_TAB, //'<tab>': 16,
        HID_KEYBOARD_SC_Q, //'q': 17,
        HID_KEYBOARD_SC_W, //'w': 18,
        HID_KEYBOARD_SC_E, //'e': 19,
        HID_KEYBOARD_SC_R, //'r': 20,
        HID_KEYBOARD_SC_T, //'t': 21,
        HID_KEYBOARD_SC_Y, //'y': 22,
        HID_KEYBOARD_SC_U, //'u': 23,
        HID_KEYBOARD_SC_I, //'i': 24,
        HID_KEYBOARD_SC_O, //'o': 25,
        HID_KEYBOARD_SC_P, //'p': 26,
        HID_KEYBOARD_SC_OPENING_BRACKET_AND_OPENING_BRACE, //'[': 27,
        HID_KEYBOARD_SC_CLOSING_BRACKET_AND_CLOSING_BRACE, //']': 28,
        HID_KEYBOARD_SC_BACKSLASH_AND_PIPE, //'\\': 29,
        HID_KEYBOARD_SC_CAPS_LOCK, //'<capslock>': 30,
        HID_KEYBOARD_SC_A, //'a': 31,
        HID_KEYBOARD_SC_S, //'s': 32,
        HID_KEYBOARD_SC_D, //'d': 33,
        HID_KEYBOARD_SC_F, //'f': 34,
        HID_KEYBOARD_SC_G, //'g': 35,
        HID_KEYBOARD_SC_H, //'h': 36,
        HID_KEYBOARD_SC_J, //'j': 37,
        HID_KEYBOARD_SC_K, //'k': 38,
        HID_KEYBOARD_SC_L, //'l': 39,
        HID_KEYBOARD_SC_SEMICOLON_AND_COLON, //';': 40,
        HID_KEYBOARD_SC_APOSTROPHE_AND_QUOTE, //'\'': 41,
        0, //'<undef2>': 42,
        HID_KEYBOARD_SC_ENTER, //'<enter>': 43,
        HID_KEYBOARD_SC_LEFT_SHIFT, //'<lshift>': 44,
        0, //'<undef3>': 45,
        HID_KEYBOARD_SC_Z, //'z': 46,
        HID_KEYBOARD_SC_X, //'x': 47,
        HID_KEYBOARD_SC_C, //'c': 48,
        HID_KEYBOARD_SC_V, //'v': 49,
        HID_KEYBOARD_SC_B, //'b': 50,
        HID_KEYBOARD_SC_N, //'n': 51,
        HID_KEYBOARD_SC_M, //'m': 52,
        HID_KEYBOARD_SC_COMMA_AND_LESS_THAN_SIGN, //',': 53,
        HID_KEYBOARD_SC_DOT_AND_GREATER_THAN_SIGN, //'.': 54,
        HID_KEYBOARD_SC_SLASH_AND_QUESTION_MARK, //'/': 55,
        HID_KEYBOARD_SC_CLEAR, //'[clear]': 56,
        HID_KEYBOARD_SC_RIGHT_SHIFT, //'<rshift>': 57,
        HID_KEYBOARD_SC_LEFT_CONTROL, //'<lctrl>': 58,
        0, //'<undef5>': 59,
        HID_KEYBOARD_SC_LEFT_ALT, //'<lalt>': 60,
        HID_KEYBOARD_SC_SPACE, //' ': 61,
        HID_KEYBOARD_SC_RIGHT_ALT, //'<ralt>': 62,
        0, //'<undef6>': 63,
        HID_KEYBOARD_SC_RIGHT_CONTROL, //'<rctrl>': 64,
        0, //'<undef7>': 65,
        0, //'<mouse_left>': 66,
        0, //'<mouse_right>': 67,
        0, //'<mouse_up>': 68,
        0, //'<mouse_down>': 69,
        0, //'<lwin>': 70,
        0, //'<rwin>': 71,
        0, //'<win apl>': 72,
        0, //'<mouse_lbtn_press>': 73,
        0, //'<mouse_rbtn_press>': 74,
        HID_KEYBOARD_SC_INSERT, //'<insert>': 75,
        HID_KEYBOARD_SC_DELETE, //'<delete>': 76,
        0, //'<mouse_mbtn_press>': 77,
        0, //'<undef16>': 78,
        HID_KEYBOARD_SC_LEFT_ARROW, //'<larrow>': 79,
        HID_KEYBOARD_SC_HOME, //'<home>': 80,
        HID_KEYBOARD_SC_END, //'<end>': 81,
        0, //'<undef23>': 82,
        HID_KEYBOARD_SC_UP_ARROW, //'<uparrow>': 83,
        HID_KEYBOARD_SC_DOWN_ARROW, //'<downarrow>': 84,
        HID_KEYBOARD_SC_PAGE_UP, //'<pgup>': 85,
        HID_KEYBOARD_SC_PAGE_DOWN, //'<pgdown>': 86,
        0, //'<mouse_scr_up>': 87,
        0, //'<mouse_scr_down>': 88,
        HID_KEYBOARD_SC_RIGHT_ARROW, //'<rarrow>': 89,
        HID_KEYBOARD_SC_NUM_LOCK, //'<numlock>': 90,
        HID_KEYBOARD_SC_KEYPAD_7_AND_HOME, //'<num7>': 91,
        HID_KEYBOARD_SC_KEYPAD_4_AND_LEFT_ARROW, //'<num4>': 92,
        HID_KEYBOARD_SC_KEYPAD_1_AND_END, //'<num1>': 93,
        0, //'<undef27>': 94,
        HID_KEYBOARD_SC_KEYPAD_SLASH, //'<num/>': 95,
        HID_KEYBOARD_SC_KEYPAD_8_AND_UP_ARROW, //'<num8>': 96,
        HID_KEYBOARD_SC_KEYPAD_5, //'<num5>': 97,
        HID_KEYBOARD_SC_KEYPAD_2_AND_DOWN_ARROW, //'<num2>': 98,
        HID_KEYBOARD_SC_KEYPAD_0_AND_INSERT, //'<num0>': 99,
        HID_KEYBOARD_SC_KEYPAD_ASTERISK, //'<num*>': 100,
        HID_KEYBOARD_SC_KEYPAD_9_AND_PAGE_UP, //'<num9>': 101,
        HID_KEYBOARD_SC_KEYPAD_6_AND_RIGHT_ARROW, //'<num6>': 102,
        HID_KEYBOARD_SC_KEYPAD_3_AND_PAGE_DOWN, //'<num3>': 103,
        HID_KEYBOARD_SC_KEYPAD_DOT_AND_DELETE, //'<num.>': 104,
        HID_KEYBOARD_SC_KEYPAD_MINUS, //'<num->': 105,
        HID_KEYBOARD_SC_KEYPAD_PLUS, //'<num+>': 106,
        HID_KEYBOARD_SC_KEYPAD_ENTER, //'<numenter>': 107,
        0, //'<undef28>': 108,
        0, //'<mouse_slow>': 109,
        HID_KEYBOARD_SC_ESCAPE, //'<esc>': 110,
        0, //'<mouse_fast>': 111,
        HID_KEYBOARD_SC_F1, //'<f1>': 112,
        HID_KEYBOARD_SC_F2, //'<f2>': 113,
        HID_KEYBOARD_SC_F3, //'<f3>': 114,
        HID_KEYBOARD_SC_F4, //'<f4>': 115,
        HID_KEYBOARD_SC_F5, //'<f5>': 116,
        HID_KEYBOARD_SC_F6, //'<f6>': 117,
        HID_KEYBOARD_SC_F7, //'<f7>': 118,
        HID_KEYBOARD_SC_F8, //'<f8>': 119,
        HID_KEYBOARD_SC_F9, //'<f9>': 120,
        HID_KEYBOARD_SC_F10, //'<f10>': 121,
        HID_KEYBOARD_SC_F11, //'<f11>': 122,
        HID_KEYBOARD_SC_F12, //'<f12>': 123,
        HID_KEYBOARD_SC_PRINT_SCREEN, //'<prtscr>': 124,
        HID_KEYBOARD_SC_SCROLL_LOCK, //'<scrllk>': 125,
        HID_KEYBOARD_SC_PAUSE, //'<pause/brk>': 126,
        };


/** Current scancode tracking for 6 active keys. */
#define KEYCOUNT 6
uint8_t pressed[KEYCOUNT];

void keyclear() {
	for (int i = 0; i < KEYCOUNT; i++)
		pressed[i] = 0;
}

int iskeypressed(uint8_t key) {
	for (int i = 0; i < KEYCOUNT; i++) {
		if (pressed[i] == key)
			return 1;
	}
	return 0;
}

int insertkey(uint8_t key) {
	for (int i = 0; i < KEYCOUNT; i++) {
		if (pressed[i] == key)
			return 1;
		if (pressed[i] == 0) {
			pressed[i] = key;
			return 1;
		}
	}
	pressed[0] = key;
	return 1;
}

int removekey(uint8_t key) {
	for (int i = 0; i < KEYCOUNT; i++) {
		if (pressed[i] == key) {
			pressed[i] = 0;
			return 1;
		}
	}
	return 0;
}


/** Main program entry point. This routine configures the hardware required by the application, then
 *  enters a loop to run the application tasks in sequence.
 */
int main(void)
{
	SetupHardware();


        RingBuffer_InitBuffer(&USBtoUSART_Buffer, USBtoUSART_Buffer_Data, sizeof(USBtoUSART_Buffer_Data));
        RingBuffer_InitBuffer(&USARTtoUSB_Buffer, USARTtoUSB_Buffer_Data, sizeof(USARTtoUSB_Buffer_Data));

	GlobalInterruptEnable();

	for (;;)
	{
                /* Load the next byte from the USART transmit buffer into the USART */
                /*  if transmit buffer space is available */
                if (Serial_IsSendReady() && !(RingBuffer_IsEmpty(&USBtoUSART_Buffer)))
                {
                  Serial_SendByte(RingBuffer_Remove(&USBtoUSART_Buffer));
                }


		HID_Task();
		USB_USBTask();
	}
}

/** Configures the board hardware and chip peripherals for the demo's functionality. */
void SetupHardware(void)
{
#if (ARCH == ARCH_AVR8)
	/* Disable watchdog if enabled by bootloader/fuses */
	MCUSR &= ~(1 << WDRF);
	wdt_disable();

	/* Disable clock division */
	clock_prescale_set(clock_div_1);
#elif (ARCH == ARCH_XMEGA)
	/* Start the PLL to multiply the 2MHz RC oscillator to 32MHz and switch the CPU core to run from it */
	XMEGACLK_StartPLL(CLOCK_SRC_INT_RC2MHZ, 2000000, F_CPU);
	XMEGACLK_SetCPUClockSource(CLOCK_SRC_PLL);

	/* Start the 32MHz internal RC oscillator and start the DFLL to increase it to 48MHz using the USB SOF as a reference */
	XMEGACLK_StartInternalOscillator(CLOCK_SRC_INT_RC32MHZ);
	XMEGACLK_StartDFLL(CLOCK_SRC_INT_RC32MHZ, DFLL_REF_INT_USBSOF, F_USB);

	PMIC.CTRL = PMIC_LOLVLEN_bm | PMIC_MEDLVLEN_bm | PMIC_HILVLEN_bm;
#endif

	/* Hardware Initialization */
        keyclear();
	USB_Init();
        SetupSerial();
}

/** Event handler for the USB_Connect event. This indicates that the device is enumerating via the status LEDs and
 *  starts the library USB task to begin the enumeration and USB management process.
 */
void EVENT_USB_Device_Connect(void)
{
	/* Default to report protocol on connect */
	UsingReportProtocol = true;
}

/** Event handler for the USB_Disconnect event. This indicates that the device is no longer connected to a host via
 *  the status LEDs.
 */
void EVENT_USB_Device_Disconnect(void)
{
	/* Indicate USB not ready */
	/* No LEDs on servo. */
}

/** Event handler for the USB_ConfigurationChanged event. This is fired when the host sets the current configuration
 *  of the USB device after enumeration, and configures the keyboard device endpoints.
 */
void EVENT_USB_Device_ConfigurationChanged(void)
{
	bool ConfigSuccess = true;

	/* Setup HID Report Endpoints */
	ConfigSuccess &= Endpoint_ConfigureEndpoint(KEYBOARD_IN_EPADDR, EP_TYPE_INTERRUPT, KEYBOARD_EPSIZE, 1);
	ConfigSuccess &= Endpoint_ConfigureEndpoint(KEYBOARD_OUT_EPADDR, EP_TYPE_INTERRUPT, KEYBOARD_EPSIZE, 1);

	/* Turn on Start-of-Frame events for tracking HID report period expiry */
	USB_Device_EnableSOFEvents();

	/* Indicate endpoint configuration success or failure */
	//LEDs_SetAllLEDs(ConfigSuccess ? LEDMASK_USB_READY : LEDMASK_USB_ERROR);
}

/** Event handler for the USB_ControlRequest event. This is used to catch and process control requests sent to
 *  the device from the USB host before passing along unhandled control requests to the library for processing
 *  internally.
 */
void EVENT_USB_Device_ControlRequest(void)
{
	/* Handle HID Class specific requests */
	switch (USB_ControlRequest.bRequest)
	{
		case HID_REQ_GetReport:
			if (USB_ControlRequest.bmRequestType == (REQDIR_DEVICETOHOST | REQTYPE_CLASS | REQREC_INTERFACE))
			{
				USB_KeyboardReport_Data_t KeyboardReportData;

				/* Create the next keyboard report for transmission to the host */
				CreateKeyboardReport(&KeyboardReportData);

				Endpoint_ClearSETUP();

				/* Write the report data to the control endpoint */
				Endpoint_Write_Control_Stream_LE(&KeyboardReportData, sizeof(KeyboardReportData));
				Endpoint_ClearOUT();
			}

			break;
		case HID_REQ_SetReport:
			if (USB_ControlRequest.bmRequestType == (REQDIR_HOSTTODEVICE | REQTYPE_CLASS | REQREC_INTERFACE))
			{
				Endpoint_ClearSETUP();

				/* Wait until the LED report has been sent by the host */
				while (!(Endpoint_IsOUTReceived()))
				{
					if (USB_DeviceState == DEVICE_STATE_Unattached)
					  return;
				}

				/* Read in the LED report from the host */
				uint8_t LEDStatus = Endpoint_Read_8();

				Endpoint_ClearOUT();
				Endpoint_ClearStatusStage();

				/* Process the incoming LED report */
				ProcessLEDReport(LEDStatus);
			}

			break;
		case HID_REQ_GetProtocol:
			if (USB_ControlRequest.bmRequestType == (REQDIR_DEVICETOHOST | REQTYPE_CLASS | REQREC_INTERFACE))
			{
				Endpoint_ClearSETUP();

				/* Write the current protocol flag to the host */
				Endpoint_Write_8(UsingReportProtocol);

				Endpoint_ClearIN();
				Endpoint_ClearStatusStage();
			}

			break;
		case HID_REQ_SetProtocol:
			if (USB_ControlRequest.bmRequestType == (REQDIR_HOSTTODEVICE | REQTYPE_CLASS | REQREC_INTERFACE))
			{
				Endpoint_ClearSETUP();
				Endpoint_ClearStatusStage();

				/* Set or clear the flag depending on what the host indicates that the current Protocol should be */
				UsingReportProtocol = (USB_ControlRequest.wValue != 0);
			}

			break;
		case HID_REQ_SetIdle:
			if (USB_ControlRequest.bmRequestType == (REQDIR_HOSTTODEVICE | REQTYPE_CLASS | REQREC_INTERFACE))
			{
				Endpoint_ClearSETUP();
				Endpoint_ClearStatusStage();

				/* Get idle period in MSB, IdleCount must be multiplied by 4 to get number of milliseconds */
				IdleCount = ((USB_ControlRequest.wValue & 0xFF00) >> 6);
			}

			break;
		case HID_REQ_GetIdle:
			if (USB_ControlRequest.bmRequestType == (REQDIR_DEVICETOHOST | REQTYPE_CLASS | REQREC_INTERFACE))
			{
				Endpoint_ClearSETUP();

				/* Write the current idle duration to the host, must be divided by 4 before sent to host */
				Endpoint_Write_8(IdleCount >> 2);

				Endpoint_ClearIN();
				Endpoint_ClearStatusStage();
			}

			break;
	}
}

/** Event handler for the USB device Start Of Frame event. */
void EVENT_USB_Device_StartOfFrame(void)
{
	/* One millisecond has elapsed, decrement the idle time remaining counter if it has not already elapsed */
	if (IdleMSRemaining)
	  IdleMSRemaining--;
}

/** Fills the given HID report data structure with the next HID report to send to the host.
 *
 *  \param[out] ReportData  Pointer to a HID report data structure to be filled
 */
void CreateKeyboardReport(USB_KeyboardReport_Data_t* const ReportData)
{
	uint8_t UsedKeyCodes      = 0;

	/* Clear the report contents */
	memset(ReportData, 0, sizeof(USB_KeyboardReport_Data_t));

	uint16_t BufferCount = RingBuffer_GetCount(&USARTtoUSB_Buffer);
	if (BufferCount)
	{
		uint8_t ReceivedByte = RingBuffer_Remove(&USARTtoUSB_Buffer);
		uint16_t size = sizeof(KEYS)/sizeof(KEYS[0]);

		// Echo the result back when the thing is written.
		RingBuffer_Insert(&USBtoUSART_Buffer, ~(ReceivedByte));

		 // High bit indicates press/release.
		 if (ReceivedByte & 0x80) {
		   removekey(ReceivedByte & 0x7f);
		 } else {
		   if (ReceivedByte < size) {
		     if (KEYS[ReceivedByte] == HID_KEYBOARD_SC_CLEAR) {
		       keyclear();
		     } else if (ReceivedByte != 0) {
		       insertkey(ReceivedByte);
		     }
		   }
		 }
	}

	for (int i = 0; i < KEYCOUNT; i++) {
		if (pressed[i] != 0) {
			ReportData->KeyCode[UsedKeyCodes++] = KEYS[pressed[i]];
		}

		if (KEYS[pressed[i]] == HID_KEYBOARD_SC_LEFT_SHIFT)
			ReportData->Modifier |= HID_KEYBOARD_MODIFIER_LEFTSHIFT;
		if (KEYS[pressed[i]] == HID_KEYBOARD_SC_RIGHT_SHIFT)
			ReportData->Modifier |= HID_KEYBOARD_MODIFIER_RIGHTSHIFT;
		if (KEYS[pressed[i]] == HID_KEYBOARD_SC_LEFT_CONTROL)
			ReportData->Modifier |= HID_KEYBOARD_MODIFIER_LEFTCTRL;
		if (KEYS[pressed[i]] ==  HID_KEYBOARD_SC_RIGHT_CONTROL)
			ReportData->Modifier |= HID_KEYBOARD_MODIFIER_RIGHTCTRL;
		if (KEYS[pressed[i]] == HID_KEYBOARD_SC_LEFT_ALT)
			ReportData->Modifier |= HID_KEYBOARD_MODIFIER_LEFTALT;
		if (KEYS[pressed[i]] == HID_KEYBOARD_SC_RIGHT_ALT)
			ReportData->Modifier |= HID_KEYBOARD_MODIFIER_RIGHTALT;
		if (KEYS[pressed[i]] == HID_KEYBOARD_SC_LEFT_GUI)
			ReportData->Modifier |= HID_KEYBOARD_MODIFIER_LEFTGUI;
		if (KEYS[pressed[i]] == HID_KEYBOARD_SC_RIGHT_GUI)
			ReportData->Modifier |= HID_KEYBOARD_MODIFIER_RIGHTGUI;
	}
}

/** Processes a received LED report, and updates the board LEDs states to match.
 *
 *  \param[in] LEDReport  LED status report from the host
 */
void ProcessLEDReport(const uint8_t LEDReport)
{
	/* We don't have LEDs so we ddon't care. */
}

/** Sends the next HID report to the host, via the keyboard data endpoint. */
void SendNextReport(void)
{
	static USB_KeyboardReport_Data_t PrevKeyboardReportData;
	USB_KeyboardReport_Data_t	KeyboardReportData;
	bool                             SendReport = false;

	/* Create the next keyboard report for transmission to the host */
	CreateKeyboardReport(&KeyboardReportData);

	/* Check if the idle period is set and has elapsed */
	if (IdleCount && (!(IdleMSRemaining)))
	{
		/* Reset the idle time remaining counter */
		IdleMSRemaining = IdleCount;

		/* Idle period is set and has elapsed, must send a report to the host */
		SendReport = true;
	}
	else
	{
		/* Check to see if the report data has changed - if so a report MUST be sent */
		SendReport = (memcmp(&PrevKeyboardReportData, &KeyboardReportData, sizeof(USB_KeyboardReport_Data_t)) != 0);
	}

	/* Select the Keyboard Report Endpoint */
	Endpoint_SelectEndpoint(KEYBOARD_IN_EPADDR);

	/* Check if Keyboard Endpoint Ready for Read/Write and if we should send a new report */
	if (Endpoint_IsReadWriteAllowed() && SendReport)
	{
		/* Save the current report data for later comparison to check for changes */
		PrevKeyboardReportData = KeyboardReportData;

		/* Write Keyboard Report Data */
		Endpoint_Write_Stream_LE(&KeyboardReportData, sizeof(KeyboardReportData), NULL);

		/* Finalize the stream transfer to send the last packet */
		Endpoint_ClearIN();
	}
}

/** Reads the next LED status report from the host from the LED data endpoint, if one has been sent. */
void ReceiveNextReport(void)
{
	/* Select the Keyboard LED Report Endpoint */
	Endpoint_SelectEndpoint(KEYBOARD_OUT_EPADDR);

	/* Check if Keyboard LED Endpoint contains a packet */
	if (Endpoint_IsOUTReceived())
	{
		/* Check to see if the packet contains data */
		if (Endpoint_IsReadWriteAllowed())
		{
			/* Read in the LED report from the host */
			uint8_t LEDReport = Endpoint_Read_8();

			/* Process the read LED report from the host */
			ProcessLEDReport(LEDReport);
		}

		/* Handshake the OUT Endpoint - clear endpoint and ready for next report */
		Endpoint_ClearOUT();
	}
}

/** Function to manage HID report generation and transmission to the host, when in report mode. */
void HID_Task(void)
{
	/* Device must be connected and configured for the task to run */
	if (USB_DeviceState != DEVICE_STATE_Configured)
	  return;

	/* Send the next keypress report to the host */
	SendNextReport();

	/* Process the LED report sent from the host */
	ReceiveNextReport();
}


/** ISR to manage the reception of data from the serial port, placing received bytes into a circular buffer
 *  for later transmission to the host.
 */
ISR(USART1_RX_vect, ISR_BLOCK)
{
	uint8_t ReceivedByte = UDR1;

	if (ReceivedByte == 0) {
		/* Acknowledge presence regardless of USB state */
		RingBuffer_Insert(&USBtoUSART_Buffer, ~(ReceivedByte));
	} else if ((USB_DeviceState == DEVICE_STATE_Configured) &&
		   !(RingBuffer_IsFull(&USARTtoUSB_Buffer))) {
		RingBuffer_Insert(&USARTtoUSB_Buffer, ReceivedByte);
	}
}


void SetupSerial() {
	uint8_t ConfigMask = 0;
	uint32_t baud = 9600;

	/* Must turn off USART before reconfiguring it, otherwise incorrect operation may occur */
	UCSR1B = 0;
	UCSR1A = 0;
	UCSR1C = 0;
	PORTD |= (1 << 3);

	/* Set baud rate */
	UBRR1  = SERIAL_2X_UBBRVAL(baud);

	// No double speed, clear status.
	UCSR1A = (1 << U2X1);
	/* Enable interrupt, receiver and transmitter */
	UCSR1B = ((1<<RXCIE1)|(1<<TXEN1)|(1 << RXEN1));
	/* Set frame format: 8data, 1stop bit */
	UCSR1C = ((1 << UCSZ11) | (1 << UCSZ10));
	//UCSR1D = 0;

	/* Release the TX line after the USART has been reconfigured */
	PORTD &= ~(1 << 3);
}
