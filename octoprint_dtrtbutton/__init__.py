# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import time
#import threading
#import subprocess

class DTRTButtonPlugin(octoprint.plugin.StartupPlugin,
                       octoprint.plugin.TemplatePlugin,
                       octoprint.plugin.EventHandlerPlugin,
                       octoprint.plugin.SettingsPlugin):

    def __init__(self):
        global GPIO
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BOARD)
        self.btnpin = 0 # type: int
        self.ledpin = 0 # type: int
        self.btnActive = True
        self.heatTemp = 0
        self.psuControl = ""

    def _set_led(self, event):
        from octoprint.events import Events

        if event == Events.SETTINGS_UPDATED:
            self._logger.info("DTRT Settings Changed")
            if self.ledpin < 1 or self.ledpin > 41:
                return

            try:
                GPIO.setup(self.ledpin, GPIO.OUT)
            except (RuntimeError, ValueError) as e:
                self._logger.error(e)

        elif event == Events.CONNECTED:
            self._logger.info("DTRT LED turned on pin %s" % self.ledpin)
            GPIO.output(self.ledpin, GPIO.HIGH)

        elif event == Events.DISCONNECTED or event == Events.ERROR:
            self._logger.info("DTRT LED turned off pin %s" % self.ledpin)
            GPIO.output(self.ledpin, GPIO.LOW)

        elif event == Events.PRINT_CANCELLED:
            self._logger.info("DTRT LED blink pin %s" % self.ledpin)
            for x in range(3):
                GPIO.output(self.ledpin, GPIO.LOW)
                time.sleep(0.1)
                GPIO.output(self.ledpin, GPIO.HIGH)
                time.sleep(0.1)

        elif event == Events.SHUTDOWN:
            GPIO.output(self.ledpin, GPIO.LOW)
            GPIO.cleanup([self.ledpin, self.btnpin])

    def on_event(self, event, payload):
         self._set_led(event)
        
    def _handle_btn(self, channel):
         import requests
         self._logger.info("DTRT button pressed.")
         data = {'command':'getPSUState'}
         r = requests.post(self.psuControl, json=data)
         if "false" in r.text:
             self._logger.info("Turning PSU on")
             data = {'command':'turnPSUOn'}
             r = requests.post(self.psuControl, json=data)
         elif self._printer.is_printing():
             self._logger.info("Cancelling print")
             self._printer.cancel_print()
             time.sleep(2)
             self._printer.commands("G1 Z10")
         elif self._printer.is_ready():
#             TODO Set a timer to turn off after 15 minutes
             self._logger.info("Preheating printer to %s" % self.heatTemp)
             self._printer.set_temperature("tool0", self.heatTemp)

    def _watch_btnpin(self):
        if self.btnpin < 0 or self.btnpin > 41:
            self._logger.info("DTRT set to invalid pin %s" % self.btnpin)
            return
        try:
            GPIO.setup(self.btnpin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            self._logger.info("DTRT button interrupt set to pin %s" % self.btnpin)
            GPIO.add_event_detect(self.btnpin, GPIO.RISING, callback=self._handle_btn, bouncetime=2000)

        except (RuntimeError, ValueError) as e:
            self._logger.error(e)

    def on_after_startup(self):
        self.btnpin = int(self._settings.get(["btnpin"]))
        self.ledpin = int(self._settings.get(["ledpin"]))
        self._set_led("SettingsUpdated")
        self._watch_btnpin()

    def get_settings_defaults(self):
        return dict(
            btnpin = 0,
            ledpin = 0,
            heatTemp = 200,
            psuControl = "http://localhost:5000/api/plugin/psucontrol",
        )

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False)
        ]

__plugin_name__ = "DTRT Button"
__plugin_implementation__ = DTRTButtonPlugin()
