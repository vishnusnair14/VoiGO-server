# converters.py

class FloatConverter:
    regex = '[+-]?\d+(?:\.\d+)?'

    def to_python(self, value):
        return float(value)

    def to_url(self, value):
        return str(value)
