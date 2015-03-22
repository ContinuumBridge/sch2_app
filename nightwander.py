#!/usr/bin/env python
# nightwander.py
# Copyright (C) ContinuumBridge Limited, 2014-2015 - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Peter Claydon
#

import time
from between_times import betweenTimes
from twisted.internet import reactor

class NightWander():
    def __init__(self, aid, config):
        self.config = config
        self.aid = aid
        self.lastActive = 0
        self.activatedSensors = []
        if self.config["client_test"] == 'True':
            reactor.callLater(30, self.clientTest)

    def clientTest(self):
        self.cbLog("debug", "clientTest")
        msg = {"m": "alarm",
               "s": "Test",
               "t": time.time()
              }
        self.client.send(msg)
        reactor.callLater(20, self.clientTest)

    def setNames(self, idToName):
        self.idToName = idToName
        if self.config["night_wandering"] == "True":
            if self.config["night_sensors"] == []:
                for d in idToName:
                    self.config["night_sensors"].append(d)
            else:
                for n in self.config["night_sensors"]:
                    found = False
                    for d in idToName:
                        self.cbLog("debug", "NightWander. Matching n: " + n + " with d: " + d + " , idToName[d]: " + idToName[d])
                        if n == idToName[d]:
                            loc = self.config["night_sensors"].index(n) 
                            self.config["night_sensors"][loc] = d
                            found = True
                            break
                    if not found:
                        self.cbLog("info", "NightWander. Sensor name does not exist: " + n)
            self.cbLog("debug", "NightWander. night sensors: " + str(self.config["night_sensors"]))

    def onChange(self, devID, timeStamp, value):
        self.cbLog("debug", "Night Wander onChange, devID: " + devID + " value: " + value)
        if value == "on":
            alarm = betweenTimes(timeStamp, self.config["night_start"], self.config["night_end"])
            if alarm:
                sensor = self.idToName[devID]
                if sensor not in self.activatedSensors:
                    self.activatedSensors.append(self.idToName[devID])
                if timeStamp - self.lastActive > self.config["night_ignore_time"]:
                    self.cbLog("debug", "Night Wander: " + str(alarm) + ": " + str(time.asctime(time.localtime(timeStamp))) + \
                    " sensors: " + str(self.activatedSensors))
                    msg = {"m": "alarm",
                           "s": str(", ".join(self.activatedSensors)),
                           "t": timeStamp
                          }
                    self.client.send(msg)
                    self.dm.storeActivity("Night_Wander", timeStamp, self.idToName[devID], 1)
                    self.lastActive = timeStamp
                    self.activatedSensors = []

