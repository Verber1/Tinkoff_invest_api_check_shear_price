from pandas import DataFrame
from datetime import datetime, timezone

from tinkoff.invest import Client, InstrumentIdType, InstrumentStatus, CandleInterval
from tinkoff.invest.utils import decimal_to_quotation, quotation_to_decimal

import pandas as pd
import time

"""
https://tinkoff.github.io/invest-python/
https://tinkoff.github.io/investAPI/            # Описание методов и руководство
https://tinkoff.github.io/investAPI/errors/     # Коды ошибок
https://tinkoff.github.io/investAPI/marketdata/ # Просмотр котировок

https://github.com/AzzraelCode/api_v2_tinvest   # Туториалы
"""

# Считываем токен из файла
def read_token(file_name):
    f = open(file_name, 'r')
    line = f.readline()
    #with open(file_name) as file:
        #line = file.readline()
    return line

# Вернуть время в отформатированном формате в виде ДД:ММ:ГГ ЧЧ-ММ-СС (для текущего часового пояса)
def get_formatting_time(time):
    # Перевод в местное время
    formatting_time = time.replace(tzinfo=timezone.utc).astimezone(tz=None)
    # Задаём свой формат времени
    formatting_time = datetime.strftime(formatting_time, '%d-%m-%Y %H:%M:%S')
    return formatting_time


'''
Вернуть датафрейм с текущими ценами акций в виде:
    --FIGI акции
    --Тикер акции
    --Название акции (полное)
    --Время совершения сделки (используя свой формат времени)
    --Стоимость акции (нормальный формат)
'''
def get_data_frame_current_price_shares(client, shares):
    # Выносим FIGI акций в отдельный список, так как он нужен для полученя стоимости акций
    figi_list = [share.figi for share in shares]
    # print(figi_list)

    # Получаем текущую стоимость по всем акциям
    price_shares = client.market_data.get_last_prices(figi=figi_list)
    #print(price_shares.last_prices)

    # Проверяем, что размер списка стоимости акций совпадает с количеством акций
    if len(figi_list) != len(price_shares.last_prices):
        print("Warning! Size lists don't equal!")

    # Приводим стоимость акций и время их покупки к нормальному (человеческому) виду
    for share in price_shares.last_prices:
        share.price = quotation_to_decimal(share.price)
        share.time = get_formatting_time(share.time)

    # Создаем датафрейм
    # PS: Так как я не знаю, как сделать датафрейм из двух списков с отдельными атрибутами,
    # то создаю 2 датафрейма и объединяю их в один датафрейм
    shares_data_frame = DataFrame(shares, columns=['figi', 'ticker', 'name'])
    time_and_price_shares_data_frame = DataFrame(price_shares.last_prices, columns=['time', 'price'])
    price_shares_data_frame = pd.concat([shares_data_frame, time_and_price_shares_data_frame], axis=1, join='inner')

    # Выводим датаферйм в полном виде(без сокращений).
    # to_string() можно использовать только, если объем данных меньше 1кк строк
    #print(price_shares_data_frame.to_string())

    # Возвращаем датафрейм с текущими стоимостями акций
    return price_shares_data_frame

# Получить текущую стоимость акций и заполнить список history_price_shares
def get_init_price_history(client, shares):
    # Получаем датафрейм с текущими стоимостями акций
    current_price_shares = get_data_frame_current_price_shares(client, shares)

    # Заполняем список датафреймов с прошлыми стоимостями акций текущими значениями
    # в качестве начальных значений
    '''
    [0] - стоимость акций 5 минут назад
    [1] - стоимость акций 4 минуты назад
    [2] - стоимость акций 3 минуты назад
    [3] - стоимость акций 2 минуты назад
    [4] - стоимость акций 1 минуту назад
    [5] - текущая стоимость акций
    '''
    history_price_shares = []
    for i in range(6):
        history_price_shares.append(current_price_shares)

    # Возвращаем список датафреймов с начальными значениями стоимости акций
    return history_price_shares

# Вывести информацию об изменении стоимости акции
def print_info_change_price(time_delta, percent_delta, price_curr, price_last):
    print(get_formatting_time(datetime.utcnow()), ": ", "Стоимость акции ", price_curr['name'],
          " за ", time_delta, " минут(у) увеличилась на ", format(percent_delta, '.2f'), "%. ",
          "Текущая (", price_curr['time'], ") стоимость составляет ",
          format(price_curr['price'], '.2f'), " руб.. ", "Стоимость акции ", time_delta, " минут(у) назад (",
          price_last['time'], ") составляла ",
          format(price_last['price'], '.2f'), " руб..", sep='')


# Проведение анализа стоимости акций и отображение акций, цена которых выросла
# относительно стоимости, что была получена одну минуту назад и 5 минут назад
def share_price_analysis(history_price_shares):
    # Процент, с которым сравниаем увеличение стоимости акции за 1 минуту
    standart_percent_1_min = 1.5
    # Процент, с которым сравниаем увеличение стоимости акции за 5 минут
    standart_percent_5_min = 3.

    ###########
    #max_1_min = -100.
    #max_5_min = -100.
    ###########

    # Определяем процент, на который произошло изменение стоимости акций
    for (index, price_5_min_ago), (index, price_1_min_ago), (index, price_curr) in \
            zip(history_price_shares[0].iterrows(), history_price_shares[4].iterrows(), history_price_shares[5].iterrows()):
        # Определяем изменение стоимости акции (в процентах) за одну минуту
        delta_percent_1_min = (price_curr['price'] - price_1_min_ago['price']) / price_1_min_ago['price'] * 100
        # Определяем изменение стоимости акции (в процентах) за пять минут
        delta_percent_5_min = (price_curr['price'] - price_5_min_ago['price']) / price_5_min_ago['price'] * 100

        ###########
        #max_1_min = max(max_1_min, delta_percent_1_min)
        #max_5_min = max(max_5_min, delta_percent_5_min)
        #print(price_curr['time'])
        ###########

        # Выводим информацию об акции, если по ней произошел рост за последнюю минуту
        if delta_percent_1_min >= standart_percent_1_min:
            '''
            print(get_formatting_time(datetime.utcnow()), ": ", "Стоимость акции ", price_curr['name'],
                  " за 1 минуту увеличилась на ", format(delta_percent_1_min, '.2f'), "%. ",
                  "Текущая (", price_curr['time'], ") стоимость составляет ",
                  format(price_curr['price'], '.2f'), " руб.. ", "Стоимость акции 1 минуту назад (",
                  price_1_min_ago['time'], ") составляла ",
                  format(price_1_min_ago['price'], '.2f'), " руб..", sep='')
            '''
            print_info_change_price(time_delta=1, percent_delta=delta_percent_1_min,
                                    price_curr=price_curr, price_last=price_1_min_ago)

        # Выводим информацию об акции, если по ней произошел рост за последние 5 минут
        if delta_percent_5_min >= standart_percent_5_min:
            '''
            print(get_formatting_time(datetime.utcnow()), ": ", "Стоимость акции ", price_curr['name'],
                  " за 5 минут увеличилась на ", format(delta_percent_5_min, '.2f'), "%. ",
                  "Текущая (", price_curr['time'], ") стоимость составляет ",
                  format(price_curr['price'], '.2f'), " руб.. ", "Стоимость акции 5 минут назад (",
                  price_5_min_ago['time'], ") составляла ",
                  format(price_5_min_ago['price'], '.2f'), " руб..", sep='')
            '''
            print_info_change_price(time_delta=5, percent_delta=delta_percent_5_min,
                                    price_curr=price_curr, price_last=price_5_min_ago)

    ###########
    #print(get_formatting_time(datetime.utcnow()), ": max_1_min = ", max_1_min, "% max_5_min = ", max_5_min, "%.")
    ###########


# Запуск основной программы
def launch_work():
    token = read_token('token.txt')
    print("Токен считан!")
    with Client(token) as client:

        print("Начинаем анализ...")

        # Получить список всех акций в Тинькофф Инвестиции
        shares = client.instruments.shares()
        # print(shares)
        print('Число акций в Тинькофф Инвестиции:',  len(shares.instruments))

        # Будем работать только с MOEX акциями
        shares_moex = []
        for share in shares.instruments:
            if 'MOEX' in share.exchange:
                shares_moex.append(share)
        # print(shares_moex)
        print('Число акций MOEX в Тинькофф Инвестиции:', len(shares_moex))

        # Получаем список датафреймов с начальными значениями стоимости акций
        '''
        [0] - стоимость акций 5 минут назад
        [1] - стоимость акций 4 минуты назад
        [2] - стоимость акций 3 минуты назад
        [3] - стоимость акций 2 минуты назад
        [4] - стоимость акций 1 минуту назад
        [5] - текущая стоимость акций
        '''
        history_price_shares = get_init_price_history(client=client, shares=shares_moex)

        while True:

            # Получаем текущую стоимость акций
            current_price_shares = get_data_frame_current_price_shares(client=client, shares=shares_moex)

            # Удаляем датафрейм со стоимостями акций, который был получен 5 минут назад,
            # так как с того момента прошло уже 6 минут
            del history_price_shares[0]

            # Добавляем в список датафреймов текущую стоимость акций
            history_price_shares.append(current_price_shares)

            # Проводим анализ стоимости акций и отображаем акции, цена которых выросла
            # относительно стоимости, что была получена одну минуту назад и 5 минут назад
            share_price_analysis(history_price_shares)

            #break

            # Функция будет выполняться каждые 60 секунд
            time.sleep(60)


#if __name__ == '__main__':
#   launch_work()

