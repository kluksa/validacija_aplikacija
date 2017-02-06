from unittest import TestCase
from app.control.rest_comm import MockZahtjev

class TestMockZahtjev(TestCase):


    def test_get_broj_u_satu(self):
        m = MockZahtjev()
        m.get_programe_mjerenja()

    def test_get_status_map(self):
        self.fail()

    def test_get_sirovi(self):
        m = MockZahtjev()
        m.get_sirovi('','2017-01-23')
        self.fail()

    def test_get_zero_span(self):
        self.fail()

    def test_get_programe_mjerenja(self):
        self.fail()
