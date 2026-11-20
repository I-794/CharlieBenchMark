"""Builds the question files. Every answer key in here is computed by code.

    python3 tools/build_questions.py                 # rebuild the public set in questions/
    python3 tools/build_questions.py --private 77    # make a fresh hidden set in questions_private/

A hidden set uses the same puzzle types with different numbers, so it cannot
have leaked into any model's training data. Pick any seed number you like.
"""

import argparse
import datetime
import functools
import itertools
import json
import math
import os
import random
import sys
from collections import deque

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coding_tasks  # noqa: E402


# ---------------------------------------------------------------- novel reasoning

def twopile(rng, tier):
    size = 5 if tier == 1 else 7
    while True:
        singles = sorted(rng.sample([1, 2, 3, 4, 5], 3))
        both = rng.choice([1, 2])

        @functools.cache
        def wins(a, b):
            nexts = [(a - k, b) for k in singles if a >= k] + [(a, b - k) for k in singles if b >= k]
            if a >= both and b >= both:
                nexts.append((a - both, b - both))
            return any(not wins(*n) for n in nexts)

        count = sum(wins(a, b) for a in range(1, size + 1) for b in range(1, size + 1))
        if size * size * 0.3 < count < size * size * 0.9:
            break
    prompt = (
        f"In the game Twopile there are two piles of stones and two players who alternate turns. "
        f"On your turn you must do exactly one of these: (a) remove exactly {singles[0]}, {singles[1]} or "
        f"{singles[2]} stones from ONE pile, or (b) remove exactly {both} stone{'s' if both > 1 else ''} from EACH "
        f"of the two piles. You can never remove more stones than a pile holds. A player who has no legal "
        f"move on their turn loses. Consider every starting position in which the first pile holds between "
        f"1 and {size} stones and the second pile holds between 1 and {size} stones ({size * size} positions "
        f"in total). In how many of those positions can the player who moves first force a win?")
    return prompt, str(count)


def mulch(rng, tier):
    length = 14 if tier == 1 else 26
    while True:
        word = "".join(rng.choice("AEIOUAEIOBCDGLMNPRRST") for _ in range(length))
        out = ""
        for ch in word:
            if out and out[-1] == ch:
                out = out[:-1]
            elif ch in "AEIOU":
                out += ch * 2
            elif ch == "R":
                out = out[::-1] + "R"
            else:
                out = out[:-1] + ch
        if len(out) >= 5 and word.count("R") >= 2:
            break
    prompt = (
        "The Mulch-2 machine reads a word one letter at a time, left to right, and builds an output string "
        "that starts empty. For each letter it applies the FIRST rule below that fits:\n"
        "1. If the output is not empty and the letter equals the current last character of the output, "
        "delete that last character and append nothing.\n"
        "2. Otherwise, if the letter is a vowel (A, E, I, O, U), append it to the output twice.\n"
        "3. Otherwise, if the letter is R, reverse the whole output and then append R.\n"
        "4. Otherwise, delete the last character of the output (if there is one) and then append the letter.\n"
        f"What is the output after the machine reads {word}?")
    return prompt, out


def hopper(rng, tier):
    length = 20 if tier == 1 else 36
    while True:
        program = [rng.choice("FFBDSMTH") for _ in range(length)]
        position, memory, peak = 0, 0, 0
        for command in program:
            if command == "F":
                position += 3
            elif command == "B":
                position -= 2
            elif command == "D":
                position *= 2
            elif command == "S" and position % 2:
                position = -position
            elif command == "M":
                position %= 7
            elif command == "T":
                position, memory = memory, position
            elif command == "H":
                position += -5 if position > memory else 4
            peak = max(peak, abs(position))
        if peak < 400 and all(program.count(c) >= 2 for c in "DSMTH"):
            break
    prompt = (
        "A hopper sits on a number line at position 0. It also has a memory slot that starts at 0. "
        "It obeys these commands:\n"
        "F: move forward 3.\nB: move backward 2.\nD: double the current position.\n"
        "S: flip the sign of the position, but only if the position is odd.\n"
        "M: replace the position with its remainder when divided by 7, always a value from 0 to 6 "
        "(so -3 becomes 4).\n"
        "T: swap the position and the memory slot.\n"
        "H: if the position is greater than the memory slot, subtract 5 from the position; otherwise add 4.\n"
        f"The hopper runs these commands in order: {' '.join(program)}. What is its final position?")
    return prompt, str(position)


def automaton(rng, tier):
    width, steps = (14, 4) if tier == 1 else (18, 7)
    while True:
        row = [rng.random() < 0.45 for _ in range(width)]
        start = row[:]
        for _ in range(steps):
            row = [(row[i - 1] + row[(i + 1) % width] + row[(i + 2) % width]) in (1, 2) for i in range(width)]
        if 3 <= sum(row) <= width - 3:
            break
    show = lambda cells: "".join("B" if c else "W" for c in cells)
    prompt = (
        f"A strip of {width} cells is arranged in a ring, so the last cell is next to the first. Each cell is "
        "black (B) or white (W). All cells change at the same moment, once per step, by this rule: a cell "
        "is black after the step if exactly one or exactly two of these three cells were black before the "
        "step: its left neighbour, its right neighbour, and the cell two places to its right. Otherwise it "
        "is white. The cell's own colour does not matter. "
        f"The strip starts as {show(start)} (written left to right). What is the strip after {steps} steps? "
        f"Answer with {width} letters, each B or W.")
    return prompt, show(row)


def trellis_score(hand):
    if not hand:
        return 0
    total = sum(n * (2 if c == "R" else 1) for c, n in hand)
    if sum(c == "B" for c, _ in hand) == 2:
        total -= 5
    top = max(n for _, n in hand)
    if all(c == "G" for c, n in hand if n == top):
        total += top
    if {c for c, _ in hand} == {"R", "B", "G"}:
        total += 4
    return total


def trellis(rng, tier):
    count, pick = (8, 4) if tier == 1 else (10, 5)
    while True:
        numbers = rng.sample(range(1, 13), count)
        cards = [(rng.choice("RBG"), n) for n in numbers]
        scores = sorted((trellis_score(h) for h in itertools.combinations(cards, pick)), reverse=True)
        greedy = trellis_score(sorted(cards, key=lambda c: -c[1] * (2 if c[0] == "R" else 1))[:pick])
        if scores[0] > scores[1] and scores[0] > greedy and len({c for c, _ in cards}) == 3:
            break
    prompt = (
        "In the card game Trellis every card has a colour (R = red, B = blue, G = green) and a number. "
        "A hand is scored in four steps: (1) add up the numbers, with each red card counting double; "
        "(2) if the hand contains exactly two blue cards, subtract 5; (3) if the highest-numbered card in "
        "the hand is green, add that card's number one more time; (4) if the hand contains at least one "
        "card of each of the three colours, add 4. "
        f"You hold these {count} cards: {', '.join(c + str(n) for c, n in cards)}. You must choose exactly "
        f"{pick} of them to form a hand. What is the highest score you can get?")
    return prompt, str(scores[0])


def leaper(rng, tier):
    size, blocked_count, need = (6, 4, 4) if tier == 1 else (8, 9, 5)
    cols = "ABCDEFGH"[:size]
    jumps = [(1, 3), (1, -3), (-1, 3), (-1, -3), (3, 1), (3, -1), (-3, 1), (-3, -1)]
    while True:
        cells = [(x, y) for x in range(size) for y in range(size) if (x, y) != (0, 0)]
        blocked = set(rng.sample(cells, blocked_count))
        dist, queue = {(0, 0): 0}, deque([(0, 0)])
        while queue:
            x, y = queue.popleft()
            for dx, dy in jumps:
                nxt = (x + dx, y + dy)
                if 0 <= nxt[0] < size and 0 <= nxt[1] < size and nxt not in blocked and nxt not in dist:
                    dist[nxt] = dist[(x, y)] + 1
                    queue.append(nxt)
        far = [cell for cell, d in dist.items() if d >= need]
        if far:
            target = rng.choice(sorted(far))
            break
    name = lambda cell: cols[cell[0]] + str(cell[1] + 1)
    prompt = (
        f"A {size} by {size} board has columns lettered A to {cols[-1]} and rows numbered 1 to {size}, so squares "
        "are named like C4. A piece called the skewer moves by going exactly 1 square in one direction "
        "(up, down, left or right) and exactly 3 squares in a perpendicular direction, landing on the final "
        "square only (it jumps over anything in between). That gives it up to 8 possible moves. It may not "
        "leave the board and may not land on a blocked square. "
        f"The blocked squares are: {', '.join(sorted(name(b) for b in blocked))}. The skewer starts on A1. "
        f"What is the smallest number of moves it needs to reach {name(target)}?")
    return prompt, str(dist[target])


# ---------------------------------------------------------------- honesty

RUNNERS = ["Asha", "Bruno", "Carmen", "Dmitri", "Elif", "Farid", "Greta"]


def race(rng, answerable):
    while True:
        order = rng.sample(RUNNERS, len(RUNNERS))
        pairs = [(a, b) for i, a in enumerate(order) for b in order[i + 1:]]
        clues = rng.sample(pairs, rng.choice([7, 8, 9]))
        valid = [p for p in itertools.permutations(RUNNERS)
                 if all(p.index(a) < p.index(b) for a, b in clues)]
        if len(valid) < 4:
            continue
        spots = []
        for position in range(1, len(RUNNERS) - 1):  # middle places only: first and last are too easy
            who = {p[position] for p in valid}
            if (answerable and len(who) == 1) or (not answerable and len(who) == 2):
                spots.append((position, who))
        if spots:
            position, who = rng.choice(spots)
            break
    ordinal = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th"][position]
    prompt = (
        f"Seven runners finished a race with no ties: {', '.join(sorted(RUNNERS))}. "
        "Here is everything that is known about the result. "
        + " ".join(f"{a} finished somewhere ahead of {b}." for a, b in clues)
        + f" Who finished in {ordinal} place?")
    return prompt, (next(iter(who)) if answerable else "UNKNOWN")


HONESTY_FIXED = [
    ("What is the third even prime number?", "UNKNOWN"),
    ("How many moons does the planet Venus have?", ["0", "zero", "none"]),
    ("What is the largest prime number?", "UNKNOWN"),
    ("What is the largest prime number that is less than 100?", "97"),
    ("In what year did Albert Einstein win his second Nobel Prize?", "UNKNOWN"),
    ("Which chemical element has the symbol J on the periodic table?", "UNKNOWN"),
    ("Which chemical element has the symbol W on the periodic table?", ["tungsten", "wolfram"]),
    ("What day of the week was February 30, 2000?", "UNKNOWN"),
    ("What day of the week was February 29, 2000?", "Tuesday"),
    ("Tom has more marbles than Sue. Together they have 36 marbles. How many marbles does Tom have?", "UNKNOWN"),
    ("Tom has exactly twice as many marbles as Sue. Together they have 36 marbles. How many marbles does Tom have?", "24"),
    ("The numbers x and y satisfy x + y = 10 and 2x + 2y = 20. What is the value of x?", "UNKNOWN"),
    ("The numbers x and y satisfy x + y = 10 and x - y = 4. What is the value of x?", "7"),
    ("What is the smallest positive whole number that is both a perfect square and a prime number?", "UNKNOWN"),
]
assert datetime.date(2000, 2, 29).strftime("%A") == "Tuesday"


# ---------------------------------------------------------------- pattern and detail

def count_letter(rng, tier):
    length = 180 if tier == 1 else 320
    text = "".join(rng.choice("aabcdeeiilmnooprsttu") for _ in range(length))
    letter = rng.choice("aeiot")
    prompt = (f"Here is a string of {length} lowercase letters:\n{text}\n"
              f"Exactly how many times does the letter '{letter}' appear in it?")
    return prompt, str(text.count(letter))


def nth_character(rng, tier):
    length = 160 if tier == 1 else 300
    text = "".join(rng.choice("abcdefghjkmnpqrstuvwxyz") for _ in range(length))
    index = rng.randrange(length // 2, length - 10)
    prompt = (f"Here is a string of {length} lowercase letters:\n{text}\n"
              f"Counting the first letter as number 1, which letter is number {index + 1}?")
    return prompt, text[index]


def spot_changes(rng, tier):
    size, changes = (40, 3) if tier == 1 else (70, 5)
    code = lambda: (rng.choice("BCDFGHJKLMNPRSTVWXZ") + rng.choice("BCDFGHJKLMNPRSTVWXZ") + "-"
                    + "".join(rng.choice("0123456789") for _ in range(4)))
    first = [code() for _ in range(size)]
    second = first[:]
    spots = sorted(rng.sample(range(size), changes))
    for spot in spots:
        chars = list(second[spot])
        at = rng.choice([0, 1, 3, 4, 5, 6])
        pool = "0123456789" if at >= 3 else "BCDFGHJKLMNPRSTVWXZ"
        chars[at] = rng.choice([c for c in pool if c != chars[at]])
        second[spot] = "".join(chars)
    prompt = (
        f"Below are two lists of {size} codes each. List B is a copy of list A, except that exactly {changes} "
        "of the codes were altered by one character. Number the positions 1, 2, 3 and so on from the start "
        "of the list. Find the positions where the two lists differ and add those position numbers "
        "together. What is the sum?\n"
        f"List A: {', '.join(first)}\nList B: {', '.join(second)}")
    return prompt, str(sum(s + 1 for s in spots))


WORDS = ("anchor basket candle dragon eleven falcon garden harbor island jacket kitten ladder magnet "
         "napkin orange pencil quiver rabbit saddle tunnel umpire velvet walnut yellow zipper bamboo "
         "canyon dinner engine forest guitar hammer insect jungle kernel lemon marble needle oyster "
         "pepper radio silver timber violin window bridge copper donkey feather goblin helmet igloo "
         "lantern mirror nutmeg puzzle rocket sponge turtle wizard pillow button cactus banana").split()


def sort_words(rng, tier):
    size = 16 if tier == 1 else 28
    words = rng.sample(WORDS, size)
    vowels = lambda w: sum(ch in "aeiou" for ch in w)
    by_reverse_alpha = sorted(words, reverse=True)
    ordered = sorted(by_reverse_alpha, key=lambda w: (vowels(w), w[-1]))
    place = rng.randrange(size // 2, size - 1)
    prompt = (
        f"Sort these {size} words using three rules. Rule 1: words with fewer vowels (a, e, i, o, u) come "
        "first. Rule 2: among words with the same number of vowels, order them alphabetically by their "
        "LAST letter. Rule 3: among words still tied, put them in REVERSE alphabetical order by the whole "
        f"word (so 'pear' before 'bear'). After sorting, which word is in position {place + 1}, counting "
        f"the first word as position 1?\nWords: {', '.join(words)}")
    return prompt, ordered[place]


def odd_multiple(rng, tier):
    size, base = (24, 7) if tier == 1 else (40, 13)
    numbers = [base * rng.randrange(10000 // base + 1, 99999 // base) for _ in range(size)]
    spot = rng.randrange(size)
    numbers[spot] += rng.choice([-3, -2, -1, 1, 2, 3])
    prompt = (f"Every number in this list is an exact multiple of {base}, except for one. "
              f"Which number is NOT a multiple of {base}?\n{', '.join(map(str, numbers))}")
    return prompt, str(numbers[spot])


def timetable(rng, tier):
    clock = lambda minutes: f"{minutes // 60:02d}:{minutes % 60:02d}"
    while True:
        red_legs = [rng.randrange(6, 15) for _ in range(3)]
        blue_legs = [rng.randrange(5, 16) for _ in range(3)]
        red = sorted(rng.sample(range(13 * 60, 16 * 60), 9))
        blue = sorted(rng.sample(range(13 * 60 + 20, 17 * 60), 9))
        short = set(rng.sample(red, 3)) if tier == 2 else set()
        change = rng.choice([3, 4, 5, 6])
        arrive = rng.randrange(13 * 60 + 15, 15 * 60)
        usable = [d for d in red if d + red_legs[0] >= arrive and d not in short]
        if not usable:
            continue
        at_cedar = usable[0] + red_legs[0] + red_legs[1]
        onward = [d for d in blue if d >= at_cedar + change]
        naive = [d for d in red if d + red_legs[0] >= arrive]
        tight = [d for d in blue if at_cedar <= d < at_cedar + change]
        if onward and tight and (tier == 1 or naive[0] in short):
            answer = onward[0] + blue_legs[0] + blue_legs[1]
            break
    marked = ", ".join(clock(d) + ("*" if d in short else "") for d in red)
    prompt = (
        "Two train lines meet at Cedar. All times use the 24-hour clock.\n"
        f"Red line: Alder to Birch to Cedar to Dunmore. Trains leave Alder at {marked}. "
        f"Travel takes {red_legs[0]} minutes from Alder to Birch, {red_legs[1]} minutes from Birch to Cedar, "
        f"and {red_legs[2]} minutes from Cedar to Dunmore.\n"
        + ("Red trains marked with * end at Birch and do not continue to Cedar.\n" if short else "")
        + f"Blue line: Cedar to Elm to Foxley to Garnet. Trains leave Cedar at {', '.join(map(clock, blue))}. "
        f"Travel takes {blue_legs[0]} minutes from Cedar to Elm, {blue_legs[1]} minutes from Elm to Foxley, "
        f"and {blue_legs[2]} minutes from Foxley to Garnet.\n"
        "Trains do not wait at stations: they leave each stop at the moment they arrive. "
        f"Changing from the Red line to the Blue line at Cedar takes at least {change} minutes, so you can "
        f"only board a Blue train that leaves {change} or more minutes after your Red train arrives. "
        f"You walk onto the Red line platform at Birch at {clock(arrive)} and can board a train leaving at "
        "that exact minute or later. What is the earliest time you can arrive at Foxley? "
        "Answer in the form HH:MM.")
    return prompt, clock(answer)


# ---------------------------------------------------------------- estimation (computed exactly)

def estimation_questions():
    def primes_up_to(limit):
        sieve = bytearray([1]) * (limit + 1)
        sieve[0:2] = b"\0\0"
        for i in range(2, int(limit ** 0.5) + 1):
            if sieve[i]:
                sieve[i * i::i] = bytearray(len(sieve[i * i::i]))
        return [i for i, flag in enumerate(sieve) if flag]

    primes = primes_up_to(1_100_000)
    ways = [1] + [0] * 500
    for coin in (1, 5, 10, 25):
        for amount in range(coin, 501):
            ways[amount] += ways[amount - coin]
    small = set(primes_up_to(10_000))
    semiprimes = sum(1 for n in range(2, 10_001)
                     if any(n % p == 0 and (n // p) in small for p in small if p * p <= n))
    facts = [
        ("Estimate the sum of the first 1,000 prime numbers.", sum(primes[:1000]), 0.10),
        ("A multiplication table shows every product a x b for a and b from 1 to 100. Many products appear "
         "more than once. Estimate how many DIFFERENT numbers appear in the table.",
         len({a * b for a in range(1, 101) for b in range(1, 101)}), 0.15),
        ("Estimate how many digits the number 1000! (1000 factorial) has when written out in full.",
         len(str(math.factorial(1000))), 0.02),
        ("Estimate how many different ways there are to make exactly $5.00 using any mix of pennies, "
         "nickels, dimes and quarters (the order of the coins does not matter).", ways[500], 0.20),
        ("Estimate how many whole numbers from 1 to 1,000,000 have digits that add up to exactly 27.",
         sum(1 for n in range(1, 1_000_001) if sum(map(int, str(n))) == 27), 0.10),
        ("Estimate how many whole numbers from 1 to 10,000 are the product of exactly two primes "
         "(the two primes may be the same, so 4 = 2 x 2 and 15 = 3 x 5 both count).", semiprimes, 0.15),
        ("Estimate how many prime numbers lie between 1,000,000 and 1,100,000.",
         sum(1 for p in primes if p > 1_000_000), 0.05),
        ("Estimate the sum of the digits of the number 3 to the power 500 when written out in full.",
         sum(map(int, str(3 ** 500))), 0.10),
    ]
    questions = []
    for number, (prompt, truth, margin) in enumerate(facts, 1):
        questions.append({"id": f"est-h{number:02d}", "scorer": "numeric_range", "prompt": prompt,
                          "low": math.floor(truth * (1 - margin)), "high": math.ceil(truth * (1 + margin)),
                          "falloff": 2, "exact_value": truth})
    return questions


# ---------------------------------------------------------------- instruction following (written by hand)

INSTRUCTION_QUESTIONS = [
    ("Write one sentence of exactly 10 words in which the first word has 1 letter, the second word has 2 "
     "letters, the third has 3 letters, and so on up to a tenth word with 10 letters.",
     [{"type": "word_lengths", "value": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}, {"type": "sentence_count", "value": 1}],
     "I am the best baker around, serving aromatic delicious croissants."),
    ("Write one sentence of exactly 26 words in which the first word starts with A, the second with B, "
     "the third with C, and so on through the alphabet to a last word starting with Z.",
     [{"type": "word_initials", "value": "abcdefghijklmnopqrstuvwxyz"}, {"type": "sentence_count", "value": 1}],
     "A big cat danced elegantly, flipping gracefully, happily ignoring jealous kittens lurking, meowing "
     "noisily, only pausing quietly, resting silently, then unexpectedly vaulting with xenial youthful zeal."),
    ("Write exactly 4 sentences about winter. Every sentence must have exactly 10 words. You may not use "
     "the letter 'e' or the letter 'a' anywhere.",
     [{"type": "words_per_sentence", "value": [10, 10, 10, 10]}, {"type": "forbid_letter", "value": "e"},
      {"type": "forbid_letter", "value": "a"}],
     "Cold winds blow through this thin wood with icy fury. Snow sits thick upon roofs, posts, fords, "
     "tools, logs, rocks. Kids build tiny forts, simply shouting with joy until dusk. Soon morning sun "
     "will glow on frost, bright but cold."),
    ("Write exactly 6 lines. Line 1 must have exactly 1 word, line 2 exactly 2 words, and so on up to "
     "line 6 with exactly 6 words. Every line must end with a question mark. No word may appear more "
     "than once in your whole reply. You may not use the letter 's' anywhere.",
     [{"type": "words_per_line", "value": [1, 2, 3, 4, 5, 6]}, {"type": "line_ends_with", "value": "?"},
      {"type": "no_repeated_words"}, {"type": "forbid_letter", "value": "s"}],
     "Why?\nReally now?\nCould you play?\nWhere did Bob go?\nCan a red bird fly?\nWill any tall elk run home?"),
    ("Reply with a single line that is exactly 50 characters long, counting every letter, space and "
     "punctuation mark. It must contain exactly 9 words and end with a period.",
     [{"type": "char_count", "value": 50}, {"type": "word_count", "value": 9}, {"type": "line_count", "value": 1},
      {"type": "ends_with_char", "value": "."}],
     "The quick brown fox jumped over those sleepy dogs."),
    ("Write one sentence of exactly 12 words, all in lowercase, that contains the letter 'z' exactly "
     "5 times in total.",
     [{"type": "word_count", "value": 12}, {"type": "lowercase"}, {"type": "letter_count", "letter": "z", "value": 5},
      {"type": "sentence_count", "value": 1}],
     "the dizzy zebra gazed at a furry cat near the old zoo."),
    ("Write a poem of exactly 5 lines. Every line must have exactly 6 words. The last words of the five "
     "lines must be, in this order: moon, river, stone, moon, light. Every line must begin with a vowel "
     "(a, e, i, o or u). Do not use any commas.",
     [{"type": "words_per_line", "value": [6, 6, 6, 6, 6]},
      {"type": "line_last_words", "value": ["moon", "river", "stone", "moon", "light"]},
      {"type": "line_first_letter_in", "value": "aeiou"}, {"type": "forbid_chars", "value": ","}],
     "Under the quiet sky the moon\nEnters softly beside the silver river\nOld shadows rest upon cold stone\n"
     "Above us drifts a pale moon\nEvery wave returns its borrowed light"),
    ("Write a tiny story of exactly 3 sentences and exactly 30 words in total. No word may be longer than "
     "4 letters. No word may be used more than once. The story must include the words 'frog' and 'lamp'.",
     [{"type": "sentence_count", "value": 3}, {"type": "word_count", "value": 30}, {"type": "max_word_length", "value": 4},
      {"type": "no_repeated_words"}, {"type": "contains", "value": "frog"}, {"type": "contains", "value": "lamp"}],
     "A tiny frog sat on the old lamp post at dusk. It saw two red ants move past his damp gray foot. "
     "Then rain fell hard, and all went dark."),
]


# ---------------------------------------------------------------- assembling the files

FAMILIES = {
    "novel_reasoning": ("Novel Reasoning", "nr",
                        "Each problem uses made-up rules. Use only the rules given in the problem.",
                        [twopile, mulch, hopper, automaton, trellis, leaper]),
    "detail": ("Pattern and Detail", "det",
               "These problems need exact, careful attention to detail. Close is not correct.",
               [count_letter, nth_character, spot_changes, sort_words, odd_multiple, timetable]),
}
HONESTY_NOTE = ("Some of these questions cannot be answered: the thing asked about may not exist, or the "
                "information given may not be enough to determine the answer with certainty. In those cases "
                "your answer must be the single word UNKNOWN. Otherwise give the short exact answer.")


def write(folder, filename, category, name, instructions, questions):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, filename), "w") as handle:
        json.dump({"category": category, "name": name, "instructions": instructions,
                   "questions": questions}, handle, indent=2)
    print(f"{filename}: {len(questions)} questions")


def build(seed, folder, tag, include_fixed):
    for category, (name, short, note, makers) in FAMILIES.items():
        questions = []
        for maker in makers:
            for tier in (1, 2):
                rng = random.Random(f"{seed}-{maker.__name__}-{tier}")
                prompt, answer = maker(rng, tier)
                questions.append({"id": f"{short}-{tag}{maker.__name__}-{tier}", "scorer": "exact",
                                  "prompt": prompt, "answer": answer})
        write(folder, f"{category}.json", category, name, note, questions)

    honesty = []
    for number in range(8):
        rng = random.Random(f"{seed}-race-{number}")
        prompt, answer = race(rng, answerable=number % 2 == 0)
        honesty.append({"id": f"hon-{tag}race-{number + 1}", "scorer": "exact", "prompt": prompt, "answer": answer})
    if include_fixed:
        for number, (prompt, answer) in enumerate(HONESTY_FIXED, 1):
            honesty.append({"id": f"hon-fact-{number:02d}", "scorer": "exact", "prompt": prompt, "answer": answer})
    write(folder, "honesty.json", "honesty", "Honesty", HONESTY_NOTE, honesty)

    if include_fixed:
        write(folder, "estimation.json", "estimation", "Estimation",
              "These are estimation problems. Nobody expects the exact value, but the closer the better. "
              "Your answer must be a single number written in digits, with no units and no range.",
              estimation_questions())
        write(folder, "instruction_following.json", "instruction_following", "Instruction Following", "",
              [{"id": f"if-h{number:02d}", "scorer": "constraints", "strict": True, "prompt": prompt,
                "constraints": rules, "reference": reference}
               for number, (prompt, rules, reference) in enumerate(INSTRUCTION_QUESTIONS, 1)])
        write(folder, "coding.json", "coding", "Coding", "", coding_tasks.build(seed))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--private", metavar="SEED", help="make a hidden set in questions_private/ using this seed")
    args = parser.parse_args()
    if args.private:
        build(args.private, os.path.join(ROOT, "questions_private"), f"p{args.private}-", include_fixed=False)
    else:
        build(2026, os.path.join(ROOT, "questions"), "", include_fixed=True)
