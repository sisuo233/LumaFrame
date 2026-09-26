import unittest

from menu_navigation import MenuNavigation


class MenuNavigationTests(unittest.TestCase):
    def test_old_completion_cannot_close_replacement(self):
        depth, closed = [], []
        menus = MenuNavigation(depth.append)
        menus.open("camera", lambda: closed.append("camera"), lambda: None)
        menus.open("border", lambda: closed.append("border"), lambda: None)
        menus.release("camera")
        self.assertEqual(menus.current, "border")
        self.assertEqual(closed, ["camera"])
        self.assertTrue(depth[-1])

    def test_close_is_idempotent_even_with_dismiss_callback(self):
        closed = []
        menus = MenuNavigation(lambda value: None)

        def cleanup():
            closed.append(True)
            menus.release("popup")

        menus.open("popup", cleanup, menus.close)
        self.assertTrue(menus.back())
        self.assertFalse(menus.back())
        menus.close()
        self.assertEqual(closed, [True])

    def test_back_can_navigate_to_parent(self):
        menus = MenuNavigation(lambda value: None)
        menus.open("group", lambda: None,
                   lambda: menus.open("categories", lambda: None, menus.close))
        menus.back()
        self.assertEqual(menus.current, "categories")
