import datetime

FROZEN_TIME_LIST_INT = [2020, 1, 1, 12, 0, 0]
FROZEN_DATETIME =  datetime.datetime(*FROZEN_TIME_LIST_INT)
FROZEN_TIME_STR = FROZEN_DATETIME.strftime("%d-%m-%YT%H:%M:%S")

