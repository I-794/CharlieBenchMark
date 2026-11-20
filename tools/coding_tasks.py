"""The coding questions: each has a detailed spec, a reference solution, and hidden tests.

Expected outputs are produced by running the reference solution, so the spec
and the tests can never disagree with each other by accident.
"""

import json
import random

TASKS = []


def task(function, prompt, reference, make_tests):
    TASKS.append((function, prompt, reference, make_tests))


# ------------------------------------------------------------------ 1. stack language

task("blip", """Write a function blip(program) that runs a program in the tiny stack language Blip and returns its output.

`program` is a string of tokens separated by single spaces. An empty string is a program with no tokens. The machine has a stack of integers (starts empty) and an output list (starts empty). Tokens are executed left to right:

- An integer such as 7 or -12 (an optional minus sign followed by digits): push it.
- + - * : pop b, then pop a, then push a+b, a-b or a*b.
- / : pop b, then pop a, then push a // b using Python floor division. If b is 0 that is an error.
- dup : push a copy of the top value.
- drop : remove the top value.
- swap : swap the top two values.
- over : push a copy of the second value from the top.
- print : pop the top value and append it to the output list.
- [ : pop a value n. If n <= 0, skip forward to just after the matching ]. Otherwise run the tokens between this [ and its matching ] exactly n times in a row, then continue after the ]. Blocks can be nested. n is popped only once, when the [ is reached.
- ] : marks the end of a block.

Errors: any token that is not listed above, popping or reading from a stack that does not hold enough values, division by zero, or brackets that do not match up (a ] with no earlier unmatched [, or a [ that is never closed). Brackets are checked for the whole program before anything runs, so a program with bad brackets is an error even if the bad part would never execute. Other errors only count if the token is actually executed.

If an error happens return the string "ERROR". Otherwise return the output list.

Example: blip("3 [ 7 print ]") returns [7, 7, 7] and blip("1 +") returns "ERROR".""",
'''def blip(program):
    import re
    tokens = program.split(" ") if program else []
    match, open_stack = {}, []
    for i, tok in enumerate(tokens):
        if tok == "[":
            open_stack.append(i)
        elif tok == "]":
            if not open_stack:
                return "ERROR"
            match[open_stack.pop()] = i
    if open_stack:
        return "ERROR"
    stack, out = [], []

    class Bad(Exception):
        pass

    def pop():
        if not stack:
            raise Bad()
        return stack.pop()

    def run(lo, hi):
        i = lo
        while i < hi:
            tok = tokens[i]
            if re.fullmatch(r"-?[0-9]+", tok):
                stack.append(int(tok))
            elif tok in ("+", "-", "*", "/"):
                b = pop()
                a = pop()
                if tok == "+":
                    stack.append(a + b)
                elif tok == "-":
                    stack.append(a - b)
                elif tok == "*":
                    stack.append(a * b)
                else:
                    if b == 0:
                        raise Bad()
                    stack.append(a // b)
            elif tok == "dup":
                a = pop()
                stack.extend([a, a])
            elif tok == "drop":
                pop()
            elif tok == "swap":
                b = pop()
                a = pop()
                stack.extend([b, a])
            elif tok == "over":
                if len(stack) < 2:
                    raise Bad()
                stack.append(stack[-2])
            elif tok == "print":
                out.append(pop())
            elif tok == "[":
                n = pop()
                end = match[i]
                for _ in range(max(n, 0)):
                    run(i + 1, end)
                i = end
            elif tok == "]":
                pass
            else:
                raise Bad()
            i += 1

    try:
        run(0, len(tokens))
    except Bad:
        return "ERROR"
    return out
''',
lambda rng: [[p] for p in [
    "", "3 [ 7 print ]", "1 +", "2 3 + print", "10 3 - print 10 3 / print -10 3 / print", "7 0 /",
    "5 dup * print", "1 2 swap print print", "1 2 over print print print", "4 drop print",
    "0 [ 1 0 / ] 9 print", "0 [ bogus ] 9 print", "1 [ bogus ]", "-2 [ 5 print ] 6 print",
    "2 [ 3 [ 1 print ] 0 print ]", "1 5 [ dup print 2 * ] drop", "] 1 print [", "1 [ 2 print", "1 print ]",
    "0 [ ] ]", "3 [ ]", "[", "5 print print", "over", "1 over", "2 [ 2 [ 2 [ 8 print ] ] ]",
    "1 2 3 4 5 5 [ print ]", "10 0 4 [ over + ] print print", "3 dup [ dup print 1 - ] print",
    "6 -3 / print 7 -2 / print", "--5 print", "1 2 3 * + print", "0 1 [ dup [ 9 print ] 4 print ] print",
    "2 [ 1 [ 0 [ 5 0 / ] 3 print ] ]", "4 2 [ dup * ] print", "1 [ 2 [ ] ] print", "PRINT", "3 [ 1 ] + + print",
]])


# ------------------------------------------------------------------ 2. invented calendar

task("kessel_date", """Write a function kessel_date(n) that converts a day count into a date in the Kessel calendar.

The Kessel calendar works like this:
- A year has 10 months, numbered 1 to 10. Odd-numbered months have 37 days and even-numbered months have 36 days.
- In a leap year, month 10 has 37 days instead of 36.
- Year Y is a leap year if Y is divisible by 4 but not by 20, or if Y is divisible by 100. Years are numbered starting from 1.
- Weeks have 6 days named, in order: Ao, Bel, Cur, Dax, Eph, Fen. The week cycle never resets.

n is a whole number, 1 or more. Day number 1 is year 1, month 1, day 1, and it is an Ao. Return a string in the form "Y-M-D W" where W is the weekday name, with no zero padding.

Example: kessel_date(1) returns "1-1-1 Ao" and kessel_date(38) returns "1-2-1 Bel".""",
'''def kessel_date(n):
    names = ["Ao", "Bel", "Cur", "Dax", "Eph", "Fen"]
    weekday = names[(n - 1) % 6]

    def leap(y):
        return (y % 4 == 0 and y % 20 != 0) or y % 100 == 0

    year, left = 1, n
    while True:
        size = 366 if leap(year) else 365
        if left > size:
            left -= size
            year += 1
        else:
            break
    month = 1
    while True:
        days = 37 if month % 2 == 1 else 36
        if month == 10 and leap(year):
            days = 37
        if left > days:
            left -= days
            month += 1
        else:
            break
    return "%d-%d-%d %s" % (year, month, left, weekday)
''',
lambda rng: [[n] for n in
             [1, 2, 6, 7, 37, 38, 73, 74, 365, 366, 367, 730, 731, 1095, 1096, 1460, 1461, 1462, 1827,
              365 * 19 + 4, 365 * 19 + 5, 365 * 20 + 4, 365 * 20 + 5, 7300, 7305, 36500, 36523, 36524, 36525]
             + [rng.randrange(1, 3_000_000) for _ in range(12)]])


# ------------------------------------------------------------------ 3. spreadsheet

task("evaluate_sheet", """Write a function evaluate_sheet(cells) that evaluates a small spreadsheet.

`cells` is a dict that maps cell names (an uppercase letter followed by digits, like "A1" or "C12") to strings. Each string is one of:
- An integer literal such as "42" or "-7".
- A formula: "=" followed by one or more terms joined by "+" or "-" with no spaces, such as "=A1+B2-3". Each term is either a non-negative integer or a cell name. The first term never has a sign in front of it.

Rules:
- A reference to a cell name that is not a key in `cells` counts as 0.
- A cell is "bad" if it is part of a reference cycle (including a cell that refers to itself), or if it refers, directly or through other cells, to a bad cell.

Return a dict with the same keys. Each value is the cell's integer result, or the string "#CYCLE" if the cell is bad.

Example: evaluate_sheet({"A1": "5", "A2": "=A1+A1-2", "A3": "=A3+1", "A4": "=A3+A1", "A5": "=Z9+1"}) returns {"A1": 5, "A2": 8, "A3": "#CYCLE", "A4": "#CYCLE", "A5": 1}.""",
'''def evaluate_sheet(cells):
    import re
    result, state = {}, {}

    def value(name):
        if name not in cells:
            return 0
        if name in result:
            return result[name]
        if state.get(name) == "busy":
            return None
        state[name] = "busy"
        text = cells[name]
        if not text.startswith("="):
            answer = int(text)
        else:
            answer = 0
            for sign, term in re.findall(r"([+-]?)([A-Z][0-9]+|[0-9]+)", text[1:]):
                v = int(term) if term.isdigit() else value(term)
                if v is None or v == "#CYCLE":
                    answer = "#CYCLE"
                    break
                answer += -v if sign == "-" else v
        state[name] = "done"
        result[name] = answer
        return answer

    for name in cells:
        value(name)
    return {name: result[name] for name in cells}
''',
None)


def sheet_tests(rng):
    tests = [
        [{"A1": "5", "A2": "=A1+A1-2", "A3": "=A3+1", "A4": "=A3+A1", "A5": "=Z9+1"}],
        [{}], [{"A1": "-7"}], [{"A1": "=A1"}], [{"A1": "=B1", "B1": "=A1"}],
        [{"A1": "=B1", "B1": "=C1", "C1": "=A1", "D1": "=B1+1", "E1": "=7"}],
        [{"A1": "=10-3-2", "B1": "=A1-A1", "C1": "=0-A1"}],
        [{"B2": "=A1+A1+A1", "A1": "=C3-1", "C3": "4"}],
        [{"A1": "=B1+C1", "B1": "=D1", "C1": "=D1", "D1": "3"}],
        [{"A1": "=A2", "A2": "=A3", "A3": "=A4", "A4": "=A5", "A5": "=A2+1", "A6": "=A1", "A7": "=9-A9"}],
        [{"A10": "=A1+1", "A1": "=A10+1", "A100": "12", "B1": "=A100-A11"}],
    ]
    for _ in range(14):
        names = [rng.choice("ABCD") + str(rng.randrange(1, 5)) for _ in range(rng.randrange(3, 9))]
        sheet = {}
        for name in dict.fromkeys(names):
            if rng.random() < 0.35:
                sheet[name] = str(rng.randrange(-20, 50))
            else:
                terms = [rng.choice(names + ["E9", str(rng.randrange(0, 30))]) if rng.random() < 0.75
                         else str(rng.randrange(0, 30)) for _ in range(rng.randrange(1, 4))]
                formula = terms[0]
                for term in terms[1:]:
                    formula += rng.choice("+-") + term
                sheet[name] = "=" + formula
        tests.append([sheet])
    return tests


TASKS[-1] = TASKS[-1][:3] + (sheet_tests,)


# ------------------------------------------------------------------ 4. game referee

task("corners_result", """Write a function corners_result(moves) that referees the game Corners.

Corners is played on a 4 by 4 grid. Columns are lettered A to D and rows are numbered 1 to 4, so the 16 cells are named "A1" to "D4" (uppercase letter, then digit). Two players, X and O, take turns claiming one empty cell. X makes move 1, O makes move 2, and so on. A player wins the moment they own all four corner cells of a rectangle whose sides are parallel to the grid. The rectangle must span two different columns and two different rows; squares count.

`moves` is a list of strings, the cells claimed in order. Number the moves starting from 1. Go through them in order:
- If a move is not one of the 16 valid cell names exactly as written above (for example "E1", "A5", "b3" or ""), or the cell is already claimed, or the game was already won by an earlier move, stop and return "invalid move K" where K is that move's number.
- Otherwise the cell is claimed, and if that completes a rectangle for the player who moved, the game is won on that move.

If every move was valid: return "X wins on move K" or "O wins on move K" if the game was won (K is the winning move's number), "draw" if all 16 cells are claimed with no winner, and "unfinished" otherwise.

Example: corners_result(["A1", "B1", "A3", "B2", "C1", "D4", "C3"]) returns "X wins on move 7".""",
'''def corners_result(moves):
    valid = {c + r for c in "ABCD" for r in "1234"}
    owned = {"X": set(), "O": set()}
    taken = set()
    winner = None
    for k, move in enumerate(moves, 1):
        if not isinstance(move, str) or move not in valid or move in taken or winner:
            return "invalid move %d" % k
        player = "X" if k % 2 == 1 else "O"
        taken.add(move)
        mine = owned[player]
        mine.add(move)
        col, row = move[0], move[1]
        for c2 in "ABCD":
            for r2 in "1234":
                if c2 != col and r2 != row and c2 + row in mine and col + r2 in mine and c2 + r2 in mine:
                    winner = (player, k)
    if winner:
        return "%s wins on move %d" % winner
    return "draw" if len(taken) == 16 else "unfinished"
''',
None)


def corners_tests(rng):
    cells = [c + r for c in "ABCD" for r in "1234"]
    tests = [[["A1", "B1", "A3", "B2", "C1", "D4", "C3"]], [[]], [["A1"]], [["A1", "A1"]], [["E1"]],
             [["A1", "b3"]], [["A1", "B2", ""]], [["A1", "B1", "A3", "B2", "C1", "D4", "C3", "D1"]],
             [["A1", "B1", "A2", "B2", "D4", "C1", "D3", "C2"]], [["A1", "A5"]], [["A1", "B2", "A10"]],
             [["A1", "B1", "A2", "B2", "C3", "D4", "B3", "C1", "D2", "C2"]]]
    for _ in range(26):
        order = rng.sample(cells, rng.randrange(4, 17))
        if rng.random() < 0.25:
            order.insert(rng.randrange(len(order) + 1), rng.choice(order + ["D5", "a1", "AA"]))
        tests.append([order])
    # a full board with no rectangle for either player, so the draw outcome is covered
    x_cells = ["A1", "B1", "A2", "C2", "B3", "C3", "A4", "D4"]
    o_cells = ["C1", "D1", "B2", "D2", "A3", "D3", "B4", "C4"]
    draw = [cell for pair in zip(x_cells, o_cells) for cell in pair]
    assert DRAW_CHECK(draw) == "draw"
    tests.append([draw])
    tests.append([draw + ["A1"]])
    return tests


TASKS[-1] = TASKS[-1][:3] + (corners_tests,)


# ------------------------------------------------------------------ 5. card optimiser

task("trellis_best", """Write a function trellis_best(cards, k) for the card game Trellis.

`cards` is a list of [colour, number] pairs. Colour is "R" (red), "B" (blue) or "G" (green) and number is a positive integer. Numbers and whole cards may repeat. You must choose exactly k of the cards (each card in the list can be used at most once) to form a hand, and you want the highest possible score.

A hand is scored like this:
1. Add up the numbers, with each red card counting double.
2. If the hand contains exactly two blue cards, subtract 5.
3. Find the highest number in the hand. If every card in the hand that has that highest number is green, add that number once more (once in total, not once per card).
4. If the hand contains at least one card of each of the three colours, add 4.
An empty hand scores 0.

Return the highest score possible with exactly k cards. Return None if k is greater than the number of cards. The list has at most 12 cards.

Example: trellis_best([["R", 3], ["B", 7], ["G", 9], ["B", 2], ["R", 4]], 5) returns 40.""",
'''def trellis_best(cards, k):
    from itertools import combinations
    if k > len(cards):
        return None

    def score(hand):
        if not hand:
            return 0
        total = sum(n * 2 if c == "R" else n for c, n in hand)
        if sum(1 for c, n in hand if c == "B") == 2:
            total -= 5
        top = max(n for c, n in hand)
        if all(c == "G" for c, n in hand if n == top):
            total += top
        if {c for c, n in hand} == {"R", "B", "G"}:
            total += 4
        return total

    return max(score(hand) for hand in combinations(cards, k))
''',
lambda rng: [[[["R", 3], ["B", 7], ["G", 9], ["B", 2], ["R", 4]], 5], [[], 0], [[], 1], [[["G", 5]], 1],
             [[["G", 5], ["G", 5]], 2], [[["G", 5], ["R", 5]], 2], [[["B", 1], ["B", 2], ["B", 3]], 2],
             [[["B", 1], ["B", 2], ["B", 3]], 3], [[["R", 1]], 0], [[["R", 2], ["B", 2], ["G", 2]], 3]]
            + [[[[rng.choice("RBG"), rng.randrange(1, 10)] for _ in range(rng.randrange(1, 12))],
                rng.randrange(0, 8)] for _ in range(28)])


# ------------------------------------------------------------------ 6. journey planner

task("earliest_arrival", """Write a function earliest_arrival(lines, start, goal, time, transfer) that plans a train journey.

`lines` is a list of dicts. Each dict describes one train line with three keys:
- "stops": a list of station names, in the order trains visit them (at least 2, no repeats within a line).
- "minutes": a list of travel times in whole minutes between consecutive stops (one fewer entry than "stops").
- "departures": a list of times, in minutes after midnight, at which a train leaves the first stop.
Each departure is a separate train. Trains only travel forward along their line. They do not wait at stations: a train leaves each stop at the same minute it arrives there. A station may appear on several lines.

You are standing at station `start` at minute `time`. For the first train of your journey you may board any train that leaves `start` at minute `time` or later. Every later time you board a train (a different departure, even one on the same line) you need a margin: it must leave at least `transfer` minutes after you arrived at that station. Staying on the same train through a stop needs no margin. You may get off at any stop and you may wait as long as you like.

Return the earliest minute at which you can be at `goal`, or None if it cannot be reached. If start equals goal, return `time`.

Example: with lines = [{"stops": ["A", "B", "C"], "minutes": [10, 10], "departures": [0, 30]}, {"stops": ["B", "D"], "minutes": [5], "departures": [12, 45]}], earliest_arrival(lines, "A", "D", 0, 3) returns 50, because the train from A reaches B at minute 10, and the 12 departure is too soon to catch with a 3 minute margin.""",
'''def earliest_arrival(lines, start, goal, time, transfer):
    import heapq
    if start == goal:
        return time
    best = {start: time}
    heap = [(time, start)]
    while heap:
        t, station = heapq.heappop(heap)
        if t > best.get(station, float("inf")):
            continue
        if station == goal:
            return t
        ready = t if station == start else t + transfer
        for line in lines:
            stops = line["stops"]
            if station not in stops:
                continue
            i = stops.index(station)
            if i == len(stops) - 1:
                continue
            offset = sum(line["minutes"][:i])
            leaving = [d + offset for d in line["departures"] if d + offset >= ready]
            if not leaving:
                continue
            clock = min(leaving)
            for j in range(i + 1, len(stops)):
                clock += line["minutes"][j - 1]
                if clock < best.get(stops[j], float("inf")):
                    best[stops[j]] = clock
                    heapq.heappush(heap, (clock, stops[j]))
    return None
''',
None)


def journey_tests(rng):
    base = [{"stops": ["A", "B", "C"], "minutes": [10, 10], "departures": [0, 30]},
            {"stops": ["B", "D"], "minutes": [5], "departures": [12, 45]}]
    tests = [[base, "A", "D", 0, 3], [base, "A", "D", 0, 2], [base, "A", "A", 17, 3], [base, "D", "A", 0, 3],
             [base, "A", "D", 31, 0], [base, "B", "D", 12, 99], [base, "B", "D", 13, 0], [base, "A", "C", 1, 5],
             [[], "A", "B", 0, 0],
             [[{"stops": ["A", "B", "C"], "minutes": [5, 5], "departures": [0]},
               {"stops": ["B", "C"], "minutes": [1], "departures": [5, 6]}], "A", "C", 0, 1],
             [[{"stops": ["A", "B"], "minutes": [5], "departures": [0, 20]},
               {"stops": ["B", "A"], "minutes": [5], "departures": [6, 26]},
               {"stops": ["A", "C"], "minutes": [1], "departures": [10, 12, 31]}], "B", "C", 0, 2]]
    names = "PQRSTUV"
    for _ in range(24):
        lines = []
        for _ in range(rng.randrange(2, 5)):
            stops = rng.sample(names, rng.randrange(2, 5))
            lines.append({"stops": stops, "minutes": [rng.randrange(1, 12) for _ in stops[1:]],
                          "departures": sorted(rng.sample(range(0, 90), rng.randrange(1, 5)))})
        tests.append([lines, rng.choice(names), rng.choice(names), rng.randrange(0, 40), rng.randrange(0, 6)])
    return tests


TASKS[-1] = TASKS[-1][:3] + (journey_tests,)


# ------------------------------------------------------------------ 7. league table

task("rank_teams", """Write a function rank_teams(matches) that produces a league table order.

`matches` is a list of [home, away, home_goals, away_goals]. Team names are strings and the goals are whole numbers. A team is in the league if it appears in at least one match. Two teams may play each other any number of times. A win is worth 3 points, a draw 1 point each, a loss 0.

Order the teams by these rules, in order:
1. More points first.
2. Then better goal difference (goals scored minus goals conceded) first.
3. Then more goals scored first.
4. Teams that are still level on all three of those form a tied group. Within each tied group, compute a mini-league using only the matches played between teams of that same group: more mini-league points first.
5. Teams in a tied group that are also level on mini-league points are ordered by name, alphabetically (ordinary string comparison).

Return the list of team names from first place to last place.

Example: rank_teams([["Ants", "Bees", 1, 0], ["Bees", "Cats", 1, 0], ["Cats", "Ants", 1, 0]]) returns ["Ants", "Bees", "Cats"], because all three are level on everything, including the mini-league, so names decide.""",
'''def rank_teams(matches):
    stats = {}
    for home, away, hg, ag in matches:
        for team in (home, away):
            stats.setdefault(team, [0, 0, 0])
        stats[home][1] += hg - ag
        stats[away][1] += ag - hg
        stats[home][2] += hg
        stats[away][2] += ag
        if hg > ag:
            stats[home][0] += 3
        elif ag > hg:
            stats[away][0] += 3
        else:
            stats[home][0] += 1
            stats[away][0] += 1
    groups = {}
    for team, key in stats.items():
        groups.setdefault(tuple(key), []).append(team)
    table = []
    for key in sorted(groups, reverse=True):
        group = groups[key]
        mini = {team: 0 for team in group}
        for home, away, hg, ag in matches:
            if home in mini and away in mini and home != away:
                if hg > ag:
                    mini[home] += 3
                elif ag > hg:
                    mini[away] += 3
                else:
                    mini[home] += 1
                    mini[away] += 1
        table.extend(sorted(group, key=lambda team: (-mini[team], team)))
    return table
''',
None)


def league_tests(rng):
    tests = [[[["Ants", "Bees", 1, 0], ["Bees", "Cats", 1, 0], ["Cats", "Ants", 1, 0]]], [[]],
             [[["Zed", "Abe", 0, 0]]], [[["Zed", "Abe", 2, 1]]],
             [[["A", "B", 1, 0], ["C", "D", 1, 0], ["B", "A", 1, 0], ["D", "C", 1, 0], ["C", "A", 2, 2]]],
             [[["A", "B", 2, 0], ["B", "A", 2, 0], ["A", "B", 1, 1], ["C", "D", 3, 1], ["D", "C", 3, 1]]],
             [[["b", "a", 1, 1], ["B", "A", 1, 1]]],
             [[["P", "Q", 1, 0], ["R", "S", 1, 0], ["Q", "R", 1, 0], ["S", "P", 1, 0],
               ["P", "R", 0, 0], ["Q", "S", 0, 0]]]]
    for _ in range(26):
        teams = rng.sample(["Ajax", "Bolt", "Crow", "Dune", "Echo", "Fury", "Gale"], rng.randrange(3, 7))
        games = []
        for _ in range(rng.randrange(3, 12)):
            home, away = rng.sample(teams, 2)
            games.append([home, away, rng.randrange(0, 3), rng.randrange(0, 3)])
        tests.append([games])
    return tests


TASKS[-1] = TASKS[-1][:3] + (league_tests,)


# ------------------------------------------------------------------ assembling

def load(reference, name):
    namespace = {}
    exec(reference, namespace)
    return namespace[name]


def DRAW_CHECK(order):
    return load(next(t for t in TASKS if t[0] == "corners_result")[2], "corners_result")(order)


def build(seed):
    questions = []
    for number, (function, prompt, reference, make_tests) in enumerate(TASKS, 1):
        solve = load(reference, function)
        rng = random.Random(f"{seed}-{function}")
        tests = []
        for args in make_tests(rng):
            args = json.loads(json.dumps(args))
            expected = json.loads(json.dumps(solve(*json.loads(json.dumps(args)))))
            tests.append([args, expected])
        questions.append({"id": f"code-h{number:02d}", "scorer": "code", "strict": True, "function": function,
                          "prompt": prompt, "tests": tests,
                          "reference": "```python\n" + reference + "```"})
    return questions
