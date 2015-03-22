#!/usr/bin/env python
# entry-exit.py
# Copyright (C) ContinuumBridge Limited, 2014-2015 - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Peter Claydon
#

import time
from twisted.internet import reactor

# For entry/exit
IN_PIR_TO_DOOR_TIME               = 30   
DOOR_CLOSE_TO_IN_PIR_TIME         = 10
DOOR_OPEN_TO_IN_PIR_TIME          = 30
MAX_DOOR_OPEN_TIME                = 60

class EntryExit():
    def __init__(self):
        self.inside_triggered = False
        self.inside_pir_on = False
        self.door_open = False
        self.action = "nothing"
        self.locations = []
        self.checkExit = {}

    def initExits(self, idToName, enable, entry_exits):
        self.idToName = idToName
        devs = []
        try:
            if enable:
                for c in entry_exits:
                    ipir = False
                    magsw = False
                    loc = {}
                    loc["location"] = c["location"]
                    for d in idToName:
                        if idToName[d] == c["inside_activity"]:
                            loc["ipir"] = d
                            ipir = True
                        if idToName[d] == c["door"]:
                            loc["magsw"] = d
                            magsw = True
                    if ipir and magsw:
                        self.locations.append(loc)
                    else:
                        self.cbLog("warning", "entry-exit, location does not have known sensors: " + c["location"])
            self.cbLog("debug", "initExits, locations: " + str(self.locations))
            for l in self.locations:
                self.checkExit[l["location"]] = CheckExit(l["location"])
                self.checkExit[l["location"]].cbLog = self.cbLog
                self.checkExit[l["location"]].dm = self.dm
                devs.append(l["magsw"])
                devs.append(l["ipir"])
        except Exception as ex:
            self.cbLog("warning", "entry-exit initialisation failed, possibly due to corrupt sch2_app.config file")
            self.cbLog("warning", "Exception: " + str(type(ex)) + str(ex.args))
        return devs

    def onChange(self, devID, timeStamp, value):
        #self.cbLog("debug", "EntryExit onChange, devID: " + "devID")
        for l in self.locations:
            if devID == l["magsw"]:
                self.checkExit[l["location"]].onChange("magsw", timeStamp, value)
            elif devID == l["ipir"]:
                self.checkExit[l["location"]].onChange("ipir", timeStamp, value)

class CheckExit():
    def __init__(self, location):
        self.location = location
        self.inside_pir_on_time = 0
        self.inside_pir_off_time = 0
        self.inside_pir_on = False
        self.door_open = False
        self.door_open_time = 0
        self.door_close_time = 0
        self.state = "idle"
        reactor.callLater(10, self.fsm)

    def onChange(self, sensor, timeStamp, value):
        self.cbLog("debug", "CheckExit, onChange. loc: " + self.location + " sensor: " + sensor)
        if sensor == "ipir":
            if value == "on":
                self.inside_pir_on_time = timeStamp
                self.inside_pir_on = True
            else:
                self.inside_pir_off_time = timeStamp
                self.inside_pir_on = False
        if sensor == "magsw":
            if value == "on":
                self.door_open = True
                self.door_open_time = timeStamp
            else:
                self.door_open = False
                self.door_close_time = timeStamp
              
    def fsm(self):
        # This method is called every second
        prev_state = self.state
        action = "none"
        if self.state == "idle":
            if self.door_open:
                if self.door_open_time - self.inside_pir_on_time < IN_PIR_TO_DOOR_TIME or self.inside_pir_on:
                    self.state = "check_going_out"
                else:
                    self.state = "check_coming_in"
        elif self.state == "check_going_out":
            if not self.door_open:
                self.state = "check_went_out"
        elif self.state == "check_went_out":
            t = time.time()
            if t - self.door_close_time > DOOR_CLOSE_TO_IN_PIR_TIME:
                if self.inside_pir_on or t - self.inside_pir_off_time < DOOR_CLOSE_TO_IN_PIR_TIME - 4:
                    action = "answered_door"
                    self.state = "idle"
                else:
                    action = "went_out"
                    self.state = "idle"
        elif self.state == "check_coming_in":
            if self.inside_pir_on:
                action = "came_in"
                self.state = "wait_door_close"
            elif time.time() - self.door_open_time > DOOR_OPEN_TO_IN_PIR_TIME:
                action = "open_and_close"
                self.state = "wait_door_close"
        elif self.state == "wait_door_close":
            if not self.door_open:
                self.state = "idle"
            elif time.time() - self.door_open_time > MAX_DOOR_OPEN_TIME:
                action = "door_open_too_long"
                self.state = "wait_long_door_open"
        elif self.state == "wait_long_door_open":
            if not self.door_open:
                self.state = "idle"
        elif self.state == "wait_door_close":
            if not self.door_open:
                self.state = "idle"
        else:
            self.cbLog("warning", "self.door algorithm imposssible self.state")
            self.state = "idle"
        if self.state != prev_state:
            self.cbLog("debug", "checkExits, new state: " + self.state)
        if action != "none":
            self.cbLog("debug", "checkExits, action: " + action) 
            self.dm.storeActivity(self.location, self.door_open_time, action, 0)
            self.dm.storeActivity(self.location, self.door_open_time + 1, action, 1)
            self.dm.storeActivity(self.location, self.door_open_time + 2, action, 0)
        reactor.callLater(1, self.fsm)

