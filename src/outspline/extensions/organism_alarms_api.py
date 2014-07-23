# Outspline - A highly modular and extensible outliner.
# Copyright (C) 2011-2014 Dario Giovannetti <dev@dariogiovannetti.net>
#
# This file is part of Outspline.
#
# Outspline is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Outspline is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Outspline.  If not, see <http://www.gnu.org/licenses/>.

from organism_alarms import extension, alarmsmod


def get_supported_open_databases():
    return alarmsmod.cdbs


def get_number_of_active_alarms():
    return extension.get_number_of_active_alarms()


def snooze_alarms(alarmsd, stime):
    return extension.snooze_alarms(alarmsd, stime)


def dismiss_alarms(alarmsd):
    return alarmsmod.dismiss_alarms(alarmsd)


def get_alarms_log(filename):
    return alarmsmod.select_alarms_log(filename)


def get_alarms_log_limit(filename):
    return alarmsmod.log_limits[filename][0]


def update_alarms_log_limit(filename, limit):
    return alarmsmod.update_alarm_log_soft_limit(filename, limit)


def bind_to_alarm(handler, bind=True):
    # Warning, this function is executed on a separate thread!!!
    # (Check for race conditions)
    return alarmsmod.alarm_event.bind(handler, bind)


def bind_to_alarm_off(handler, bind=True):
    return alarmsmod.alarm_off_event.bind(handler, bind)
