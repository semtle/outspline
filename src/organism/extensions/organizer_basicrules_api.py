# Organism - A highly modular and extensible outliner.
# Copyright (C) 2011-2013 Dario Giovannetti <dev@dariogiovannetti.net>
#
# This file is part of Organism.
#
# Organism is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Organism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Organism.  If not, see <http://www.gnu.org/licenses/>.

from organizer_basicrules import except_once, occur_every_day, occur_once
from organizer_basicrules.exceptions import BadRuleError


def make_except_once_rule(start, end, inclusive):
    return except_once.make_rule(start, end, inclusive)


def make_occur_every_day_rule(rstart, rendn, rendu, ralarm):
    return occur_every_day.make_rule(rstart, rendn, rendu, ralarm)


def make_occur_once_rule(start, end, ralarm):
    return occur_once.make_rule(start, end, ralarm)
