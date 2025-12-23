import json
from datetime import datetime, timedelta

from PySide6.QtCore import QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QInputDialog, QSizePolicy

from db.core import connect_db
from db.settings import get_setting, set_setting #for weather 

#just some japan presets for now, add more (maybe capitals of some big countries all over the world)
CITY_PRESETS = {
    'Kyoto': (35.0116, 135.7681),
    'Osaka': (34.6937, 135.5023),
    'Tokyo': (35.6762, 139.6503),
    'Nagoya': (35.1815, 136.9066),
    'Kobe': (34.6901, 135.1955),
    'Custom…': None,
}


class WeatherWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.network = QNetworkAccessManager(self)

        self.last_fetch_utc = None
        self.cache_minutes = 45

        self.build_ui()
        self.load_location_from_settings()
        self.refresh(force=True)

    def build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        layout.addLayout(top_row)

        self.city_input = QComboBox()
        self.city_input.addItems(list(CITY_PRESETS.keys()))
        self.city_input.currentTextChanged.connect(self.on_city_changed)
        self.city_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        top_row.addWidget(self.city_input, 1)

        top_row.addStretch(0)

        self.big_label = QLabel('—')
        self.big_label.setStyleSheet('font-size: 30px; font-weight: 900;')
        layout.addWidget(self.big_label)

        self.small_label = QLabel('—')
        self.small_label.setStyleSheet('font-size: 16px; font-weight: 650; color: #666;')
        self.small_label.setWordWrap(True)
        layout.addWidget(self.small_label)

        layout.addStretch(1)

    def load_location_from_settings(self) -> None:
        connection = connect_db()

        saved_city = get_setting(connection, 'weather_city') or 'Kyoto'
        saved_lat = get_setting(connection, 'weather_lat')
        saved_lon = get_setting(connection, 'weather_lon')

        connection.close()

        if saved_city in CITY_PRESETS:
            self.city_input.blockSignals(True)
            self.city_input.setCurrentText(saved_city)
            self.city_input.blockSignals(False)

        #to keep lat/lon if saved, otherwise using default 
        if not saved_lat or not saved_lon:
            if saved_city in CITY_PRESETS and CITY_PRESETS[saved_city] is not None:
                lat, lon = CITY_PRESETS[saved_city]
                self.save_location_to_settings(saved_city, lat, lon)

    def save_location_to_settings(self, city: str, lat: float, lon: float) -> None:
        connection = connect_db()
        set_setting(connection, 'weather_city', city)
        set_setting(connection, 'weather_lat', str(lat))
        set_setting(connection, 'weather_lon', str(lon))
        connection.close()

    def on_city_changed(self, city: str) -> None:
        if city == 'Custom…':
            text, ok = QInputDialog.getText(
                self,
                'Custom location',
                'Enter lat,lon (e.g. 35.0116,135.7681):',
            )
            if not ok:
                self.load_location_from_settings()
                return

            try:
                parts = [p.strip() for p in text.split(',')]
                lat = float(parts[0])
                lon = float(parts[1])
            except Exception:
                self.small_label.setText('Invalid format. Use lat,lon (e.g. 35.0116,135.7681)')
                return

            self.save_location_to_settings('Custom…', lat, lon)
            self.refresh(force=True)
            return

        coords = CITY_PRESETS.get(city)
        if coords is None:
            return

        lat, lon = coords
        self.save_location_to_settings(city, lat, lon)
        self.refresh(force=True)

    #dont fetch in every refresh, interval defined in cache_minutes
    def should_fetch(self) -> bool:
        if self.last_fetch_utc is None:
            return True
        return (datetime.utcnow() - self.last_fetch_utc) > timedelta(minutes=self.cache_minutes)

    #force=True to bypass fetching interval 
    def refresh(self, force: bool = False) -> None:
        if not force and not self.should_fetch(): 
            return

        connection = connect_db()
        lat = get_setting(connection, 'weather_lat')
        lon = get_setting(connection, 'weather_lon')
        connection.close()

        if not lat or not lon:
            # defauly kyoto
            lat, lon = CITY_PRESETS['Kyoto']
            self.save_location_to_settings('Kyoto', lat, lon)

        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except Exception:
            lat_f, lon_f = CITY_PRESETS['Kyoto']
            self.save_location_to_settings('Kyoto', lat_f, lon_f)

        self.fetch_weather(lat_f, lon_f)

    #openmeteo api request here
    def fetch_weather(self, lat: float, lon: float) -> None:
        self.small_label.setText('Loading…')
        
        url = (
            'https://api.open-meteo.com/v1/forecast'
            f'?latitude={lat}&longitude={lon}'
            '&current=temperature_2m,weather_code'
            '&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max'
            '&timezone=auto'
        )

        request = QNetworkRequest(QUrl(url))
        reply = self.network.get(request)
        reply.finished.connect(lambda: self.on_reply_finished(reply))


    def on_reply_finished(self, reply) -> None:
        err = reply.error()

        raw = bytes(reply.readAll()).decode('utf-8', errors='replace')
        reply.deleteLater()

        #used err for debugging before but no it works so this is sufficient
        if err != QNetworkReply.NoError:
            self.small_label.setText(f'Weather fetch failed')
            return

        try:
            obj = json.loads(raw)

            current = obj.get('current', {})
            daily = obj.get('daily', {})

            current_temp = current.get('temperature_2m', None)
            code = current.get('weather_code', None)

            hi_list = daily.get('temperature_2m_max', [])
            lo_list = daily.get('temperature_2m_min', [])
            rain_list = daily.get('precipitation_probability_max', [])

            hi = hi_list[0] if len(hi_list) else None
            lo = lo_list[0] if len(lo_list) else None
            rain = rain_list[0] if len(rain_list) else None

            icon = self.weather_icon_for_code(int(code)) if code is not None else '🌡'

            hi_txt = f'{float(hi):.0f}°' if hi is not None else '—'
            lo_txt = f'{float(lo):.0f}°' if lo is not None else '—'
            rain_txt = f'{float(rain):.0f}%' if rain is not None else '—'

            self.big_label.setText(f'{icon}  {float(current_temp):.0f}°C')
            self.small_label.setText(f'H: {hi_txt}  L: {lo_txt}   Rain: {rain_txt}')

            self.last_fetch_utc = datetime.utcnow()

        except Exception as e:
            self.small_label.setText(f'Weather parse failed: {e}')

    #matched some of this by hand, maybe there is a better solution but this seems sufficient for now 
    def weather_icon_for_code(self, code: int) -> str:
        if code == 0:
            return '☀'
        if code in (1, 2):
            return '🌤'
        if code == 3:
            return '☁'
        if code in (45, 48):
            return '🌫'
        if code in (51, 53, 55, 56, 57):
            return '🌦'
        if code in (61, 63, 65, 66, 67):
            return '🌧'
        if code in (71, 73, 75, 77):
            return '🌨'
        if code in (80, 81, 82):
            return '🌧'
        if code in (85, 86):
            return '❄'
        if code in (95, 96, 99):
            return '⛈'
        return '🌡'
