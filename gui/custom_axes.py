"""
Vlastní osy pro PyQtGraph grafy
"""
import pyqtgraph as pg
from datetime import datetime


class TimeAxisItem(pg.AxisItem):
    """Custom axis pro zobrazení datetime"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enableAutoSIPrefix(False)

    def tickStrings(self, values, scale, spacing):
        """Převede timestamp na čitelný formát"""
        strings = []
        for v in values:
            try:
                dt = datetime.fromtimestamp(v)
                if spacing < 60:  # méně než minuta
                    s = dt.strftime('%H:%M:%S')
                elif spacing < 3600:  # méně než hodina
                    s = dt.strftime('%H:%M')
                elif spacing < 86400:  # méně než den
                    s = dt.strftime('%m-%d %H:%M')
                else:
                    s = dt.strftime('%Y-%m-%d')
                strings.append(s)
            except:
                strings.append('')
        return strings


class ScientificAxisItem(pg.AxisItem):
    """Custom axis pro vědeckou notaci"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enableAutoSIPrefix(False)

    def tickStrings(self, values, scale, spacing):
        """Zobraz čísla ve vědecké notaci"""
        return ['0' if v == 0 else f'{v:.2e}' for v in values]