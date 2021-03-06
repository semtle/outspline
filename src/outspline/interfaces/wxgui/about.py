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
from datetime import datetime

from outspline.static.wxclasses.texturl import TextUrlCtrl
import outspline.coreaux_api as coreaux_api

_SIZE = 600


class AboutWindow(wx.Dialog):
    def __init__(self):
        wx.Dialog.__init__(self, wx.GetApp().root, title='About Outspline',
                          size=(_SIZE, _SIZE * 2 // 3))

        sizer1 = wx.GridBagSizer(4, 4)
        self.SetSizer(sizer1)

        logo = wx.StaticBitmap(self, bitmap=wx.Bitmap(
                                    wx.GetApp().artprovider.get_about_icon()))

        name = wx.StaticText(self, label='Outspline')
        name.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC,
                             wx.FONTWEIGHT_BOLD))

        cinfo = coreaux_api.get_main_component_info()

        version = wx.StaticText(self, label='version: {} ({})'.format(
                                            cinfo.version, cinfo.release_date))

        self.copyright = wx.StaticText(self,
                                    label=coreaux_api.get_copyright_unicode())
        self.copyright.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT,
                                       wx.FONTSTYLE_NORMAL,
                                       wx.FONTWEIGHT_NORMAL))

        coreinfo = coreaux_api.get_core_info()

        self.website = wx.HyperlinkCtrl(self,
            label=coreinfo.website, url=coreinfo.website)

        description = wx.StaticText(self,
                                    label=coreaux_api.get_description())
        description.Wrap(_SIZE - 8)

        info = InfoBox(self)

        button = wx.Button(self, label='&Close')

        sizer1.Add(logo, (0, 0), span=(2, 1), flag=wx.ALIGN_CENTER | wx.LEFT |
                   wx.TOP | wx.RIGHT, border=8)
        sizer1.Add(name, (0, 1), flag=wx.ALIGN_LEFT | wx.ALIGN_BOTTOM | wx.TOP,
                   border=8)
        sizer1.Add(version, (0, 2), flag=wx.ALIGN_RIGHT | wx.ALIGN_BOTTOM |
                   wx.RIGHT, border=8)
        sizer1.Add(self.copyright, (1, 1), flag=wx.ALIGN_LEFT |
                   wx.ALIGN_CENTER_VERTICAL)
        sizer1.Add(self.website, (1, 2), flag=wx.ALIGN_RIGHT |
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=8)
        sizer1.Add(description, (2, 0), span=(1, 3), flag=wx.ALL, border=4)
        sizer1.Add(info, (3, 0), span=(1, 3), flag=wx.LEFT | wx.RIGHT |
                   wx.EXPAND, border=4)
        sizer1.Add(button, (4, 0), span=(1, 3), flag=wx.ALIGN_CENTER |
                   wx.BOTTOM, border=4)

        sizer1.AddGrowableRow(3)
        sizer1.AddGrowableCol(2)

        self.Bind(wx.EVT_BUTTON, self.close, button)

        self.Centre()
        self.Show(True)

    def close(self, event):
        self.Destroy()


class InfoBox(wx.SplitterWindow):
    tree = None
    textw = None
    STYLE_HEAD = None
    STYLE_NORMAL = None
    STYLE_BOLD = None
    STYLE_ITALIC = None

    def __init__(self, parent):
        wx.SplitterWindow.__init__(self, parent, style=wx.SP_LIVE_UPDATE)

        self.tree = wx.TreeCtrl(self, style=wx.TR_HAS_BUTTONS |
                                wx.TR_HIDE_ROOT | wx.TR_SINGLE |
                                wx.TR_FULL_ROW_HIGHLIGHT)

        self.STYLE_HEAD = wx.TextAttr(font=wx.Font(14, wx.FONTFAMILY_DEFAULT,
                                                   wx.FONTSTYLE_NORMAL,
                                                   wx.FONTWEIGHT_BOLD))
        self.STYLE_NORMAL = wx.TextAttr(font=wx.Font(10, wx.FONTFAMILY_DEFAULT,
                                                     wx.FONTSTYLE_NORMAL,
                                                     wx.FONTWEIGHT_NORMAL))
        self.STYLE_BOLD = wx.TextAttr(font=wx.Font(10, wx.FONTFAMILY_DEFAULT,
                                                   wx.FONTSTYLE_NORMAL,
                                                   wx.FONTWEIGHT_BOLD))
        self.STYLE_ITALIC = wx.TextAttr(font=wx.Font(10, wx.FONTFAMILY_DEFAULT,
                                                     wx.FONTSTYLE_ITALIC,
                                                     wx.FONTWEIGHT_NORMAL))

        self.tree.AddRoot(text='root')
        self.init_info()

        self.textw = TextUrlCtrl(self, value='', style=wx.TE_MULTILINE |
                                            wx.TE_READONLY | wx.TE_DONTWRAP)

        self.SplitVertically(self.tree, self.textw)

        # Prevent the window from unsplitting when dragging the sash to the
        # border
        self.SetMinimumPaneSize(20)
        self.SetSashPosition(120)

        self.Bind(wx.EVT_SPLITTER_DCLICK, self.veto_dclick)
        self.tree.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.veto_label_edit)
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.retrieve_info)

        self.tree.SelectItem(self.tree.GetFirstChild(self.tree.GetRootItem())[0
                                                                             ])

    def init_info(self):
        self.tree.AppendItem(self.tree.GetRootItem(), text='License',
                             data=wx.TreeItemData({'req': 'lic'}))

        self.tree.AppendItem(self.tree.GetRootItem(), text='Info',
                             data=wx.TreeItemData({'req': 'cor'}))

        # Do not use the configuration because it could have entries about
        # addons that aren't actually installed
        addons = coreaux_api.get_components_info()["addons"]

        for type_ in ('Extensions', 'Interfaces', 'Plugins'):
            typeitem = self.tree.AppendItem(self.tree.GetRootItem(),
                        text=type_,
                        data=wx.TreeItemData({'req': 'lst', 'type_': type_}))
            for addon in addons[type_]:
                self.tree.AppendItem(typeitem, text=addon,
                            data=wx.TreeItemData(
                            {'req': 'inf', 'type_': type_, 'addon': addon}))

    def compose_license(self):
        self.textw.AppendText(coreaux_api.get_license())

    def compose_main_info(self):
        coreinfo = coreaux_api.get_core_info()

        self.textw.SetDefaultStyle(self.STYLE_BOLD)
        self.textw.AppendText('Core version: ')
        self.textw.SetDefaultStyle(self.STYLE_NORMAL)
        self.textw.AppendText(coreinfo.version)

        self.textw.SetDefaultStyle(self.STYLE_BOLD)
        self.textw.AppendText('\nWebsite: ')
        self.textw.SetDefaultStyle(self.STYLE_NORMAL)
        self.textw.AppendText(coreinfo.website)

        self.textw.SetDefaultStyle(self.STYLE_BOLD)
        self.textw.AppendText('\nAuthor: ')
        self.textw.SetDefaultStyle(self.STYLE_NORMAL)
        self.textw.AppendText('Dario Giovannetti <dev@dariogiovannetti.net>')

        self.textw.SetDefaultStyle(self.STYLE_BOLD)
        self.textw.AppendText('\nContributors: ')
        self.textw.SetDefaultStyle(self.STYLE_NORMAL)

        try:
            contributors = coreinfo.contributors
        except AttributeError:
            pass
        else:
            for c in contributors:
                self.textw.AppendText('\n\t{}'.format(c))

        self.textw.SetDefaultStyle(self.STYLE_BOLD)
        self.textw.AppendText('\n\nInstalled components:')
        self.textw.SetDefaultStyle(self.STYLE_NORMAL)
        cinfo = coreaux_api.get_components_info()["info"]
        for cname in cinfo:
            self.textw.AppendText('\n\t{} {} ({})'.format(cname,
                            cinfo[cname].version, cinfo[cname].release_date))

    def compose_addon_info(self, type_, addon):
        info = {
            "Extensions": coreaux_api.import_extension_info,
            "Interfaces": coreaux_api.import_interface_info,
            "Plugins": coreaux_api.import_plugin_info,
        }[type_](addon)

        config = coreaux_api.get_configuration()(type_)(addon)

        self.textw.SetDefaultStyle(self.STYLE_HEAD)
        self.textw.AppendText('{}\n'.format(addon))

        self.textw.SetDefaultStyle(self.STYLE_NORMAL)

        self.textw.AppendText('{}\n'.format(info.description))

        self.textw.SetDefaultStyle(self.STYLE_BOLD)
        self.textw.AppendText('\nEnabled: ')
        self.textw.SetDefaultStyle(self.STYLE_NORMAL)
        self.textw.AppendText('yes' if config.get_bool('enabled') else 'no')

        self.textw.SetDefaultStyle(self.STYLE_BOLD)
        self.textw.AppendText('\nVersion: ')
        self.textw.SetDefaultStyle(self.STYLE_NORMAL)
        self.textw.AppendText(info.version)

        self.textw.SetDefaultStyle(self.STYLE_BOLD)
        self.textw.AppendText('\nWebsite: ')
        self.textw.SetDefaultStyle(self.STYLE_NORMAL)
        self.textw.AppendText(info.website)

        self.textw.SetDefaultStyle(self.STYLE_BOLD)

        if len(info.authors) > 1:
            self.textw.AppendText('\nAuthors:')
            self.textw.SetDefaultStyle(self.STYLE_NORMAL)

            for a in info.authors:
                self.textw.AppendText('\n\t{}'.format(a))
        else:
            self.textw.AppendText('\nAuthor: ')
            self.textw.SetDefaultStyle(self.STYLE_NORMAL)
            self.textw.AppendText(info.authors[0])

        self.textw.SetDefaultStyle(self.STYLE_BOLD)
        self.textw.AppendText('\nContributors:')
        self.textw.SetDefaultStyle(self.STYLE_NORMAL)

        try:
            contributors = info.contributors
        except AttributeError:
            pass
        else:
            for c in contributors:
                self.textw.AppendText('\n\t{}'.format(c))

        self.textw.SetDefaultStyle(self.STYLE_BOLD)
        self.textw.AppendText('\nComponent: ')
        self.textw.SetDefaultStyle(self.STYLE_NORMAL)
        cinfo = coreaux_api.get_components_info()
        cname = cinfo["addons"][type_][addon]
        component = cinfo["info"][cname]
        self.textw.AppendText('{} {} ({})'.format(cname, component.version,
                                                    component.release_date))

        self.textw.SetDefaultStyle(self.STYLE_BOLD)
        self.textw.AppendText('\nDependencies:')
        self.textw.SetDefaultStyle(self.STYLE_NORMAL)

        try:
            deps = info.dependencies
        except AttributeError:
            pass
        else:
            for d in deps:
                self.textw.AppendText('\n\t{} {}.x'.format(*d))

        self.textw.SetDefaultStyle(self.STYLE_BOLD)
        self.textw.AppendText('\nOptional dependencies:')
        self.textw.SetDefaultStyle(self.STYLE_NORMAL)

        try:
            opts = info.optional_dependencies
        except AttributeError:
            pass
        else:
            for o in opts:
                self.textw.AppendText('\n\t{} {}.x'.format(*o))

    def compose_list(self, type_):
        # Do not use the configuration because it could have entries about
        # addons that aren't actually installed
        info = coreaux_api.get_components_info()["addons"]
        self.textw.SetDefaultStyle(self.STYLE_BOLD)
        self.textw.AppendText('{}:\n'.format(type_))

        for addon in info[type_]:
            config = coreaux_api.get_configuration()(type_)(addon)

            if config.get_bool('enabled'):
                self.textw.SetDefaultStyle(self.STYLE_NORMAL)
                self.textw.AppendText('\t{}\n'.format(addon))
            else:
                self.textw.SetDefaultStyle(self.STYLE_ITALIC)
                self.textw.AppendText('\t{} [disabled]\n'.format(addon))

    def veto_dclick(self, event):
        event.Veto()

    def veto_label_edit(self, event):
        event.Veto()

    def retrieve_info(self, event):
        self.textw.Clear()
        self.textw.SetDefaultStyle(self.STYLE_NORMAL)
        data = self.tree.GetPyData(event.GetItem())
        if data['req'] == 'lic':
            self.compose_license()
        elif data['req'] == 'cor':
            self.compose_main_info()
        elif data['req'] == 'lst':
            self.compose_list(data['type_'])
        elif data['req'] == 'inf':
            self.compose_addon_info(data['type_'], data['addon'])
        # Scroll back to top
        self.textw.ShowPosition(0)
