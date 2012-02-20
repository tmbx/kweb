
class MenuList:
    def __init__(self):
        self._menu_items = []
        self._menus = {}

    def add_menu(self, menu):
        if not isinstance(menu, Menu):
            raise Exception("This is not a valid menu item: '%s'" % ( str(menu) ) )
        self._menu_items.append(menu)
        self._menus[menu.id] = menu

    def add_separator(self):
        self._menu_items.append(MenuSeparator())

    def _get_menu_items(self):
        return self._menu_items
    menu_items = property(_get_menu_items)

    def _get_menus(self):
        return self._menus
    menus = property(_get_menus)

class Menu:
    def __init__(self, id, label, url):
        self.id = id
        self.label = label
        self.url = url
        self.active = False
        self.enabled = True

    def __str__(self):
        return '<%s id="%s" label="%s" url="%s" active="%s" enabled="%s">' % \
            ( self.__class__.__name__, self.id, self.label, self.url, str(self.active), str(self.enabled) )

class MenuSeparator:
    pass


# Non-exhaustive tests
if __name__ == "__main__":
    ml = MenuList()
    ml.add_menu(Menu("status", "Status", "?page=status"))
    ml.add_menu(Menu("config", "Config", "?page=config"))
    ml.add_separator()
    ml.add_menu(Menu("blabla", "BlaBla", "?page=blabla"))
    ml.add_separator()
    ml.add_menu(Menu("about", "About", "?page=about"))

    ml.menus["blabla"].active = True
    ml.menus["about"].enabled = False

    for menu in ml.menu_items:
        print str(menu)



