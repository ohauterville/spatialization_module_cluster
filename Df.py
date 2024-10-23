from pandas import DataFrame


class Df:
    def __init__(self, df: DataFrame, name: str, year: str, lvl: int):
        self.name = name
        self.df = df
        self.year = year
        self.lvl = lvl
