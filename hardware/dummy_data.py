import random

def get_pressure():
    get_random = round(random.uniform(1, 9), 1)
    pressure_random = float(f"{get_random}E-05")
    return pressure_random