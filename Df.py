from pandas import DataFrame


class Df:
    def __init__(self, df: DataFrame, name: str, desc="Description"):
        self.name = name
        self.df = df
        self.desc = desc
