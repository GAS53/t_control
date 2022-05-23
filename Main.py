from datetime import datetime
from distutils.command.config import config
import time
from collections import defaultdict, deque
from accessory import get_config
import os
import RPi.GPIO as GPIO
GPIO.setwarnings(False)
GPIO.cleanup()

message_di = defaultdict(int)
config = get_config()


def messager(name, message, digit):
    print(f'digit {digit} type {type(digit)}')
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
    print(message_di)

class Thermocupe():
    def __init__(self, name):
        self.values = deque(maxlen=2)
        self.is_active = True
        self.name = name
        self.full_path = os.path.join(config['socket_path'], self.name, 'w1_slave')

    def get_temperature(self):
        with open(self.full_path, 'r') as file:
            res = file.readlines()
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
        if delta > float(config['max_delta']):
            messager(self.name, 'перепад температуры больше максимального разового отключение термопары', -1)
            self.is_active = False
        else:
            self.is_active = True
            # print(f'{self.name} перeепад в норме {delta} - посравнивать между собой')

class Main():
    def __init__(self):
        self.therm_1 = Thermocupe(config['t1_name'])
        self.therm_2 = Thermocupe(config['t2_name'])
        self.virtual_t = None
        self.t_cool = None
        self.t_heart = None
        GPIO.setmode(GPIO.BCM)

    def run(self):
        self.therm_1.get_temperature()
        self.therm_2.get_temperature()
        while True:
            time.sleep(1)
            t = self.calculate_t()
            if self.t_cool and self.t_heart: 
                print('запрет ложного срабатывания одновременного нагрева и охлаждения')
                self.t_cool = None
                self.t_heart = None
                self.gpio_control(config['cold_pin'], False)
                self.gpio_control(config['heart_pin'], False)

            
            if self.t_cool:
                if self.t_cool >= t:  # закончить охлаждение
                    print('закончить охлаждение')
                    self.t_cool = None
                    self.gpio_control(config['cold_pin'], False)

            elif self.t_heart:
                if self.t_heart <= t:  # закончить нагрев
                    print('закончить нагрев')
                    self.t_heart = None
                    self.gpio_control(config['heart_pin'], False)
            
            elif t >= float(config['heat']) and not self.t_cool:
                print('начинать охлаждение')
                self.t_cool = float(config['cold']) + 1.0
                self.gpio_control(config['cold_pin'])

            elif t <= float(config['cold']) and not self.t_heart: # начинать нагрев
                print('начинать нагрев')
                self.t_heart = float(config['heat']) - 1.0
                self.gpio_control(config['heart_pin'])

            


    def gpio_control(self, pin, is_start=True):
        pin = int(pin)
        print(f'use pin: {pin}')
        if is_start:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
        else:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)




    def calculate_t(self):
        t1 = self.therm_1.get_temperature()
        t2 = self.therm_2.get_temperature()
        
        self.therm_1.check()
        self.therm_2.check()
        if self.virtual_t == None:
            self.virtual_t = (t1 + t2) / 2
        if self.therm_1.is_active and self.therm_2.is_active:
            t1 = self.therm_1.values[1]
            t2 = self.therm_2.values[1]
            # print(f't1 {self.therm_1.values} t2 {self.therm_2.values} температуры из после проверки')
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
        print(f't1 {t1} t2 {t2} result {self.virtual_t}')
        return self.virtual_t


if __name__ == '__main__':
    try:
        GPIO.setwarnings(False)
        GPIO.cleanup()
        m = Main()
        m.run()
    finally:
        GPIO.cleanup()

