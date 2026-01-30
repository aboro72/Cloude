"""
Clock preview provider handler.

Displays an animated analog clock in the file preview.
Great for testing the plugin system - you can immediately see it working!
"""

from plugins.preview import FilePreviewProvider
import logging

logger = logging.getLogger(__name__)


class ClockPreviewProvider(FilePreviewProvider):
    """
    Provides an animated analog clock preview.

    Perfect for testing plugins - shows animated clock with moving hands.
    """

    @property
    def supported_mime_types(self):
        """MIME types supported by this provider"""
        return ['application/clock', 'text/clock']

    def can_preview(self, file_obj) -> bool:
        """Check if this provider can preview the given file"""
        return file_obj.mime_type in self.supported_mime_types

    def get_preview_html(self, file_obj) -> str:
        """
        Generate HTML for animated clock preview.

        Returns beautiful analog clock that updates in real-time.
        """
        try:
            logger.info(f"Generating clock preview for {file_obj.name}")

            html = '''
            <div class="clock-container">
                <style>
                    .clock-container {
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        padding: 40px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        border-radius: 10px;
                        min-height: 400px;
                    }

                    .clock {
                        width: 300px;
                        height: 300px;
                        border: 8px solid white;
                        border-radius: 50%;
                        position: relative;
                        background: white;
                        box-shadow: 0 0 30px rgba(0, 0, 0, 0.3), inset 0 0 20px rgba(0, 0, 0, 0.1);
                    }

                    .clock::before {
                        content: '';
                        position: absolute;
                        width: 15px;
                        height: 15px;
                        background: #333;
                        border-radius: 50%;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                        z-index: 10;
                    }

                    .hand {
                        position: absolute;
                        bottom: 50%;
                        left: 50%;
                        transform-origin: bottom center;
                        background: #333;
                        border-radius: 10px;
                    }

                    .hour-hand {
                        width: 6px;
                        height: 80px;
                        margin-left: -3px;
                        background: #333;
                    }

                    .minute-hand {
                        width: 4px;
                        height: 110px;
                        margin-left: -2px;
                        background: #555;
                    }

                    .second-hand {
                        width: 2px;
                        height: 120px;
                        margin-left: -1px;
                        background: #e74c3c;
                    }

                    .number {
                        position: absolute;
                        width: 100%;
                        height: 100%;
                        text-align: center;
                        font-size: 20px;
                        font-weight: bold;
                        color: #333;
                    }

                    .number span {
                        display: inline-block;
                        position: absolute;
                        left: 50%;
                        transform-origin: 0 150px;
                        transform: translateX(-50%);
                    }

                    .digital-time {
                        margin-top: 30px;
                        text-align: center;
                        font-size: 24px;
                        color: white;
                        font-family: 'Courier New', monospace;
                        font-weight: bold;
                        letter-spacing: 2px;
                    }

                    .clock-info {
                        margin-top: 20px;
                        text-align: center;
                        color: rgba(255, 255, 255, 0.8);
                        font-size: 14px;
                    }

                    @media (prefers-reduced-motion: reduce) {
                        .hour-hand, .minute-hand, .second-hand {
                            transition: transform 0.5s;
                        }
                    }
                </style>

                <div style="text-align: center;">
                    <div class="clock">
                        <div class="number" id="numbers"></div>
                        <div class="hand hour-hand" id="hour"></div>
                        <div class="hand minute-hand" id="minute"></div>
                        <div class="hand second-hand" id="second"></div>
                    </div>
                    <div class="digital-time" id="digital-time">00:00:00</div>
                    <div class="clock-info">
                        ⏰ CloudService Plugin System Test Clock
                    </div>
                </div>
            </div>

            <script>
                // Initialize clock numbers
                function initClockNumbers() {
                    const numbersDiv = document.getElementById('numbers');
                    for (let i = 1; i <= 12; i++) {
                        const span = document.createElement('span');
                        span.textContent = i;
                        span.style.transform = `rotate(${i * 30}deg)`;
                        numbersDiv.appendChild(span);
                    }
                }

                // Update clock hands
                function updateClock() {
                    const now = new Date();

                    const seconds = now.getSeconds();
                    const minutes = now.getMinutes();
                    const hours = now.getHours() % 12;

                    const secondDeg = (seconds / 60) * 360;
                    const minuteDeg = (minutes / 60) * 360 + (seconds / 60) * 6;
                    const hourDeg = (hours / 12) * 360 + (minutes / 60) * 30;

                    document.getElementById('second').style.transform = `rotate(${secondDeg}deg)`;
                    document.getElementById('minute').style.transform = `rotate(${minuteDeg}deg)`;
                    document.getElementById('hour').style.transform = `rotate(${hourDeg}deg)`;

                    // Update digital time
                    const hoursStr = String(now.getHours()).padStart(2, '0');
                    const minutesStr = String(now.getMinutes()).padStart(2, '0');
                    const secondsStr = String(now.getSeconds()).padStart(2, '0');
                    document.getElementById('digital-time').textContent =
                        `${hoursStr}:${minutesStr}:${secondsStr}`;
                }

                // Initialize and start clock
                function startClock() {
                    initClockNumbers();
                    updateClock();
                    setInterval(updateClock, 1000);
                }

                // Start when page is loaded
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', startClock);
                } else {
                    startClock();
                }
            </script>
            '''

            logger.info(f"Clock preview generated successfully for {file_obj.name}")
            return html

        except Exception as e:
            logger.error(f"Failed to generate clock preview: {e}")
            raise
