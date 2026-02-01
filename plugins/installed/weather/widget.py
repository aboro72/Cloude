"""
Weather Dashboard Widget.

Displays current weather information using OpenWeatherMap API.
"""

import urllib.request
import json
from typing import Dict, Any
from datetime import datetime
from django.core.cache import cache
from plugins.widgets import DashboardWidgetProvider
import logging

logger = logging.getLogger(__name__)


class WeatherWidgetProvider(DashboardWidgetProvider):
    """Dashboard widget showing real weather information from OpenWeatherMap."""

    widget_id = "weather_widget"
    widget_name = "Wetter"
    widget_icon = "bi-cloud-sun"
    widget_size = "small"
    widget_order = 15

    CACHE_TIMEOUT = 600  # 10 minutes

    # Weather icon mapping (OpenWeatherMap icon codes to Bootstrap icons)
    ICON_MAP = {
        '01d': 'bi-sun',           # clear sky day
        '01n': 'bi-moon',          # clear sky night
        '02d': 'bi-cloud-sun',     # few clouds day
        '02n': 'bi-cloud-moon',    # few clouds night
        '03d': 'bi-cloud',         # scattered clouds
        '03n': 'bi-cloud',
        '04d': 'bi-clouds',        # broken clouds
        '04n': 'bi-clouds',
        '09d': 'bi-cloud-drizzle', # shower rain
        '09n': 'bi-cloud-drizzle',
        '10d': 'bi-cloud-rain',    # rain
        '10n': 'bi-cloud-rain',
        '11d': 'bi-cloud-lightning-rain',  # thunderstorm
        '11n': 'bi-cloud-lightning-rain',
        '13d': 'bi-cloud-snow',    # snow
        '13n': 'bi-cloud-snow',
        '50d': 'bi-cloud-haze',    # mist
        '50n': 'bi-cloud-haze',
    }

    def get_plugin_settings(self) -> Dict[str, Any]:
        """Get settings from the database."""
        try:
            from plugins.models import Plugin
            plugin = Plugin.objects.get(slug='weather')
            return plugin.settings
        except Exception as e:
            logger.error(f"Could not load weather settings: {e}")
            return {}

    def fetch_weather(self, api_key: str, city: str, units: str = 'metric', lang: str = 'de') -> Dict[str, Any]:
        """Fetch weather data from OpenWeatherMap API."""
        cache_key = f"weather_{city}_{units}"

        # Check cache first
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units={units}&lang={lang}"

            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'CloudService Weather Widget/1.0'}
            )

            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))

            weather_data = {
                'success': True,
                'temperature': round(data['main']['temp']),
                'feels_like': round(data['main']['feels_like']),
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'wind_speed': round(data['wind']['speed'] * 3.6),  # m/s to km/h
                'condition': data['weather'][0]['description'].capitalize(),
                'icon_code': data['weather'][0]['icon'],
                'city': data['name'],
                'country': data['sys']['country'],
                'sunrise': datetime.fromtimestamp(data['sys']['sunrise']).strftime('%H:%M'),
                'sunset': datetime.fromtimestamp(data['sys']['sunset']).strftime('%H:%M'),
            }

            # Cache the result
            cache.set(cache_key, weather_data, self.CACHE_TIMEOUT)

            return weather_data

        except urllib.error.HTTPError as e:
            if e.code == 401:
                return {'success': False, 'error': 'Ungültiger API-Key'}
            elif e.code == 404:
                return {'success': False, 'error': 'Stadt nicht gefunden'}
            else:
                return {'success': False, 'error': f'API Fehler: {e.code}'}
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return {'success': False, 'error': str(e)}

    def get_demo_weather(self, city: str) -> Dict[str, Any]:
        """Return demo weather data when API is not available."""
        import random
        from datetime import datetime

        # Use hour as seed for consistent demo data
        random.seed(datetime.now().hour)

        conditions = [
            ('Sonnig', '01d'),
            ('Teilweise bewölkt', '02d'),
            ('Bewölkt', '03d'),
            ('Leichter Regen', '10d'),
        ]
        condition, icon = random.choice(conditions)

        return {
            'success': True,
            'temperature': random.randint(5, 25),
            'feels_like': random.randint(3, 23),
            'humidity': random.randint(40, 80),
            'pressure': 1013,
            'wind_speed': random.randint(5, 30),
            'condition': condition,
            'icon_code': icon,
            'city': city,
            'country': 'DE',
            'sunrise': '07:30',
            'sunset': '17:45',
            'is_demo': True,
        }

    def get_context(self, request) -> Dict[str, Any]:
        """Get weather data for the widget."""
        settings = self.get_plugin_settings()

        api_key = settings.get('api_key', '')
        city = settings.get('city', 'Berlin')
        units = settings.get('units', 'metric')
        language = settings.get('language', 'de')

        # Check if API key is configured
        if not api_key:
            return {
                'configured': False,
                'error': 'Bitte API-Key in den Plugin-Einstellungen konfigurieren.',
            }

        # Fetch weather data
        weather = self.fetch_weather(api_key, city, units, language)

        # If API fails, use demo data
        if not weather.get('success'):
            weather = self.get_demo_weather(city)
            weather['api_error'] = True

        # Map icon code to Bootstrap icon
        icon = self.ICON_MAP.get(weather['icon_code'], 'bi-cloud')

        # Determine temperature color
        temp = weather['temperature']
        if temp < 0:
            temp_color = '#3498db'  # Cold - blue
        elif temp < 10:
            temp_color = '#1abc9c'  # Cool - teal
        elif temp < 20:
            temp_color = '#2ecc71'  # Mild - green
        elif temp < 30:
            temp_color = '#f39c12'  # Warm - orange
        else:
            temp_color = '#e74c3c'  # Hot - red

        unit_symbol = '°C' if units == 'metric' else '°F'

        return {
            'configured': True,
            'temperature': weather['temperature'],
            'feels_like': weather['feels_like'],
            'temp_color': temp_color,
            'unit': unit_symbol,
            'condition': weather['condition'],
            'icon': icon,
            'humidity': weather['humidity'],
            'wind_speed': weather['wind_speed'],
            'city': weather['city'],
            'country': weather['country'],
            'sunrise': weather['sunrise'],
            'sunset': weather['sunset'],
            'updated': datetime.now().strftime('%H:%M'),
            'is_demo': weather.get('is_demo', False),
            'api_error': weather.get('api_error', False),
        }

    def get_template_name(self) -> str:
        return 'weather/widget.html'
