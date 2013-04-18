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

import os
import errno
import Queue as queue
import sqlite3 as _sql

import organism.coreaux_api as coreaux_api
from organism.coreaux_api import Event, log

import exceptions
import items
import queries
import history

protection = None
memory = None

create_database_event = Event()
open_database_event = Event()
close_database_event = Event()
save_database_copy_event = Event()
delete_items_event = Event()
exit_app_event_1 = Event()
exit_app_event_2 = Event()

dbs = {}


class Protection():
    # Avoid that an operation is started while the timer is doing something
    # In theory it could happen that, because the database connection is
    #   taken and released with .get() and .give() various times during an
    #   operation, if the timer does something in the meanwhile it could
    #   "steal" the connection to the ongoing operation, with unknown results
    # Make sure that all the commands that can be started either directly by
    #   the user (through interaction with interfaces and their plugins) or
    #   automatically (e.g. by a timer) are protected
    # Also be sure to protect the functions from start to end; for example
    #   it would be wrong, in a loop, to protect every iteration but leave out
    #   the for itself; this way, in fact, another function that was waiting
    #   for a .get() could steal the connection between a loop and the other
    # Pay attention to functions that have returns, because they could bypass
    #   the .release() and hang the program
    # Another advantage is that if an exception is raised, the program hangs
    #   at the following command issued, instead of possibly continuing
    #     operating
    # Another advantage is that this class makes sure that when a function sets
    #     the history group, it's impossible that another function manages to
    #     set the same group
    q = None
    s = None

    def __init__(self):
        baton = True
        self.q = queue.Queue()
        self.q.put(baton)

    def block(self):
        log.debug('Block databases')

        self.s = self.q.get()

    def release(self):
        log.debug('Release databases')

        self.q.task_done()
        self.q.join()
        self.q.put(self.s)


class DBQueue(queue.Queue):
    def give(self, item):
        self.task_done()
        self.join()
        self.put(item)
        return True


class MemoryDB(DBQueue):
    def __init__(self):
        DBQueue.__init__(self)

        # Enable multi-threading, as the database is protected with a queue
        self.put(_sql.connect(':memory:', check_same_thread=False))  # @UndefinedVariable

        qmemory = self.get()
        qmemory.row_factory = _sql.Row  # @UndefinedVariable
        self.give(qmemory)

    def exit_(self):
        exit_app_event_1.signal()

        qmemory = self.get()
        qmemory.close()
        self.task_done()
        self.join()

        exit_app_event_2.signal()


class Database(history.DBHistory):
    connection = None
    filename = None
    items = None

    def __init__(self, filename):
        self.connection = DBQueue()
        self.filename = filename
        self.items = {}

        conn = self.connection
        # Enable multi-threading, as the database is protected with a queue
        conn.put(_sql.connect(filename, check_same_thread=False))  # @UndefinedVariable
        qconn = conn.get()
        qconn.row_factory = _sql.Row  # @UndefinedVariable
        cursor = qconn.cursor()
        dbitems = cursor.execute(queries.items_select_tree)
        conn.give(qconn)

        for item in dbitems:
            self.items[item['I_id']] = items.Item(database=self,
                                                  filename=filename,
                                                  id_=item['I_id'])

    @staticmethod
    def create(filename):
        if filename in dbs:
            raise exceptions.DatabaseAlreadyOpenError()
        else:
            try:
                db = open(filename, 'w')
            except IOError as e:
                if e.errno in (errno.EACCES, errno.ENOENT):
                    # errno.ENOENT happens when trying to to do a save as in
                    # a non-authorized folder
                    raise exceptions.AccessDeniedError()
                raise
            else:
                db.close()

                conn = _sql.connect(filename)  # @UndefinedVariable
                cursor = conn.cursor()

                cursor.execute(queries.properties_create)
                cursor.execute(queries.properties_insert_init,
                               (coreaux_api.get_default_history_limit(), ))

                cursor.execute(queries.compatibility_create)
                cursor.execute(queries.compatibility_insert, ('Core', 'core',
                                             coreaux_api.get_core_version(), ))

                info = coreaux_api.get_addons_info(disabled=False)

                for ext in info('Extensions').get_sections():
                    cursor.execute(queries.compatibility_insert, ('Extension',
                                      ext, info('Extensions')(ext)['version']))
                for ui in info('Interfaces').get_sections():
                    cursor.execute(queries.compatibility_insert, ('Interface',
                                        ui, info('Interfaces')(ui)['version']))
                for plg in info('Plugins').get_sections():
                    cursor.execute(queries.compatibility_insert, ('Plugin',
                                         plg, info('Plugins')(plg)['version']))

                cursor.execute(queries.items_create)

                cursor.execute(queries.history_create)

                conn.commit()
                conn.close()

                create_database_event.signal(filename=filename)

                return filename

    @classmethod
    def open(cls, filename):
        global dbs
        if filename in dbs:
            raise exceptions.DatabaseAlreadyOpenError()
        elif not os.access(filename, os.W_OK):
            raise exceptions.DatabaseNotAccessibleError()
        elif not cls.check_compatibility(filename):
            raise exceptions.DatabaseNotValidError()
        else:
            dbs[filename] = cls(filename)

            # Reset modified state after instantiating the class, since this
            # signals an event whose handlers might require the object to be
            # already created
            dbs[filename].reset_modified_state()

            open_database_event.signal(filename=filename)
            return True

    @staticmethod
    def check_compatibility(filename):
        try:
            qconn = _sql.connect(filename)
            cursor = qconn.cursor()
            cursor.execute(queries.compatibility_select)
        except _sql.DatabaseError:
            qconn.close()
            return False

        info = coreaux_api.get_addons_info(disabled=False)

        for row in cursor:
            if row[1] == 'Core':
                if row[3] != coreaux_api.get_core_version():
                    break
            elif row[1] == 'Extension':
                if row[2] in info('Extensions').get_sections():
                    if row[3] == info('Extensions')(str(row[2]))['version']:
                        info('Extensions')(str(row[2])).delete()
                    else:
                        break
                else:
                    break
            elif row[1] == 'Interface':
                if row[2] in info('Interfaces').get_sections():
                    if row[3] == info('Interfaces')(str(row[2]))['version']:
                        info('Interfaces')(str(row[2])).delete()
                    else:
                        break
                else:
                    break
            elif row[1] == 'Plugin':
                if row[2] in info('Plugins').get_sections():
                    if row[3] == info('Plugins')(str(row[2]))['version']:
                        info('Plugins')(str(row[2])).delete()
                    else:
                        break
                else:
                    break
            else:
                break
        else:
            if ('Extensions' not in info.get_sections() or
                             len(info('Extensions').get_sections()) == 0) and (
                             'Interfaces' not in info.get_sections() or
                             len(info('Interfaces').get_sections()) == 0) and (
                             'Plugins' not in info.get_sections() or
                             len(info('Plugins').get_sections()) == 0):
                qconn.close()
                return True

        qconn.close()
        return False

    def save(self):
        qconn = self.connection.get()
        cursor = qconn.cursor()
        cursor.execute(queries.history_update_status_new)
        cursor.execute(queries.history_update_status_old)
        qconn.commit()
        self.connection.give(qconn)

        self.reset_modified_state()

    def save_copy(self, destination):
        # Of course the original file cannot be simply copied, in fact in that
        # case it should be saved first, and that's not what is expected

        qconn = self.connection.get()
        qconnd = _sql.connect(destination)
        cursor = qconn.cursor()
        cursord = qconnd.cursor()

        cursord.execute(queries.properties_delete)
        cursor.execute(queries.properties_select)
        for row in cursor:
            cursord.execute(queries.properties_insert_copy, tuple(row))

        cursord.execute(queries.compatibility_delete)
        cursor.execute(queries.compatibility_select)
        for row in cursor:
            cursord.execute(queries.compatibility_insert_copy, tuple(row))

        cursor.execute(queries.items_select)
        for row in cursor:
            cursord.execute(queries.items_insert_copy, tuple(row))

        cursor.execute(queries.history_select)
        for row in cursor:
            cursord.execute(queries.history_insert_copy, tuple(row))

        cursord.execute(queries.history_update_status_new)
        cursord.execute(queries.history_update_status_old)

        self.connection.give(qconn)

        qconnd.commit()
        qconnd.close()

        save_database_copy_event.signal(origin=self.filename,
                                        destination=destination)

    def close(self):
        self.remove()

        qconn = self.connection.get()
        qconn.close()
        self.connection.task_done()
        self.connection.join()

        close_database_event.signal(filename=self.filename)

        # Note that if the database has not been closed correctly, the history
        # is not cleaned
        self.clean_history()

        return True

    def remove(self):
        for id_ in self.items.copy():
            item = self.items[id_]
            if item.get_filename() == self.filename:
                item.remove()

        global dbs
        del dbs[self.filename]

    def delete_items(self, dids, group, description='Delete items'):
        while dids:
            for id_ in dids:
                # First delete the items without children
                if not self.items[id_].has_children():
                    self.items[id_].delete(group, description=description)
                    del dids[dids.index(id_)]

        delete_items_event.signal()
