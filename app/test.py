import os

font_path = os.path.join(os.path.dirname(__file__), 'static/fonts/DejaVuSans.ttf')
print(os.path.exists(font_path))  # Должно вернуть True
