from unittest import TestCase

import pandas

from app.control.adapteri import Adapter
from app.control.adapteri import MalformedJSONException


class TestAdapter(TestCase):

    def test__provjeri(self):
        a = Adapter()
        df = pandas.DataFrame(columns=(['a', 'b']))
        obavezni_stupci = ['a', 'b', 'c']
        self.assertRaises(MalformedJSONException, a._provjeri, df, obavezni_stupci)

    def test__provjeri2(self):
        a = Adapter()
        df = pandas.DataFrame(columns=(['a', 'b']))
        obavezni_stupci = ['a', 'b']
        self.assertTrue(a._provjeri(df, obavezni_stupci))

    def test__provjeri3(self):
        a = Adapter()
        df = pandas.DataFrame(columns=([]))
        obavezni_stupci = []
        self.assertTrue(a._provjeri(df, obavezni_stupci))

    def test__provjeri4(self):
        a = Adapter()
        df = pandas.DataFrame(columns=(['a', 'b']))
        obavezni_stupci = []
        self.assertTrue(a._provjeri(df, obavezni_stupci))

    def test__provjeri5(self):
        a = Adapter()
        df = pandas.DataFrame(columns=(['a', 'b']))
        obavezni_stupci = ['b']
        self.assertTrue(a._provjeri(df, obavezni_stupci))

    def test__provjeri6(self):
        a = Adapter()
        df = pandas.DataFrame(columns=([]))
        obavezni_stupci = ['b']
        self.assertRaises(MalformedJSONException, a._provjeri, df, obavezni_stupci)
