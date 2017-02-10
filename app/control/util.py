import logging


def setup_logging(file='validacija.log', level=logging.INFO, mode='w'):
    """Inicijalizacija loggera"""
    try:
        logging.basicConfig(level=level,
                            filename=file,
                            filemode=mode,
                            format='{levelname}:::{asctime}:::{module}:::{funcName}:::LOC:{lineno}:::{message}',
                            style='{')
    except Exception as err:
        print('Pogreska prilikom konfiguracije loggera.')
        print(str(err))
        raise SystemExit('Kriticna greska, izlaz iz aplikacije.')
