# Outspline - A highly modular and extensible outliner.
# Copyright (C) 2011 Dario Giovannetti <dev@dariogiovannetti.net>
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

import wx

from outspline.coreaux_api import Event, OutsplineError
import outspline.coreaux_api as coreaux_api
import outspline.core_api as core_api

import databases
import notebooks
import editor
import textarea
import msgboxes
import logs
import tree
import about

update_menu_items_event = Event()
reset_menu_items_event = Event()
menu_database_update_event = Event()
menu_edit_update_event = Event()
menu_view_update_event = Event()
menu_view_logs_disable_event = Event()
menu_view_logs_update_event = Event()
menu_view_editors_disable_event = Event()


class RootMenu(wx.MenuBar):
    def __init__(self, frame):
        # Note that the menu can be accessed through F10, which is an
        # accelerator that doesn't seem to be overridable neither through
        # menu shortcuts nor through accelerators
        wx.MenuBar.__init__(self)

        self.file = MenuFile()
        self.database = MenuDatabase()
        self.edit = MenuEdit()
        self.view = MenuView()
        self.help = MenuHelp()

        self.Append(self.file, "&File")
        self.Append(self.database, "&Database")
        self.Append(self.edit, "&Editor")
        self.Append(self.view, "&View")
        self.Append(self.help, "&Help")

        self.menu_updaters = {
            self.file: self.file.update_items,
            self.database: self.database.update_items,
            self.edit: self.edit.update_items,
            self.view: self.view.update_items,
        }

        # self.hide_timer must be initialized even if autohide is not set
        self.hide_timer = wx.CallLater(0, int)

        frame.Bind(wx.EVT_MENU_OPEN, self.update_menus)
        frame.Bind(wx.EVT_MENU_CLOSE, self.reset_menus)

    def post_init(self):
        config = coreaux_api.get_interface_configuration('wxgui')

        if config.get_bool('autohide_menubar'):
            self._configure_autohide()

    def _configure_autohide(self):
        self.HIDE_DELAY = 10

        # Note that for F10 to work, a window (any) must be focused: this
        # wouldn't happen naturally after opening a database, so the tree
        # is given focus (with SetFocus) explicitly in order to make F10
        # work
        self.GetFrame().Bind(wx.EVT_CHAR_HOOK, self._handle_F10)

        databases.open_database_event.bind(self._enable_autohide)

        # This would preserve the native Alt+char behaviour to open the main
        #  menu items (thanks to their & shortcuts), however this way such
        #  shortcuts would conflict with the & shortcuts set for the various
        #  Buttons, thus triggering both actions at the same time (open the
        #  menu *and* activate the button)
        # Also note that the preserve_alt_menu_shortcuts option has been
        #  removed from the configuration file
        '''self.uisim = wx.UIActionSimulator()
        config = coreaux_api.get_interface_configuration('wxgui')

        if config('GlobalShortcuts').get_bool('preserve_alt_menu_shortcuts'):
            for menu, label in self.GetMenus():
                try:
                    amp = label.index('&')
                except ValueError:
                    pass
                else:
                    char = label[amp + 1]
                    id_ = wx.NewId()
                    accels.append((wx.ACCEL_ALT, ord(char), id_))
                    frame.Bind(wx.EVT_MENU,
                                self._handle_accelerator_loop(char), id=id_)

    def _handle_accelerator_loop(self, char):
        return lambda event: self._handle_accelerator(event, char)

    def _handle_accelerator(self, event, char):
        # Do *not* call self.Show(), as it will be called after simulating F10
        # The menu must be given focus by simulating F10, otherwise it's
        #  pointless to just show it
        # This method is not called if the menu is already shown, so do not
        #  even attempt to close the menu or similar
        self.uisim.Char(wx.WXK_F10)
        self.uisim.Char(ord(char))
        event.Skip()'''

    def _enable_autohide(self, kwargs):
        databases.open_database_event.bind(self._enable_autohide, False)

        # This both hides the menu the first time and initializes the timer so
        # that it can then be just called with Restart
        self.hide_timer = wx.CallLater(self.HIDE_DELAY, self.Show, False)

        notebooks.last_database_closed_event.bind(self._disable_autohide)

        frame = self.GetFrame()
        frame.Bind(wx.EVT_ENTER_WINDOW, self._handle_enter_frame)
        frame.Bind(wx.EVT_LEAVE_WINDOW, self._handle_leave_frame)

    def _disable_autohide(self, kwargs):
        # Besides being convenient, disabling the autohide when no database is
        # open lets keep accessing it with F10, which would stop working
        # otherwise
        notebooks.last_database_closed_event.bind(self._disable_autohide,
                                                                        False)

        # Don't just stop the timer, because it's always restarted when
        # resetting the menus
        self.hide_timer = wx.CallLater(0, int)
        self.Show()

        frame = self.GetFrame()
        frame.Unbind(wx.EVT_ENTER_WINDOW, handler=self._handle_enter_frame)
        frame.Unbind(wx.EVT_LEAVE_WINDOW, handler=self._handle_leave_frame)

        databases.open_database_event.bind(self._enable_autohide)

    def _handle_F10(self, event):
        if event.GetKeyCode() == wx.WXK_F10:
            self.Show()

        event.Skip()

    def _handle_enter_frame(self, event):
        self.Show(False)
        event.Skip()

    def _handle_leave_frame(self, event):
        if event.GetY() <= 0:
            self.Show()

        event.Skip()

    def update_menus(self, event):
        self.hide_timer.Stop()

        menu = event.GetMenu()

        try:
            updmenu = self.menu_updaters[menu]
        except KeyError:
            update_menu_items_event.signal(menu=menu)
        else:
            updmenu()

    def reset_menus(self, event):
        # Reset the menus only if the closed menu is a top-level one, in fact
        # EVT_MENU_CLOSE is signalled also for sub-menus, but in those cases
        # the menus must not be reset
        if event.GetMenu().GetParent() is None:
            self.hide_timer.Restart()

            # Re-enable all the actions so they are available for their
            # accelerators
            # EVT_MENU_CLOSE is signalled only for the last-closed menu, but
            # since all the others opened have been updated, all the menus have
            # to be reset (don't check event.GetMenu() is menu)
            self.file.reset_items()
            self.database.reset_items()
            self.edit.reset_items()
            self.view.reset_items()

            reset_menu_items_event.signal()


class MenuFile(wx.Menu):
    def __init__(self):
        wx.Menu.__init__(self)

        self.ID_SAVE = wx.NewId()
        self.ID_SAVE_AS = wx.NewId()
        self.ID_BACKUP = wx.NewId()
        self.ID_SAVE_ALL = wx.NewId()
        self.ID_PROPERTIES = wx.NewId()
        self.ID_CLOSE_DB = wx.NewId()
        self.ID_CLOSE_DB_ALL = wx.NewId()

        config = coreaux_api.get_interface_configuration('wxgui')(
                                                    'GlobalShortcuts')('File')

        self.new_ = wx.MenuItem(self, wx.ID_NEW,
                                "&New...\t{}".format(config['new_database']),
                                "Create a new database")
        self.open_ = wx.MenuItem(self, wx.ID_OPEN,
                                "&Open...\t{}".format(config['open_database']),
                                "Open a database")
        self.save = wx.MenuItem(self, self.ID_SAVE,
                                "&Save\t{}".format(config['save_database']),
                                "Save the selected database")
        self.saveas = wx.MenuItem(self, self.ID_SAVE_AS, "Sav&e as...",
                                "Save the selected database with another name")
        self.backup = wx.MenuItem(self, self.ID_BACKUP, "Save &backup...",
                                "Create a backup of the selected database")
        self.saveall = wx.MenuItem(self, self.ID_SAVE_ALL,
                        "Save &all\t{}".format(config['save_all_databases']),
                        "Save all open databases")
        self.properties = wx.MenuItem(self, self.ID_PROPERTIES,
                                "&Properties\t{}".format(config['properties']),
                                "Open database properties")
        self.close_ = wx.MenuItem(self, self.ID_CLOSE_DB,
                                "&Close\t{}".format(config['close_database']),
                                "Close the selected database")
        self.closeall = wx.MenuItem(self, self.ID_CLOSE_DB_ALL,
                        "C&lose all\t{}".format(config['close_all_databases']),
                        "Close all databases")
        self.exit_ = wx.MenuItem(self, wx.ID_EXIT,
                                        "E&xit\t{}".format(config['exit']),
                                        "Terminate the program")

        self.save.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@save'))
        self.saveas.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@saveas'))
        self.backup.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@saveas'))
        self.saveall.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@save'))
        self.properties.SetBitmap(wx.GetApp().artprovider.get_menu_icon(
                                                                '@properties'))
        self.close_.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@close'))
        self.closeall.SetBitmap(wx.GetApp().artprovider.get_menu_icon(
                                                                    '@close'))

        self.AppendItem(self.new_)
        self.AppendItem(self.open_)
        self.AppendSeparator()
        self.AppendItem(self.save)
        self.AppendItem(self.saveas)
        self.AppendItem(self.backup)
        self.AppendItem(self.saveall)
        self.AppendSeparator()
        self.AppendItem(self.properties)
        self.AppendSeparator()
        self.AppendItem(self.close_)
        self.AppendItem(self.closeall)
        self.AppendSeparator()
        self.AppendItem(self.exit_)

        wx.GetApp().Bind(wx.EVT_MENU, self.new_database, self.new_)
        wx.GetApp().Bind(wx.EVT_MENU, self.open_database, self.open_)
        wx.GetApp().Bind(wx.EVT_MENU, self.save_database, self.save)
        wx.GetApp().Bind(wx.EVT_MENU, self._save_database_as, self.saveas)
        wx.GetApp().Bind(wx.EVT_MENU, self.save_all_databases, self.saveall)
        wx.GetApp().Bind(wx.EVT_MENU, self._save_database_backup, self.backup)
        wx.GetApp().Bind(wx.EVT_MENU, self._open_properties, self.properties)
        wx.GetApp().Bind(wx.EVT_MENU, self.close_database, self.close_)
        wx.GetApp().Bind(wx.EVT_MENU, self.close_all_databases, self.closeall)
        wx.GetApp().Bind(wx.EVT_MENU, wx.GetApp().exit_app, self.exit_)

    def update_items(self):
        if tree.dbs:
            for dbname in tuple(tree.dbs.keys()):
                if core_api.check_pending_changes(dbname):
                    self.saveall.Enable()
                    break
            else:
                self.saveall.Enable(False)

            tab = wx.GetApp().nb_left.get_selected_tab()
            filename = tab.get_filename()

            if core_api.check_pending_changes(filename):
                self.save.Enable()
            else:
                self.save.Enable(False)

            self.saveas.Enable()
            self.backup.Enable()

            self.properties.Enable()

            self.close_.Enable()
            self.closeall.Enable()

        else:
            self.save.Enable(False)
            self.saveas.Enable(False)
            self.backup.Enable(False)
            self.saveall.Enable(False)
            self.properties.Enable(False)
            self.close_.Enable(False)
            self.closeall.Enable(False)

    def reset_items(self):
        # Re-enable all the actions so they are available for their
        # accelerators
        self.save.Enable()
        self.saveas.Enable()
        self.backup.Enable()
        self.saveall.Enable()
        self.properties.Enable()
        self.close_.Enable()
        self.closeall.Enable()

    def new_database(self, event, filename=None):
        if core_api.block_databases():
            fn = databases.create_database(filename=filename)

            if fn:
                databases.open_database(fn)

            core_api.release_databases()

    def open_database(self, event, filename=None):
        if core_api.block_databases():
            databases.open_database(filename)
            core_api.release_databases()

    def save_database(self, event):
        if core_api.block_databases():
            treedb = wx.GetApp().nb_left.get_selected_tab()

            if treedb:
                treedb.save()

            core_api.release_databases()

    def save_all_databases(self, event):
        if core_api.block_databases():
            for filename in tuple(tree.dbs.keys()):
                tree.dbs[filename].save()

            core_api.release_databases()

    def _save_database_as(self, event):
        if core_api.block_databases():
            treedb = wx.GetApp().nb_left.get_selected_tab()

            if treedb:
                databases.save_database_as(treedb.get_filename())

            core_api.release_databases()

    def _save_database_backup(self, event):
        if core_api.block_databases():
            treedb = wx.GetApp().nb_left.get_selected_tab()

            if treedb:
                databases.save_database_backup(treedb.get_filename())

            core_api.release_databases()

    def _open_properties(self, event):
        treedb = wx.GetApp().nb_left.get_selected_tab()

        if treedb:
            databases.dbpropmanager.open(treedb.get_filename())

    def close_database(self, event, no_confirm=False):
        if core_api.block_databases():
            treedb = wx.GetApp().nb_left.get_selected_tab()

            if treedb:
                databases.close_database(treedb.get_filename(),
                                                        no_confirm=no_confirm)
            core_api.release_databases()

    def close_all_databases(self, event, no_confirm=False, exit_=False):
        if core_api.block_databases():
            for filename in tuple(tree.dbs.keys()):
                if databases.close_database(filename, no_confirm=no_confirm,
                                                        exit_=exit_) == False:
                    core_api.release_databases()
                    return False
            else:
                core_api.release_databases()
                return True


class MenuDatabase(wx.Menu):
    def __init__(self):
        wx.Menu.__init__(self)

        self.ID_UNDO = wx.NewId()
        self.ID_REDO = wx.NewId()
        self.ID_SIBLING = wx.NewId()
        self.ID_CHILD = wx.NewId()
        self.ID_MOVE_UP = wx.NewId()
        self.ID_MOVE_DOWN = wx.NewId()
        self.ID_MOVE_PARENT = wx.NewId()
        self.ID_EDIT = wx.NewId()
        self.ID_DELETE = wx.NewId()

        config = coreaux_api.get_interface_configuration('wxgui')(
                                                'GlobalShortcuts')('Database')

        self.sibling_label_1 = "Create &item\t{}".format(config['create_item'])
        self.sibling_help_1 = "Create a root item"
        self.sibling_label_2 = "Create s&ibling\t{}".format(
                                                        config['create_item'])
        self.sibling_help_2 = "Create a sibling below the selected item"

        self.undo = wx.MenuItem(self, self.ID_UNDO,
                                "&Undo\t{}".format(config['undo']),
                                "Undo the previous database edit in history")
        self.redo = wx.MenuItem(self, self.ID_REDO,
                                "&Redo\t{}".format(config['redo']),
                                "Redo the next database edit in history")
        self.sibling = wx.MenuItem(self, self.ID_SIBLING, self.sibling_label_1,
                                                        self.sibling_help_1)
        self.child = wx.MenuItem(self, self.ID_CHILD,
                        "Create c&hild\t{}".format(config['create_child']),
                        "Create a child for the selected item")
        self.moveup = wx.MenuItem(self, self.ID_MOVE_UP,
                            "&Move item up\t{}".format(config['move_up']),
                            "Swap the selected item with the one above")
        self.movedn = wx.MenuItem(self, self.ID_MOVE_DOWN,
                            "Mo&ve item down\t{}".format(config['move_down']),
                            "Swap the selected item with the one below")
        self.movept = wx.MenuItem(self, self.ID_MOVE_PARENT,
                "M&ove item to parent\t{}".format(config['move_to_parent']),
                "Move the selected item as a sibling of its parent")
        self.edit = wx.MenuItem(self, self.ID_EDIT,
                                "&Edit item\t{}".format(config['edit']),
                                "Open the selected item in the editor")
        self.delete = wx.MenuItem(self, self.ID_DELETE,
                                "&Delete items\t{}".format(config['delete']),
                                "Delete the selected items")

        self.undo.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@undo'))
        self.redo.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@redo'))
        self.sibling.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@new'))
        self.child.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@new'))
        self.moveup.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@up'))
        self.movedn.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@down'))
        self.movept.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@left'))
        self.edit.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@edit'))
        self.delete.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@delete'))

        self.AppendItem(self.undo)
        self.AppendItem(self.redo)
        self.AppendSeparator()
        self.AppendItem(self.sibling)
        self.AppendItem(self.child)
        self.AppendSeparator()
        self.AppendItem(self.moveup)
        self.AppendItem(self.movedn)
        self.AppendItem(self.movept)
        self.AppendSeparator()
        self.AppendItem(self.edit)
        self.AppendSeparator()
        self.AppendItem(self.delete)

        wx.GetApp().Bind(wx.EVT_MENU, self.undo_tree, self.undo)
        wx.GetApp().Bind(wx.EVT_MENU, self.redo_tree, self.redo)
        wx.GetApp().Bind(wx.EVT_MENU, self.create_child, self.child)
        wx.GetApp().Bind(wx.EVT_MENU, self.create_sibling, self.sibling)
        wx.GetApp().Bind(wx.EVT_MENU, self.move_item_up, self.moveup)
        wx.GetApp().Bind(wx.EVT_MENU, self.move_item_down, self.movedn)
        wx.GetApp().Bind(wx.EVT_MENU, self.move_item_to_parent, self.movept)
        wx.GetApp().Bind(wx.EVT_MENU, self.edit_item, self.edit)
        wx.GetApp().Bind(wx.EVT_MENU, self.delete_items, self.delete)

    def update_items(self):
        tab = wx.GetApp().nb_left.get_selected_tab()

        if tab:
            filename = tab.get_filename()
            sel = tab.get_selections()

            if core_api.preview_undo_tree(filename):
                self.undo.Enable()
            else:
                self.undo.Enable(False)

            if core_api.preview_redo_tree(filename):
                self.redo.Enable()
            else:
                self.redo.Enable(False)

            if len(sel) == 1:
                self.sibling.Enable()
                self.sibling.SetItemLabel(self.sibling_label_2)
                self.sibling.SetHelp(self.sibling_help_2)
                self.child.Enable()

                id_ = tab.get_item_id(sel[0])

                if core_api.get_item_previous(filename, id_):
                    self.moveup.Enable()
                else:
                    self.moveup.Enable(False)

                if core_api.get_item_next(filename, id_):
                    self.movedn.Enable()
                else:
                    self.movedn.Enable(False)

                if not core_api.is_item_root(filename, id_):
                    self.movept.Enable()
                else:
                    self.movept.Enable(False)

                self.edit.Enable()
                self.delete.Enable()

            elif len(sel) > 1:
                self.sibling.Enable(False)
                self.sibling.SetItemLabel(self.sibling_label_1)
                self.sibling.SetHelp(self.sibling_help_1)
                self.child.Enable(False)
                self.moveup.Enable(False)
                self.movedn.Enable(False)
                self.movept.Enable(False)
                self.edit.Enable()
                self.delete.Enable()

            else:
                self.sibling.Enable()
                self.sibling.SetItemLabel(self.sibling_label_1)
                self.sibling.SetHelp(self.sibling_help_1)
                self.child.Enable(False)
                self.moveup.Enable(False)
                self.movedn.Enable(False)
                self.movept.Enable(False)
                self.edit.Enable(False)
                self.delete.Enable(False)

            menu_database_update_event.signal(filename=filename)
        else:
            self.undo.Enable(False)
            self.redo.Enable(False)
            self.sibling.Enable(False)
            self.child.Enable(False)
            self.moveup.Enable(False)
            self.movedn.Enable(False)
            self.movept.Enable(False)
            self.edit.Enable(False)
            self.delete.Enable(False)
            self.sibling.SetItemLabel(self.sibling_label_1)
            self.sibling.SetHelp(self.sibling_help_1)

            # Signal the event even if there are no databases (tabs) open
            menu_database_update_event.signal(filename=None)

    def reset_items(self):
        # Re-enable all the actions so they are available for their
        # accelerators
        self.undo.Enable()
        self.redo.Enable()
        self.sibling.Enable()
        self.child.Enable()
        self.moveup.Enable()
        self.movedn.Enable()
        self.movept.Enable()
        self.edit.Enable()
        self.delete.Enable()

    def undo_tree(self, event, no_confirm=False):
        tab = wx.GetApp().nb_left.get_selected_tab()

        if tab:
            tab.undo(no_confirm=no_confirm)

    def redo_tree(self, event, no_confirm=False):
        tab = wx.GetApp().nb_left.get_selected_tab()

        if tab:
            tab.redo(no_confirm=no_confirm)

    def create_sibling(self, event):
        treedb = wx.GetApp().nb_left.get_selected_tab()

        if treedb:
            treedb.create_sibling()

    def create_child(self, event):
        treedb = wx.GetApp().nb_left.get_selected_tab()

        if treedb:
            treedb.create_child()

    def move_item_up(self, event):
        treedb = wx.GetApp().nb_left.get_selected_tab()

        if treedb:
            treedb.move_item_up()

    def move_item_down(self, event):
        treedb = wx.GetApp().nb_left.get_selected_tab()

        if treedb:
            treedb.move_item_down()

    def move_item_to_parent(self, event):
        treedb = wx.GetApp().nb_left.get_selected_tab()

        if treedb:
            treedb.move_item_to_parent()

    def edit_item(self, event):
        treedb = wx.GetApp().nb_left.get_selected_tab()

        if treedb:
            treedb.edit_item()

    def delete_items(self, event, no_confirm=False):
        treedb = wx.GetApp().nb_left.get_selected_tab()

        if treedb:
            treedb.delete_selected_items(no_confirm=no_confirm)


class MenuEdit(wx.Menu):
    def __init__(self):
        wx.Menu.__init__(self)

        self.ID_SELECT_ALL = wx.NewId()
        self.ID_CUT = wx.NewId()
        self.ID_COPY = wx.NewId()
        self.ID_PASTE = wx.NewId()
        self.ID_FIND = wx.NewId()
        self.ID_APPLY = wx.NewId()
        self.ID_APPLY_ALL = wx.NewId()

        config = coreaux_api.get_interface_configuration('wxgui')(
                                                'GlobalShortcuts')('Edit')

        self.select = wx.MenuItem(self, self.ID_SELECT_ALL,
                                "&Select all\t{}".format(config['select_all']),
                                "Select all text in the editor")
        self.cut = wx.MenuItem(self, self.ID_CUT,
                                            "Cu&t\t{}".format(config['cut']),
                                            "Cut selected text in the editor")
        self.copy = wx.MenuItem(self, self.ID_COPY,
                                            "&Copy\t{}".format(config['copy']),
                                            "Copy selected text in the editor")
        self.paste = wx.MenuItem(self, self.ID_PASTE,
                                        "&Paste\t{}".format(config['paste']),
                                        "Paste text at the cursor")
        self.find = wx.MenuItem(self, self.ID_FIND,
                                "&Find in database\t{}".format(config['find']),
                                "Find the edited item in the database tree")
        self.apply = wx.MenuItem(self, self.ID_APPLY,
                                        "&Apply\t{}".format(config['apply']),
                                        "Apply the focused editor")
        self.applyall = wx.MenuItem(self, self.ID_APPLY_ALL,
                                "App&ly all\t{}".format(config['apply_all']),
                                "Apply all open editors")

        self.select.SetBitmap(wx.GetApp().artprovider.get_menu_icon(
                                                                '@selectall'))
        self.cut.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@cut'))
        self.copy.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@copy'))
        self.paste.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@paste'))
        self.find.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@dbfind'))
        self.apply.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@apply'))
        self.applyall.SetBitmap(wx.GetApp().artprovider.get_menu_icon(
                                                                    '@apply'))

        self.AppendItem(self.select)
        self.AppendItem(self.cut)
        self.AppendItem(self.copy)
        self.AppendItem(self.paste)
        self.AppendSeparator()
        self.AppendItem(self.find)
        self.AppendSeparator()
        self.AppendItem(self.apply)
        self.AppendItem(self.applyall)

        wx.GetApp().Bind(wx.EVT_MENU, self._select_all_text, self.select)
        wx.GetApp().Bind(wx.EVT_MENU, self._cut_text, self.cut)
        wx.GetApp().Bind(wx.EVT_MENU, self._copy_text, self.copy)
        wx.GetApp().Bind(wx.EVT_MENU, self._paste_text, self.paste)
        wx.GetApp().Bind(wx.EVT_MENU, self._find_item, self.find)
        wx.GetApp().Bind(wx.EVT_MENU, self.apply_tab, self.apply)
        wx.GetApp().Bind(wx.EVT_MENU, self.apply_all_tabs, self.applyall)

    def update_items(self):
        if editor.tabs:
            for i in tuple(editor.tabs.keys()):
                if editor.tabs[i].is_modified():
                    self.applyall.Enable()
                    break
            else:
                self.applyall.Enable(False)

            item = wx.GetApp().nb_right.get_selected_editor()

            if item:
                filename = editor.tabs[item].get_filename()
                id_ = editor.tabs[item].get_id()

                self.select.Enable()

                if editor.tabs[item].area.can_cut():
                    self.cut.Enable()
                else:
                    self.cut.Enable(False)

                if editor.tabs[item].area.can_copy():
                    self.copy.Enable()
                else:
                    self.copy.Enable(False)

                if editor.tabs[item].area.can_paste():
                    self.paste.Enable()
                else:
                    self.paste.Enable(False)

                self.find.Enable()

                if editor.tabs[item].is_modified():
                    self.apply.Enable()
                else:
                    self.apply.Enable(False)

                menu_edit_update_event.signal(filename=filename, id_=id_,
                                                                    item=item)
            else:
                self.select.Enable(False)
                self.cut.Enable(False)
                self.copy.Enable(False)
                self.paste.Enable(False)
                self.find.Enable(False)
                self.apply.Enable(False)

                # Signal the event even if there are no editor tabs open
                menu_edit_update_event.signal(filename=None, id_=None,
                                                                    item=None)
        else:
            self.select.Enable(False)
            self.cut.Enable(False)
            self.copy.Enable(False)
            self.paste.Enable(False)
            self.find.Enable(False)
            self.apply.Enable(False)
            self.applyall.Enable(False)

            # Signal the event even if there are no tabs open
            menu_edit_update_event.signal(filename=None, id_=None, item=None)

    def reset_items(self):
        # Re-enable all the actions so they are available for their
        # accelerators
        self.select.Enable()
        self.cut.Enable()
        self.copy.Enable()
        self.paste.Enable()
        self.find.Enable()
        self.apply.Enable()
        self.applyall.Enable()

    def _select_all_text(self, event):
        tab = wx.GetApp().nb_right.get_selected_editor()
        if tab:
            editor.tabs[tab].area.select_all()

    def _cut_text(self, event):
        tab = wx.GetApp().nb_right.get_selected_editor()
        if tab:
            editor.tabs[tab].area.cut()

    def _copy_text(self, event):
        tab = wx.GetApp().nb_right.get_selected_editor()
        if tab:
            editor.tabs[tab].area.copy()

    def _paste_text(self, event):
        tab = wx.GetApp().nb_right.get_selected_editor()
        if tab:
            editor.tabs[tab].area.paste()

    def _find_item(self, event):
        tab = wx.GetApp().nb_right.get_selected_editor()
        if tab:
            editor.tabs[tab].find_in_tree()

    def apply_tab(self, event):
        if core_api.block_databases():
            tab = wx.GetApp().nb_right.get_selected_editor()
            if tab:
                editor.tabs[tab].apply()

            core_api.release_databases()

    def apply_all_tabs(self, event):
        if core_api.block_databases():
            for item in editor.tabs:
                editor.tabs[item].apply()

            core_api.release_databases()


class MenuView(wx.Menu):
    def __init__(self):
        wx.Menu.__init__(self)

        self.has_plugin_items = False

        self.ID_DATABASES = wx.NewId()
        self.ID_LOGS = wx.NewId()
        self.ID_RIGHTNB = wx.NewId()
        self.ID_PROPS = wx.NewId()
        self.ID_EDITORS = wx.NewId()

        self.databases_submenu = MenuViewDatabases()
        self.logs_submenu = MenuViewLogs()
        self.rightnb_submenu = MenuViewRightNB()
        self.editors_submenu = MenuViewEditors()

        self.databases = wx.MenuItem(self, self.ID_DATABASES,
                        "&Databases", "Databases navigation actions",
                        subMenu=self.databases_submenu)
        self.logs = wx.MenuItem(self, self.ID_LOGS,
                        "&Logs", "Logs navigation actions",
                        subMenu=self.logs_submenu)
        self.rightnb = wx.MenuItem(self, self.ID_RIGHTNB,
                        "&Right notebook", "Right notebook navigation actions",
                        subMenu=self.rightnb_submenu)
        self.editors = wx.MenuItem(self, self.ID_EDITORS,
                        "&Editor", "Selected editor navigation actions",
                        subMenu=self.editors_submenu)

        self.databases.SetBitmap(wx.GetApp().artprovider.get_menu_icon(
                                                                    '@left'))
        self.logs.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@logs'))
        self.rightnb.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@right'))
        self.editors.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@edit'))

        self.AppendItem(self.databases)
        self.AppendItem(self.logs)
        self.AppendSeparator()
        self.AppendItem(self.rightnb)
        self.AppendItem(self.editors)

    def update_items(self):
        self.databases_submenu.update_items()
        self.logs_submenu.update_items()
        self.rightnb_submenu.update_items()
        self.editors_submenu.update_items()

        menu_view_update_event.signal()

    def reset_items(self):
        # Re-enable all the actions so they are available for their
        # accelerators
        self.databases_submenu.reset_items()
        self.logs_submenu.reset_items()
        self.rightnb_submenu.reset_items()
        self.editors_submenu.reset_items()

    def insert_tab_group(self, menu):
        self.InsertItem(5, menu)

    def append_plugin_item(self, item):
        if not self.has_plugin_items:
            self.AppendSeparator()
            self.has_plugin_items = True

        self.AppendItem(item)


class MenuViewDatabases(wx.Menu):
    def __init__(self):
        wx.Menu.__init__(self)

        self.ID_CYCLE = wx.NewId()
        self.ID_RCYCLE = wx.NewId()
        self.ID_FOCUS = wx.NewId()
        self.ID_FOCUS_1 = wx.NewId()
        self.ID_FOCUS_2 = wx.NewId()
        self.ID_FOCUS_3 = wx.NewId()
        self.ID_FOCUS_4 = wx.NewId()
        self.ID_FOCUS_5 = wx.NewId()
        self.ID_FOCUS_6 = wx.NewId()
        self.ID_FOCUS_7 = wx.NewId()
        self.ID_FOCUS_8 = wx.NewId()
        self.ID_FOCUS_9 = wx.NewId()
        self.ID_FOCUS_LAST = wx.NewId()

        config = coreaux_api.get_interface_configuration('wxgui')(
                                        'GlobalShortcuts')('View')('Databases')

        self.cycle = wx.MenuItem(self, self.ID_CYCLE,
                        "&Cycle forward\t{}".format(config['cycle']),
                        "Cycle through the open databases")
        self.rcycle = wx.MenuItem(self, self.ID_RCYCLE,
                        "Cycle &backward\t{}".format(config['cycle_reverse']),
                        "Cycle through the open databases in reverse order")
        self.focus = wx.MenuItem(self, self.ID_FOCUS,
                        "&Focus selected\t{}".format(config['focus']),
                        "Set focus on the selected database")
        self.focusN = (
            wx.MenuItem(self, self.ID_FOCUS_1,
                        "Focus &1st database\t{}".format(config['focus_1']),
                        "Set focus on the first database"),
            wx.MenuItem(self, self.ID_FOCUS_2,
                        "Focus &2nd database\t{}".format(config['focus_2']),
                        "Set focus on the second database"),
            wx.MenuItem(self, self.ID_FOCUS_3,
                        "Focus &3rd database\t{}".format(config['focus_3']),
                        "Set focus on the third database"),
            wx.MenuItem(self, self.ID_FOCUS_4,
                        "Focus &4th database\t{}".format(config['focus_4']),
                        "Set focus on the fourth database"),
            wx.MenuItem(self, self.ID_FOCUS_5,
                        "Focus &5th database\t{}".format(config['focus_5']),
                        "Set focus on the fifth database"),
            wx.MenuItem(self, self.ID_FOCUS_6,
                        "Focus &6th database\t{}".format(config['focus_6']),
                        "Set focus on the sixth database"),
            wx.MenuItem(self, self.ID_FOCUS_7,
                        "Focus &7th database\t{}".format(config['focus_7']),
                        "Set focus on the seventh database"),
            wx.MenuItem(self, self.ID_FOCUS_8,
                        "Focus &8th database\t{}".format(config['focus_8']),
                        "Set focus on the eighth database"),
            wx.MenuItem(self, self.ID_FOCUS_9,
                        "Focus &9th database\t{}".format(config['focus_9']),
                        "Set focus on the ninth database"),
        )
        self.focus_last = wx.MenuItem(self, self.ID_FOCUS_LAST,
                        "Focus last database\t{}".format(config['focus_last']),
                        "Set focus on the last database")

        self.cycle.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@right'))
        self.rcycle.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@left'))
        self.focus.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@jump'))

        self.AppendItem(self.cycle)
        self.AppendItem(self.rcycle)
        self.AppendItem(self.focus)
        self.AppendSeparator()

        for focus in self.focusN:
            self.AppendItem(focus)

        self.AppendItem(self.focus_last)

        wx.GetApp().Bind(wx.EVT_MENU, self._cycle, self.cycle)
        wx.GetApp().Bind(wx.EVT_MENU, self._rcycle, self.rcycle)
        wx.GetApp().Bind(wx.EVT_MENU, self._focus, self.focus)
        wx.GetApp().Bind(wx.EVT_MENU, self._focus1, self.focusN[0])
        wx.GetApp().Bind(wx.EVT_MENU, self._focus2, self.focusN[1])
        wx.GetApp().Bind(wx.EVT_MENU, self._focus3, self.focusN[2])
        wx.GetApp().Bind(wx.EVT_MENU, self._focus4, self.focusN[3])
        wx.GetApp().Bind(wx.EVT_MENU, self._focus5, self.focusN[4])
        wx.GetApp().Bind(wx.EVT_MENU, self._focus6, self.focusN[5])
        wx.GetApp().Bind(wx.EVT_MENU, self._focus7, self.focusN[6])
        wx.GetApp().Bind(wx.EVT_MENU, self._focus8, self.focusN[7])
        wx.GetApp().Bind(wx.EVT_MENU, self._focus9, self.focusN[8])
        wx.GetApp().Bind(wx.EVT_MENU, self._focus_last, self.focus_last)

    def update_items(self):
        ndb = len(databases.get_open_databases())

        if ndb < 1:
            self.cycle.Enable(False)
            self.rcycle.Enable(False)
            self.focus.Enable(False)
            self.focus_last.Enable(False)

        # If there are more than 8 open databases, xrange will always be an
        # empty iterator
        for N in xrange(ndb, 9):
            self.focusN[N].Enable(False)

    def reset_items(self):
        # Re-enable all the actions so they are available for their
        # accelerators
        self.cycle.Enable()
        self.rcycle.Enable()
        self.focus.Enable()
        self.focus_last.Enable()

        for focus in self.focusN:
            focus.Enable()

    def _cycle(self, event):
        wx.GetApp().nb_left.AdvanceSelection()

    def _rcycle(self, event):
        wx.GetApp().nb_left.AdvanceSelection(False)

    def _focus(self, event):
        tab = wx.GetApp().nb_left.get_selected_tab()

        if tab:
            # Explicitly focus the database, not the whole notebook tab,
            # otherwise it won't have effect if the logs are focused
            tab.focus_database()

    def _focus1(self, event):
        tab = wx.GetApp().nb_left.select_page(0)

    def _focus2(self, event):
        tab = wx.GetApp().nb_left.select_page(1)

    def _focus3(self, event):
        tab = wx.GetApp().nb_left.select_page(2)

    def _focus4(self, event):
        tab = wx.GetApp().nb_left.select_page(3)

    def _focus5(self, event):
        tab = wx.GetApp().nb_left.select_page(4)

    def _focus6(self, event):
        tab = wx.GetApp().nb_left.select_page(5)

    def _focus7(self, event):
        tab = wx.GetApp().nb_left.select_page(6)

    def _focus8(self, event):
        tab = wx.GetApp().nb_left.select_page(7)

    def _focus9(self, event):
        tab = wx.GetApp().nb_left.select_page(8)

    def _focus_last(self, event):
        tab = wx.GetApp().nb_left.select_last_page()


class MenuViewLogs(wx.Menu):
    def __init__(self):
        wx.Menu.__init__(self)

        self.ID_SHOW = wx.NewId()
        self.ID_CYCLE = wx.NewId()
        self.ID_RCYCLE = wx.NewId()
        self.ID_FOCUS = wx.NewId()
        self.ID_ITEMS = wx.NewId()

        self.items_submenu = MenuViewLogItems()

        config = coreaux_api.get_interface_configuration('wxgui')(
                                            'GlobalShortcuts')('View')('Logs')

        self.show = wx.MenuItem(self, self.ID_SHOW,
                        "Show &panel\t{}".format(config['show']),
                        "Show logs panel", kind=wx.ITEM_CHECK)
        self.cycle = wx.MenuItem(self, self.ID_CYCLE,
                        "&Cycle forward\t{}".format(config['cycle']),
                        "Cycle through the logs")
        self.rcycle = wx.MenuItem(self, self.ID_RCYCLE,
                        "Cycle &backward\t{}".format(config['cycle_reverse']),
                        "Cycle through the logs in reverse order")
        self.focus = wx.MenuItem(self, self.ID_FOCUS,
                        "&Focus selected\t{}".format(config['focus']),
                        "Set focus on the selected log")
        self.items = wx.MenuItem(self, self.ID_ITEMS,
                        "&Items", "Set focus on the items history log",
                        subMenu=self.items_submenu)

        self.cycle.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@right'))
        self.rcycle.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@left'))
        self.focus.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@jump'))
        self.items.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@edit'))

        self.AppendItem(self.show)
        self.AppendItem(self.cycle)
        self.AppendItem(self.rcycle)
        self.AppendItem(self.focus)
        self.AppendSeparator()
        self.AppendItem(self.items)

        wx.GetApp().Bind(wx.EVT_MENU, self._toggle_shown, self.show)
        wx.GetApp().Bind(wx.EVT_MENU, self._cycle, self.cycle)
        wx.GetApp().Bind(wx.EVT_MENU, self._rcycle, self.rcycle)
        wx.GetApp().Bind(wx.EVT_MENU, self._focus, self.focus)

    def update_items(self):
        self.show.Check(check=wx.GetApp().logs_configuration.is_shown())
        ndb = len(databases.get_open_databases())

        if ndb < 1:
            self.cycle.Enable(False)
            self.rcycle.Enable(False)
            self.focus.Enable(False)
            self.items.Enable(False)

            menu_view_logs_disable_event.signal()
        else:
            menu_view_logs_update_event.signal()

    def reset_items(self):
        # Re-enable all the actions so they are available for their
        # accelerators
        self.cycle.Enable()
        self.rcycle.Enable()
        self.focus.Enable()
        self.items.Enable()

    def _toggle_shown(self, event):
        # Set logs_configuration.set_shown() here, and not in each
        # tree.dbs[].show_logs()... so that this method works also if there
        # aren't open databases
        if wx.GetApp().logs_configuration.is_shown():
            for filename in tree.dbs:
                tree.dbs[filename].hide_logs()
            wx.GetApp().logs_configuration.set_shown(False)
        else:
            for filename in tree.dbs:
                tree.dbs[filename].show_logs()
            wx.GetApp().logs_configuration.set_shown(True)

    def _cycle(self, event):
        tab = wx.GetApp().nb_left.get_selected_tab()

        if tab:
            tab.get_logs_panel().advance_selection()

    def _rcycle(self, event):
        tab = wx.GetApp().nb_left.get_selected_tab()

        if tab:
            tab.get_logs_panel().reverse_selection()

    def _focus(self, event):
        tab = wx.GetApp().nb_left.get_selected_tab()

        if tab:
            tab.get_logs_panel().focus_selected()


class MenuViewLogItems(wx.Menu):
    def __init__(self):
        wx.Menu.__init__(self)

        self.ID_SELECT = wx.NewId()

        config = coreaux_api.get_interface_configuration('wxgui')(
                                    'GlobalShortcuts')('View')('Logs')('Items')

        self.select = wx.MenuItem(self, self.ID_SELECT,
                        "&Select\t{}".format(config['select']),
                        "Select the items history log")

        self.select.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@jump'))

        self.AppendItem(self.select)

        wx.GetApp().Bind(wx.EVT_MENU, self._select, self.select)

    def _select(self, event):
        treedb = wx.GetApp().nb_left.get_selected_tab()

        if treedb:
            treedb.dbhistory.select()


class MenuViewRightNB(wx.Menu):
    def __init__(self):
        wx.Menu.__init__(self)

        self.ID_CYCLE = wx.NewId()
        self.ID_RCYCLE = wx.NewId()
        self.ID_FOCUS = wx.NewId()
        self.ID_CLOSE = wx.NewId()
        self.ID_FOCUS_1 = wx.NewId()
        self.ID_FOCUS_2 = wx.NewId()
        self.ID_FOCUS_3 = wx.NewId()
        self.ID_FOCUS_4 = wx.NewId()
        self.ID_FOCUS_5 = wx.NewId()
        self.ID_FOCUS_6 = wx.NewId()
        self.ID_FOCUS_7 = wx.NewId()
        self.ID_FOCUS_8 = wx.NewId()
        self.ID_FOCUS_9 = wx.NewId()
        self.ID_FOCUS_LAST = wx.NewId()

        config = coreaux_api.get_interface_configuration('wxgui')(
                                    'GlobalShortcuts')('View')('RightNotebook')

        self.cycle = wx.MenuItem(self, self.ID_CYCLE,
                        "&Cycle forward\t{}".format(config['cycle']),
                        "Cycle through the open right-pane tabs")
        self.rcycle = wx.MenuItem(self, self.ID_RCYCLE,
                    "Cycle &backward\t{}".format(config['cycle_reverse']),
                    "Cycle through the open right-pane tabs in reverse order")
        self.focus = wx.MenuItem(self, self.ID_FOCUS,
                        "&Focus selected\t{}".format(config['focus']),
                        "Set focus on the selected right-pane tab")
        self.close = wx.MenuItem(self, self.ID_CLOSE,
                        "C&lose selected\t{}".format(config['close']),
                        "Close the selected right-pane tab")
        self.focusN = (
            wx.MenuItem(self, self.ID_FOCUS_1,
                            "Focus &1st tab\t{}".format(config['focus_1']),
                            "Set focus on the first right-pane tab"),
            wx.MenuItem(self, self.ID_FOCUS_2,
                            "Focus &2nd tab\t{}".format(config['focus_2']),
                            "Set focus on the second right-pane tab"),
            wx.MenuItem(self, self.ID_FOCUS_3,
                            "Focus &3rd tab\t{}".format(config['focus_3']),
                            "Set focus on the third right-pane tab"),
            wx.MenuItem(self, self.ID_FOCUS_4,
                            "Focus &4th tab\t{}".format(config['focus_4']),
                            "Set focus on the fourth right-pane tab"),
            wx.MenuItem(self, self.ID_FOCUS_5,
                            "Focus &5th tab\t{}".format(config['focus_5']),
                            "Set focus on the fifth right-pane tab"),
            wx.MenuItem(self, self.ID_FOCUS_6,
                            "Focus &6th tab\t{}".format(config['focus_6']),
                            "Set focus on the sixth right-pane tab"),
            wx.MenuItem(self, self.ID_FOCUS_7,
                            "Focus &7th tab\t{}".format(config['focus_7']),
                            "Set focus on the seventh right-pane tab"),
            wx.MenuItem(self, self.ID_FOCUS_8,
                            "Focus &8th tab\t{}".format(config['focus_8']),
                            "Set focus on the eighth right-pane tab"),
            wx.MenuItem(self, self.ID_FOCUS_9,
                            "Focus &9th tab\t{}".format(config['focus_9']),
                            "Set focus on the ninth right-pane tab"),
        )
        self.focus_last = wx.MenuItem(self, self.ID_FOCUS_LAST,
                            "Focus last tab\t{}".format(config['focus_last']),
                            "Set focus on the last right-pane tab")

        self.cycle.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@right'))
        self.rcycle.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@left'))
        self.focus.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@jump'))
        self.close.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@close'))

        self.AppendItem(self.cycle)
        self.AppendItem(self.rcycle)
        self.AppendItem(self.focus)
        self.AppendItem(self.close)
        self.AppendSeparator()

        for focus in self.focusN:
            self.AppendItem(focus)

        self.AppendItem(self.focus_last)

        wx.GetApp().Bind(wx.EVT_MENU, self._cycle, self.cycle)
        wx.GetApp().Bind(wx.EVT_MENU, self._rcycle, self.rcycle)
        wx.GetApp().Bind(wx.EVT_MENU, self._focus, self.focus)
        wx.GetApp().Bind(wx.EVT_MENU, self._close, self.close)
        wx.GetApp().Bind(wx.EVT_MENU, self._focus1, self.focusN[0])
        wx.GetApp().Bind(wx.EVT_MENU, self._focus2, self.focusN[1])
        wx.GetApp().Bind(wx.EVT_MENU, self._focus3, self.focusN[2])
        wx.GetApp().Bind(wx.EVT_MENU, self._focus4, self.focusN[3])
        wx.GetApp().Bind(wx.EVT_MENU, self._focus5, self.focusN[4])
        wx.GetApp().Bind(wx.EVT_MENU, self._focus6, self.focusN[5])
        wx.GetApp().Bind(wx.EVT_MENU, self._focus7, self.focusN[6])
        wx.GetApp().Bind(wx.EVT_MENU, self._focus8, self.focusN[7])
        wx.GetApp().Bind(wx.EVT_MENU, self._focus9, self.focusN[8])
        wx.GetApp().Bind(wx.EVT_MENU, self._focus_last, self.focus_last)

    def update_items(self):
        ntabs = wx.GetApp().nb_right.get_apparent_page_count()

        if ntabs < 1:
            self.cycle.Enable(False)
            self.rcycle.Enable(False)
            self.focus.Enable(False)
            self.close.Enable(False)
            self.focus_last.Enable(False)

        # If there are more than 8 open tabs, xrange will always be an empty
        # iterator
        for N in xrange(ntabs, 9):
            self.focusN[N].Enable(False)

    def reset_items(self):
        # Re-enable all the actions so they are available for their
        # accelerators
        self.cycle.Enable()
        self.rcycle.Enable()
        self.focus.Enable()
        self.close.Enable()
        self.focus_last.Enable()

        for focus in self.focusN:
            focus.Enable()

    def _cycle(self, event):
        wx.GetApp().nb_right.AdvanceSelection()

    def _rcycle(self, event):
        wx.GetApp().nb_right.AdvanceSelection(False)

    def _focus(self, event):
        tab = wx.GetApp().nb_right.get_apparent_selected_tab()

        if tab:
            tab.SetFocus()

    def _close(self, event):
        tab = wx.GetApp().nb_right.get_apparent_selected_tab()

        if tab:
            wx.GetApp().nb_right.close_tab(tab)

    def _focus1(self, event):
        tab = wx.GetApp().nb_right.select_page(0)

    def _focus2(self, event):
        tab = wx.GetApp().nb_right.select_page(1)

    def _focus3(self, event):
        tab = wx.GetApp().nb_right.select_page(2)

    def _focus4(self, event):
        tab = wx.GetApp().nb_right.select_page(3)

    def _focus5(self, event):
        tab = wx.GetApp().nb_right.select_page(4)

    def _focus6(self, event):
        tab = wx.GetApp().nb_right.select_page(5)

    def _focus7(self, event):
        tab = wx.GetApp().nb_right.select_page(6)

    def _focus8(self, event):
        tab = wx.GetApp().nb_right.select_page(7)

    def _focus9(self, event):
        tab = wx.GetApp().nb_right.select_page(8)

    def _focus_last(self, event):
        tab = wx.GetApp().nb_right.select_last_page()


class MenuViewEditors(wx.Menu):
    def __init__(self):
        wx.Menu.__init__(self)

        self.has_plugin_items = False

        self.ID_FOCUS_TEXT = wx.NewId()

        config = coreaux_api.get_interface_configuration('wxgui')(
                                        'GlobalShortcuts')('View')('Editors')

        self.text = wx.MenuItem(self, self.ID_FOCUS_TEXT,
                    "Focus &text area\t{}".format(config['focus_text_area']),
                    "Focus the editor's text area")

        self.text.SetBitmap(wx.GetApp().artprovider.get_menu_icon('@jump'))

        self.AppendItem(self.text)

        wx.GetApp().Bind(wx.EVT_MENU, self._focus_text_area, self.text)

    def update_items(self):
        if not wx.GetApp().nb_right.get_selected_editor():
            self.text.Enable(False)
            menu_view_editors_disable_event.signal()

    def reset_items(self):
        # Re-enable all the actions so they are available for their
        # accelerators
        self.text.Enable()

    def append_plugin_item(self, item):
        if not self.has_plugin_items:
            self.AppendSeparator()
            self.has_plugin_items = True

        self.AppendItem(item)

    def _focus_text_area(self, event):
        tab = wx.GetApp().nb_right.get_selected_editor()

        if tab:
            editor.tabs[tab].focus_text()


class MenuHelp(wx.Menu):
    def __init__(self):
        wx.Menu.__init__(self)

        self.about = self.Append(wx.ID_ABOUT, '&About Outspline',
                    'Information about Outspline and the installed add-ons')

        wx.GetApp().Bind(wx.EVT_MENU, self._show_about, self.about)

    def _show_about(self, event):
        about.AboutWindow()
