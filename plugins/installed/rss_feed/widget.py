"""
Heise RSS Feed Dashboard Widget.

Displays latest news from heise.de RSS feed.
"""

import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
from datetime import datetime
from django.core.cache import cache
from plugins.widgets import DashboardWidgetProvider
import logging

logger = logging.getLogger(__name__)


class RssFeedWidgetProvider(DashboardWidgetProvider):
    """Dashboard widget showing heise.de RSS feed."""

    widget_id = "rss_feed_widget"
    widget_name = "Heise News"
    widget_icon = "bi-rss"
    widget_size = "medium"
    widget_order = 25

    RSS_URL = "https://www.heise.de/rss/heise-atom.xml"
    CACHE_KEY = "heise_rss_feed"
    CACHE_TIMEOUT = 300  # 5 minutes

    def fetch_feed(self) -> List[Dict[str, str]]:
        """Fetch and parse RSS feed from heise.de."""
        # Try to get from cache first
        cached = cache.get(self.CACHE_KEY)
        if cached:
            return cached

        items = []
        try:
            # Fetch RSS feed
            req = urllib.request.Request(
                self.RSS_URL,
                headers={'User-Agent': 'CloudService RSS Reader/1.0'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                xml_data = response.read()

            # Parse XML
            root = ET.fromstring(xml_data)

            # Handle Atom feed namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            # Find entries (Atom format)
            for entry in root.findall('.//atom:entry', ns)[:5]:
                title_elem = entry.find('atom:title', ns)
                link_elem = entry.find('atom:link', ns)
                updated_elem = entry.find('atom:updated', ns)
                summary_elem = entry.find('atom:summary', ns)

                if title_elem is not None:
                    # Get link href attribute
                    link = ''
                    if link_elem is not None:
                        link = link_elem.get('href', '')

                    # Parse date
                    date_str = ''
                    if updated_elem is not None and updated_elem.text:
                        try:
                            dt = datetime.fromisoformat(updated_elem.text.replace('Z', '+00:00'))
                            date_str = dt.strftime('%d.%m. %H:%M')
                        except:
                            date_str = ''

                    # Get summary
                    summary = ''
                    if summary_elem is not None and summary_elem.text:
                        summary = summary_elem.text[:100] + '...' if len(summary_elem.text) > 100 else summary_elem.text

                    items.append({
                        'title': title_elem.text or 'Kein Titel',
                        'link': link,
                        'date': date_str,
                        'summary': summary,
                    })

            # Cache the results
            if items:
                cache.set(self.CACHE_KEY, items, self.CACHE_TIMEOUT)

        except Exception as e:
            logger.error(f"Failed to fetch RSS feed: {e}")
            # Return fallback items
            items = [
                {
                    'title': 'Feed konnte nicht geladen werden',
                    'link': 'https://www.heise.de',
                    'date': '',
                    'summary': str(e),
                }
            ]

        return items

    def get_context(self, request) -> Dict[str, Any]:
        """Get RSS feed data for the widget."""
        items = self.fetch_feed()

        return {
            'items': items,
            'feed_url': 'https://www.heise.de',
            'feed_name': 'heise online',
            'updated': datetime.now().strftime('%H:%M'),
        }

    def get_template_name(self) -> str:
        return 'rss_feed/widget.html'
