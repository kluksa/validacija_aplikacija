class Exporter:
    """Ovo je apstraktna klasa koja definira kakvo sucelje za sve druge serijalizacije mora biti"""

    def spremi_neagregirane(self):
        raise NotImplemented

    def spremi_satne(self):
        raise NotImplemented


class CsvExporter(Exporter):
    """Konkretna klasa sa implementacijom serijalizatora"""

    def spremi_neagregirane(self):
        pass

    def spremi_satne(self):
        pass
