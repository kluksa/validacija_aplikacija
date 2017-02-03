from unittest import TestCase
from adapteri import Adapter


class TestAdapter(TestCase):

    def __init__(self):
        self.adapter = Adapter()

    def test__provjeri(self):
        self.assertRaises(Exception, self.adapter._provjeri,['ss','sd'],'rfrrf')

    def test__provjeri2(self):
        self.assertRaises(Exception, self.adapter._provjeri, [],'')


