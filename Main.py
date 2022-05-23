from datetime import datetime
from distutils.command.config import config
import time
from collections import defaultdict, deque
from accessory import get_config
import os
import RPi.GPIO as GPIO
GPIO.setwarnings(False)
GPIO.cleanup()

config = get_config()



    

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
                    print(self.name, ' не найдена позиция температуры')
            else:
                    print(self.name, ' ошибка чтения файла(не YES)')
        else:
            print(self.name, ' не удалось прочитать файл')

    def check(self):

        if not any(self.values):
            print(self.name, ' два значения None')
            self.is_active = False
        else:
            self.check_delta()

    def get_delta(self):
        return abs(self.values[0] - self.values[1])

    def check_delta(self):
        delta = self.get_delta()
        if delta > float(config['max_delta']):
            print(self.name, ' перепад температуры больше максимального разового отключение термопары')
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
            time.sleep(2)
            t = self.calculate_t()
            if self.t_cool and self.t_heart: 
                print('запрет ложного срабатывания одновременного нагрева и охлаждения')
                self.t_cool = None
                self.t_heart = None
                self.gpio_control(config['cold_pin'], False)
                self.gpio_control(config['heart_pin'], False)

            
            if self.t_cool:
                if self.t_cool >= t:  # закончить охлаждение
                    print(f'{datetime.now()} cooling off')
                    self.t_cool = None
                    self.gpio_control(config['cold_pin'], False)

            elif self.t_heart:
                if self.t_heart <= t:  # закончить нагрев
                    print(f'{datetime.now()} heart off')
                    self.t_heart = None
                    self.gpio_control(config['heart_pin'], False)
            
            elif t >= float(config['heat']) and not self.t_cool:
                print(f'{datetime.now()} coold on')
                self.t_cool = float(config['cold']) + 1.0
                self.gpio_control(config['cold_pin'])

            elif t <= float(config['cold']) and not self.t_heart: # начинать нагрев
                print(f'{datetime.now()} heart on')
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

