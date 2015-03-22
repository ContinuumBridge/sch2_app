#!/usr/bin/env python
# hotdrinks.py
# Copyright (C) ContinuumBridge Limited, 2014-2015 - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Peter Claydon
#
"""
Configured using:
    "config": {"name": "Not Set",     The name to write to the database when a hot drink is made
               "enable": "False",     Enabled - not used
               "sensor": "",          The friendly name of the sensor
               "threshold": 2         The power (or other characteristic) threshold above which the "kettle" is considered on
              }
"""

IGNORE_TIME = 60          # Don't flag making a again drink if appliance is turned on within IGNORE_TIME of being turned off
import time

class HotDrinks():
    def __init__(self):
        self.on = False
        self.offTime = 0

    def initIDs(self, idToName, config):
        try:
            self.name = config["name"]
            self.threshold = config["threshold"]
            for i in idToName:
                if idToName[i] == config["sensor"]:
                    self.cbLog("info", "HotDrinks, using sensor ID: " + i + ", " + config["sensor"])
                    return i
            self.cbLog("warning", "HotDrinks. Specified sensor name not known: " + sensor)
        except Exception as ex:
            self.cbLog("warning", "Problems initialising HotDrinks")
            self.cbLog("warning", "Exception: " + str(type(ex)) + str(ex.args))

    def onChange(self, timeStamp, value):
        try:
            if value > self.threshold and not self.on:
                if timeStamp - self.offTime > IGNORE_TIME:
                    self.on = True
                    self.cbLog("debug", "HotDrinks on")
                    self.dm.storeActivity("HotDrinks", timeStamp-1, self.name, 0)
                    self.dm.storeActivity("HotDrinks", timeStamp, self.name, 1)
            elif value < self.threshold and self.on:
                self.on = False
                self.offTime = timeStamp
                self.cbLog("debug", "HotDrinks off")
                self.dm.storeActivity("HotDrinks", timeStamp-1, self.name, 1)
                self.dm.storeActivity("HotDrinks", timeStamp, self.name, 0)
        except Exception as ex:
            self.cbLog("warning", "HotDrinks onChange encountered problems")
            self.cbLog("warning", "Exception: " + str(type(ex)) + str(ex.args))
