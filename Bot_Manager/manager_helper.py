import string
import random


def generate_random_string(length):
    characters = list(f'{string.ascii_letters}')
    random.shuffle(characters)
    text = []
    for i in range(length):
        text.append(random.choice(characters))

    random.shuffle(text)
    return "".join(text)