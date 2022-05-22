from datetime import datetime
from distutils.command.config import config
import time
from collections import defaultdict, deque
from accessory import get_config
import os
import RPi.GPIO as GPIO


message_di = defaultdict(int)
config = get_config()


def messager(name, message, digit):
    if digit > 0:
        if message_di[message] == 0 :
            message_di[message] +=1
            print(f'{datetime.now()} {name} {message}')

        else:
            print(f'это тестовый блок else \n {name} {message}')
    else:
        if message_di[message] == 1 :
            message_di[message] -=1
            print(f'{datetime.now()} {name} {message}')
        else:
            print(f'это тестовый блок else \n {name} {message}')

class Thermocupe():
    def __init__(self, name):
        self.values = deque(maxlen=2)
        self.is_active = True
        self.name = name
        self.full_path = os.path.join(config['socket_path'], self.name, 'w1_slave')

    def get_temperature(self):
        with open(self.full_path, 'r') as file:
            res = file.readlines()
        print('path res')
        print(self.full_path)
        print(res)
        if res:
            if 'YES\n' in res[0]:
                time.sleep(0.2)
                equals_pos = res[1].find('t=')
                if equals_pos != -1:
                    temp_string = res[1][equals_pos+2:]
                    temp_c = float(temp_string) / 1000.0
                    self.values.append(temp_c)
                    return temp_c
                else:
                    messager(self.name, 'не найдена позиция температуры', -1)
            else:
                    messager(self.name, 'ошибка чтения файла(не YES)', -1)
        else:
            messager(self.name, 'не удалось прочитать файл', -1)

    def check(self):

        if not any(self.values):
            messager(self.name, 'два значения None', -1)
            self.is_active = False
        else:
            self.check_delta()

    def get_delta(self):
        return abs(self.values[0] - self.values[1])

    def check_delta(self):
        delta = self.get_delta()
        if delta > config['max_delta']:
            messager(self.name, 'перепад температуры больше максимального разового отключение термопары', -1)
            self.is_active = False
        else:
            self.is_active = True
            print(f'{self.name} перепад в норме {delta} - посравнивать между собой')

class Main():
    def __init__(self):
        self.therm_1 = Thermocupe(config['t1_name'])
        self.therm_2 = Thermocupe(config['t2_name'])
        self.virtual_t = None
        self.temp_t = None
        GPIO.setmode(GPIO.BCM)

    def run(self):
        test_count = 0
        self.therm_1.get_temperature()
        self.therm_2.get_temperature()
        while test_count<5:
            test_count += 1
            time.sleep(1)
            t = self.calculate_t()
            print(f'итоговая температура {t}')
            if not self.temp_t:
                if t >= config['heat']: # начинать охлаждение
                    self.temp_t = config['cold'] + 1
                    self.gpio_control(config['cold_pin'])

                elif t <= config['cold']: # начинать нагрев
                    self.temp_t = config['heat'] - 1
                    self.gpio_control(config['heart_pin'])

            elif self.temp_t:
                if self.temp_t <= t:  # закончить охлаждение
                    self.temp_t = None
                    self.gpio_control(config['cold_pin'], False)

                if self.temp_t >= t:  # закончить нагрев
                    self.temp_t = None
                    self.gpio_control(config['heart_pin'], False)


    def gpio_control(self, pin, is_start=True):
        print(f'use pin: {pin}')
        if is_start:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
        else:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)




    def calculate_t(self):
        t1 = self.therm_1.get_temperature()
        t2 = self.therm_2.get_temperature()
        print(f'полученные температуры t1 {t1} t2 {t2}')
        self.therm_1.check()
        self.therm_2.check()
        if self.therm_1.is_active and self.therm_2.is_active:
            t1 = self.therm_1.values[1]
            t2 = self.therm_2.values[1]
            if abs(self.virtual_t - t2) > float(config['max_delta']): # отказ t2
                self.virtual_t = t1
            elif abs(self.virtual_t - t1) > float(config['max_delta']): # отказ t2
                self.virtual_t = t2
            else:

                self.virtual_t = (t1 + t2) / 2
        elif self.therm_1.is_active:
            self.virtual_t = t1
        elif self.therm_2.is_active:
            self.virtual_t = t2
        return self.virtual_t


if __name__ == '__main__':
    m = Main()
    m.run()
