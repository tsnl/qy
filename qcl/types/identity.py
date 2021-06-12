import dataclasses
import enum


TID = int


count_in_circulation = 0


def mint():
    global count_in_circulation
    count_in_circulation += 1
    return count_in_circulation

