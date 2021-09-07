"""Тестирование задержки пингов к заданному узлу сети и отрисовка временного и частотного распределения задержек."""

import matplotlib.pyplot as plt
import os
import sys
from datetime import datetime
from matplotlib.ticker import (MultipleLocator, IndexLocator)
from subprocess import Popen, PIPE

start_time = datetime.strftime(datetime.now(), "%Y.%m.%d %H:%M:%S")
timesec = int(datetime.strftime(datetime.now(), "%S"))
timemin = int(datetime.strftime(datetime.now(), "%M"))
timehour = int(datetime.strftime(datetime.now(), "%H"))
# qint определяет количество интервалов,
# на которые будут рассортированы пинги (11: 0 - 1, 1 - 4, 4 - 9 ... 81 - 100, >100, Lost)
qint = 11
# 9999 - риска на графике для пинга больше максимально заданного значения
intervals = [i * i for i in range(qint)] + [9999, 'Lost']


def pinger(request: str):
    """Генератор. Делает запрос к указанному узлу через системную утилиту ping и выдаёт полученные ответы"""

    counter = 0
    print(request)
    req = Popen(request, stdout=PIPE, shell=True)
    while True:
        line = req.stdout.readline().decode('cp866')
        if line:
            if 'Приблизительное' in line:  # Статистика
                line = req.stdout.readline().decode('cp866')[:-2]
                print(line)
                yield (counter, line,)
            if 'Превышен' in line:
                counter += 1
                print(counter, ': timeout')
                yield (counter, 'timeout',)
            # При необходимости добавить сюда обработку других сообщений
            pingtime = (line.partition('время')[2].partition('мс')[
                0])  # вытаскивает из ответа миллисекунды: "<1" - 1, "=2" - 2 и т.д.
            pingtime = ''.join(x for x in pingtime if x.isdigit())  # оставляет только цифры
            if pingtime != '':
                counter += 1
                print('{}: {} мс'.format(counter, pingtime))
                yield (counter, int(pingtime),)
        else:
            break


def lego(inputfile: str):  # lego (лат) - читать, собирать, говорить. Для построения графика по txt логам
    """Читает файл и выдаёт ответы вместо pinger()"""

    global start_time
    global timehour
    global timemin
    global timesec

    try:
        start_time = open(inputfile).readline().split('\t')[0]
        timehour, timemin, timesec = map(int, start_time.split()[1].split(':'))
    except:
        print('Не удалось получить время из файла')
    open(inputfile).close
    counter = 0
    print('reading {}...'.format(inputfile))
    with open(inputfile, 'r') as file:
        lines = iter(file.readlines())
        while True:
            try:
                val = next(lines).split('\t')
                val = val[1]
            except:
                break

            try:
                val = int(val)
                counter += 1
            except:
                if val == 'timeout\n':
                    val = 'timeout'
                    counter += 1
                elif 'мсек' in val:
                    break
            finally:
                yield (counter, val,)


def receptor(request, mode, location, comment):
    """получает ответы от pinger() или lego() и проводит необходимые действия над данными, чтобы передать их в pictura()
    {0, 1, 4, 9 ... 100, 9999, 'Lost', 'counter', 'request', 'mode', 'location', 'comment', 'statistics', 'pings'}"""

    answer = {i**2 : 0 for i in range(qint)}
    answer.update({'Lost': 0, 'counter':0, 'request': request, 'mode': mode, 'location': location, 'comment': comment,
                   'statistics': '', 'pings': []})
    pings = answer['pings']
    filename = '{} {} {}.png'.format(location, start_time.replace(':', '-'), comment)
    if mode in ('f'):
        report = open(filename.replace('png', 'txt'), 'w')
    if 'ping' in request:
        a = iter(pinger(request))
    elif '.txt' in request:
        a = iter(lego(request))
    try:  # try для KeyboardInterrupt
        while True:
            try:  # try для StopIteration
                nextans = next(a)
                counter = nextans[0] #
                answer['counter'] = nextans[0]
                value = nextans[1]
                if type(value) == str:
                    if value == 'timeout':
#                        output[-2] += 1 #
                        answer['Lost'] += 1
                        pings.append(0)
                    else:
#                        statistics = value
                        answer['statistics'] = value
                else:
                    for i in range(qint+1): # for qint = 11: i -> 0-11
                        if value <= intervals[i + 1]: # intervals: [0, 1, 4 ... 100, 9999, timeout]
#                            output[i] += 1 #
                            answer[i**2] += 1
                            pings.append(value)
                            break
                if mode in ('f'):
                    report.write(datetime.strftime(datetime.now(), "%Y.%m.%d %H:%M:%S") + '\t' + str(value) + '\n')
            except StopIteration:
                print(answer)
                break

    except KeyboardInterrupt:
        pass
    finally:
        if mode in ('f'):
            report.close()
        pictura(answer)


def pictura(data: dict):
    """Создаёт изображение по полученным от receptor() данным.
    На графике для отображения qint столбцов используются qint + 2 точек:
    1 доп. для задания краёв столбцов
    1 доп. для ещё одного интервала timeout"""

#    plt.ion()
    fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(15, 8))

    # График распределения по времени ответа
    # Абсциссы (координаты) рисок на шкале x графика распределений
    xticks = list(range(qint + 2))
    ax1.set_xticks(xticks)
    # Последний столбец в height всегда = 0 и нужен для соответствия len(heights) числу len(xticks)
    heights = [data[i] for i in intervals[:-2]] + [data['Lost'], 0]
    ax1.bar(xticks, heights, align='edge')  # Распределение пингов по временным интервалам
    # Список подписей под рисками на оси x
    x1_labels = intervals.copy()
    for x in range(qint+1):
        x1_labels[x] = '   {} мс\n             {}'.format(intervals[x], heights[x])
    ax1.set_xticklabels(x1_labels)
    ax1.set_ylabel('Количество ответов')
    if data['statistics']:
        fig.text(0.3, 0.8, data['comment'] + '\n' + data['statistics'])
    else:
        fig.text(0.3, 0.8, data['comment'])

    # Временной график задержек
    ax2.plot(range(data['counter']), data['pings'])
    # Красным обозначим потерянные пакеты
    for i, ping in enumerate(data['pings']):
        if ping == 0:
            ax2.scatter(i, -1, c='red', s=2)
    ax2.set_ylabel('Время ответа, мс')
    ax2.set_xlabel('Время')
    if data['counter'] > 99:
        x2ticks, marks, shift, minorbase = ticks_maker(data['counter'])
        ax2.set_xticks(x2ticks)
        ax2.set_xticklabels(marks)
        ax2.xaxis.set_minor_locator(IndexLocator(base=minorbase, offset=shift))
        ax2.tick_params(which='major', width=1.5)
    plt.title(f"{start_time}, расположение: {data['location']}\n{data['request']}\nОтправлено запросов: {data['counter']}",
              pad=250)  # pad=245, для нетбука 240
    plt.show()
    plt.pause(0.0001)
    filename = '{} {} {}.png'.format(data['location'], start_time.replace(':', '-'), data['comment'])
    if data['mode'] in ('l', 'f'):
        fig.savefig(filename)


def ticks_maker(counter: int):
    """Распределяет отметки времени на оси x
    Если пингов до 100 - проставить автоматом
    Если пингов >= 100 и < 601 - то большие чёрточки на минутных отметках, малые на каждые 20 сек
    Отметки времени на всех минутных тиках"""

    global timehour
    global timemin

    marks = []
    periods = {99: (60, 30), 1200: (120, 60), 2400: (300, 60), 7000: (600, 120), 15000: (900, 300), 30000: (1800, 300),
               43000: (3600, 600), 86000: (7200, 1200), 170000: (14400, 2400)}
    for i in periods.items():
        if counter > i[0]:
            period, minorbase = i[1]
        else:
            break
    secleft = 60 - (timesec)  # Сколько секунд от начала измерений до начала следующей минуты
    x2ticks = [secleft + i * period for i in range(1 + counter // period) if secleft + i * period <= counter]

    if x2ticks[0] != 0:  # Если измерение начинается не в 0 секунд, ...
        timemin += 1  # ... то минута первого тика на 1 больше
    for i in x2ticks:
        if timemin >= 60:
            timemin, timehour = timemin % 60, timehour + timemin // 60
        if timehour >= 24:
            timehour = timehour % 24
        marks.append("%d:%s" % (timehour, '%.2d' % timemin))
        timemin += period / 60

    return (x2ticks, marks, secleft, minorbase)


if __name__ == "__main__":
    receptor('ping 192.168.111.59 -n 30', 'f', '5.18', 'wire')
#        receptor('Arena 2021.05.30 11-10-19 Main Commutator.txt', 'r', 'wire', 'vlan 111 Telecoma')


""" Запрос, режим, расположение, комментарий
Режимы:
    "f" - final - график строится и сохраняется по окончанию серии пингов, файл отчёта обновляется с каждым измерением
    "n" - no saving final - график строится по окончанию серии пингов, но не сохраняется
    "r" - чтение из файла
"""
