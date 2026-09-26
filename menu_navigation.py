class MenuNavigation:
    """Own one menu and ignore completion callbacks from replaced menus."""

    def __init__(self, set_depth):
        self.current = None
        self._cleanup = None
        self._back = None
        self._set_depth = set_depth

    def open(self, menu, cleanup, back):
        if self.current is menu:
            return
        self.close()
        self.current = menu
        self._cleanup = cleanup
        self._back = back
        self._set_depth(True)

    def close(self):
        if self.current is None:
            return
        cleanup = self._cleanup
        self.current = self._cleanup = self._back = None
        cleanup()
        self._set_depth(False)

    def release(self, menu):
        if self.current is menu:
            self.close()

    def back(self):
        if self.current is None:
            return False
        self._back()
        return True
