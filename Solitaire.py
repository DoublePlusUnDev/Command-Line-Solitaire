CONFIG_OVERRIDE = ""

#IMPORTS
from copy import copy
import random
import sys
import time
import os
from pynput.keyboard import Listener
from colorama import init, Fore, Back, Style
import traceback

init(autoreset=True)

#CONFIG
DEFAULT_RULESET = "klondike-passthroughs-0-turn-1-suits-1-empty_deal-0-winassist-1" 
'''available games and modifications:   klondike-passthroughs-0-turn-1
                                        spider-suits-1-empty_deal-0
                                        scrolltest
                                        extras: winassist-1
                                        '''
                                        
GAMEMODES_TO_SELECT = [
    ["klondike-passthroughs-0-turn-1", "The classic version of Solitaire"],
    ["klondike-passthroughs-3-turn-1", "The classic version of Solitaire with three passthroughs"],
    ["klondike-passthroughs-0-turn-3", "The classic version of Solitaire in which three waste cards are turned at once"],
    ["klondike-passthroughs-3-turn-3", "The classic version of Solitaire in which three waste cards are turned at once with three passthroughs"],
    ["spider-suits-1-empty_deal-0", "Spider solitaire with one suit"],
    ["spider-suits-2-empty_deal-0", "Spider solitaire with two suits"],
    ["spider-suits-3-empty_deal-0", "Spider solitaire with three suits"],
    ["spider-suits-4-empty_deal-0", "Spider solitaire with four suits"],]

FRAME_MIN_WAIT = 0.3
UPDATE_LENGTH = 0.01
ENABLE_PERFORMANCE_LOGGING = True
FORCE_START_LINES_COLORED = False #prevents color overflow in case part of a pile is chopped off, at the price of some marginal performance

#KEYBINDINGS
INTERACT_KEYS = ["Key.space", "Key.enter"]
QUICK_ACTION_KEYS = ["Key.shift", "Key.backspace"]
FORWARD_KEYS = ["'w'", "Key.up"]
BACKWARD_KEYS = ["'s'", "Key.down"]
RIGHT_KEYS = ["'d'", "Key.right"]
LEFT_KEYS = ["'a'", "Key.left"]
RESTART_KEYS = ["'r'"]
ESCAPE_KEYS = ["Key.esc"]
NUMBER_KEYS = [["'1'"], ["'2'"], ["'3'"], ["'4'"], ["'5'"], ["'6'"], ["'7'"], ["'8'"], ["'9'"]]  
MODIFY_KEYS = ["Key.alt_l"]

#NAVIGATION
JUMP_OVER_EMPTY_PILES = True
OVER_SCROLL = 1

#GRAPHICS
#COLORS
BACKGROUND_COLOR = Back.GREEN
CARD_BACKGROUND_COLOR = Back.LIGHTWHITE_EX
EMPTY_PILE_COLOR = Back.LIGHTGREEN_EX
HIGHLIGHTED_COLOR = Back.BLUE
SELECTED_COLOR = Back.YELLOW
CARD_TEXT_COLOR = Fore.BLACK

COLORS = [Fore.BLACK, Fore.BLUE, Fore.CYAN, Fore.GREEN, Fore.MAGENTA, Fore.RED, Fore.WHITE, Fore.YELLOW, Fore.LIGHTBLACK_EX, Fore.LIGHTBLUE_EX, Fore.LIGHTCYAN_EX, Fore.LIGHTGREEN_EX, Fore.LIGHTMAGENTA_EX, Fore.LIGHTRED_EX, Fore.LIGHTWHITE_EX, Fore.LIGHTYELLOW_EX,\
    Back.BLACK, Back.BLUE, Back.CYAN, Back.GREEN, Back.MAGENTA, Back.RED, Back.WHITE, Back.YELLOW, Back.LIGHTBLACK_EX, Back.LIGHTBLUE_EX, Back.LIGHTCYAN_EX, Back.LIGHTGREEN_EX, Back.LIGHTMAGENTA_EX, Back.LIGHTRED_EX, Back.LIGHTWHITE_EX, Back.LIGHTYELLOW_EX]

#CARD DATA
CARD_SUITS = [["♠", Fore.BLACK], ["♥", Fore.LIGHTRED_EX], ["♣", Fore.BLACK], ["♦", Fore.LIGHTRED_EX]]
CARD_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "0", "J", "Q", "K"]

#SPACING
LINES_BETWEEN_ROWS = 2
SPACE_BETWEEN_PILES = 3
SCREEN_BORDER_WIDTH = 1

#CARD DIMENSIONS
RENDER_HEIGHT = 29 - ENABLE_PERFORMANCE_LOGGING#53
RENDER_WIDTH = 119#210
CARD_HEIGHT = 6
CARD_WIDTH = 9
SLICE_HEIGHT = 1

#CARD TEXTURES
CARD_FRONT = """
 _______ 
|(n)?     #(b)|
|(n)       (b)|
|(n)   ?#  (b)|
|(n)       (b)|
|(n)#_____?(b)|"""

CARD_FRONT_SLICE = """
|(n)?_____#(b)|"""

CARD_BACK = """
 _______ 
|(n)\     /(b)|
|(n) \   / (b)|
|(n)  | |  (b)|
|(n) /   \ (b)|
|(n)/_____\(b)|"""

CARD_BACK_SLICE = """
|(n)\_____/(b)|"""

CARD_EMPTY = """
 _______ 
|(n)       (b)|
|(n)       (b)|
|(n)       (b)|
|(n)       (b)|
|(n)_______(b)|"""

#DEBUG
FACE_UP_DEBUG = False

#VARIABLES
cursor_position = 0, 0 #horizontal, verical
pile_position = 0 #card position inside pile

#selection data
is_selected = False
selected_position = 0, 0
selected_pile_position = 0 

scroll_offset = 0

#rules
gamemode = "klondike"
waste_size = 1
suits = 1
max_passthroughs = 0
remaining_passthroughs = 0
empty_deal = False

win_assist = True

should_render = True #gets set to false after each render, is set to true when something changes and needs to be rendered
has_won = False
 
#CLASSES
class Pile:
    face_down = 0 #cards are face down to the n-th card(n-th card included)

    def __init__(self, pile_type):
        self.pile_type = pile_type
        self.cards = []

        if pile_type == "stock":
            self.face_down = 1
        
    def add(self, cards):
        self.cards += cards

    def remove_from_top(self, number_of_cards):
        removed_cards = self.cards[-number_of_cards:]
        self.cards = self.cards[:-number_of_cards]
        if self.pile_type in "tableau":
            self.face_down = min(self.face_down, len(self.cards) - 1)

        return removed_cards

    def get_card(self, i):
        if self.pile_type in ["waste", "foundation"]:
            return self.cards[-1]
        
        else:
            return self.cards[i]

    def get_line(self, line_number):
        #first line starts at 1
        #DO NOT TOUCH THESE DAMNED LINES OF CODE UNLESS YOU INTEND TO LOSE THE LAST SLIVER OF YOUR REMAINING SANITY

        #choosing the appropriate background color for the card 
        card_background_color = CARD_BACKGROUND_COLOR
        if highlighted_pile() == self and (line_number > pile_position * SLICE_HEIGHT + 1 and (line_number <= (pile_position + 1) * SLICE_HEIGHT + 1 or pile_position == self.card_count() - 1)):
            card_background_color = HIGHLIGHTED_COLOR
        elif (is_selected and selected_pile() == self) and line_number > selected_pile_position * SLICE_HEIGHT + 1:
            card_background_color = SELECTED_COLOR
        elif len(self.cards) == 0:
            card_background_color = EMPTY_PILE_COLOR

        #returning the line
        #invalid line(above the start of the screen)
        if line_number <= 0:
            return CARD_WIDTH * " "

        #empty pile
        elif len(self.cards) == 0:
            if len(CARD_EMPTY) >= line_number:
                return self.format_card_line(CARD_EMPTY[line_number - 1], None, card_background_color)
            else:
                return CARD_WIDTH * " "
        
        #render normal pile
        else:
            #pile top
            if line_number == 1:
                if self.face_down > 0:
                    return CARD_BACK[0]
                else:
                    return CARD_FRONT[0]
            #card slices
            if line_number <= (self.card_count() - 1) * SLICE_HEIGHT + 1:
                face_down = ((line_number - 2) // SLICE_HEIGHT + 1 <= self.face_down)

                slice_index = (line_number - 2) % SLICE_HEIGHT
                card_index = (line_number - 2) // SLICE_HEIGHT
                
                if face_down:
                    return self.format_card_line(CARD_BACK_SLICE[slice_index], None, card_background_color)
                else:
                    return self.format_card_line(CARD_FRONT_SLICE[slice_index], self.cards[-self.card_count() + card_index], card_background_color)
            #top cards
            elif line_number <= + CARD_HEIGHT + (self.card_count() - 1) * SLICE_HEIGHT:
                face_down = (self.card_count() * SLICE_HEIGHT <= self.face_down)
                if face_down:
                    return self.format_card_line(CARD_BACK[line_number - self.card_count()], None, card_background_color)
                else:
                    return self.format_card_line(CARD_FRONT[(line_number - 1) - SLICE_HEIGHT * (self.card_count() - 1)], self.cards[-1], card_background_color)
            #empty background
            else:
                return CARD_WIDTH * " "

    def format_card_line(self, line, card, card_background_color):
        #this function was originally meant to render the rank, the suit and its respective font color on the card line,
        #however now it handles the background coloring as well, sorry... :(
        line = line.replace("(b)", BACKGROUND_COLOR).replace("(n)", card_background_color)
        if card != None:
             line = line.replace("#", card.COLOR() + card.SUIT() + CARD_TEXT_COLOR).replace("?", card.COLOR() + card.RANK() + CARD_TEXT_COLOR)
        return line

    def card_count(self):
        #returns how many cards, the pile is meant to display
        if self.pile_type == "waste" and len(self.cards) != 0:
            return min(waste_size, len(self.cards))

        elif self.pile_type in ["foundation", "stock"] or len(self.cards) == 0:
            return 1

        else:
            return len(self.cards)

    def get_height(self):
        #returns in how many lines, depending on the card count of course, the card is supposed to be rendered
        if self.pile_type == "waste":
            return CARD_HEIGHT + (waste_size - 1) * SLICE_HEIGHT

        else:
            return CARD_HEIGHT + (self.card_count() - 1) * SLICE_HEIGHT

class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank

    def __str__(self):
        return f"{self.suit} {self.rank}"

    def SUIT(self):
        return CARD_SUITS[self.suit - 1][0]

    def RANK(self):
        return CARD_RANKS[self.rank - 1]

    def COLOR(self):
        return CARD_SUITS[self.suit - 1][1]

#FUNCTIONS
#setup
def select_gamemode():
    global pressed_down_keys

    number_of_gamemodes = len(GAMEMODES_TO_SELECT) + 1

    while True:
        clear_screen()
        print("Choose a gamemode")
        for i, gamemode in enumerate(GAMEMODES_TO_SELECT):
            print(f"{i + 1}) {gamemode[1]}")
        print(f"{number_of_gamemodes}) custom ruleset")

        selected_gamemode = input()

        if selected_gamemode in map(str, range(1, number_of_gamemodes)):
            read_ruleset(GAMEMODES_TO_SELECT[int(selected_gamemode) - 1][0])
            break
        
        elif selected_gamemode == str(number_of_gamemodes):
            custom_ruleset = input()
            read_ruleset(DEFAULT_RULESET)
            read_ruleset(custom_ruleset)
            break

    pressed_down_keys = []

def setup_keyboard_listener():
    global pressed_keys, pressed_down_keys

    pressed_keys = []
    pressed_down_keys = []

    def on_press(key):
        if not pressed_keys.__contains__(str(key)):
            pressed_keys.append(str(key))
            pressed_down_keys.append(str(key))

    def on_release(key):
        if pressed_keys.__contains__(str(key)):
            pressed_keys.remove(str(key))

    keyboard_listener = Listener(on_press=on_press, on_release=on_release)
    keyboard_listener.start()

def setup_card_textures():
    global CARD_FRONT, CARD_FRONT_SLICE, CARD_BACK, CARD_BACK_SLICE, CARD_EMPTY

    CARD_FRONT = CARD_FRONT.split("\n")
    CARD_FRONT.remove("")

    CARD_FRONT_SLICE = CARD_FRONT_SLICE.split("\n")
    CARD_FRONT_SLICE.remove("")

    CARD_BACK = CARD_BACK.split("\n")
    CARD_BACK.remove("")

    CARD_BACK_SLICE = CARD_BACK_SLICE.split("\n")
    CARD_BACK_SLICE.remove("")

    CARD_EMPTY = CARD_EMPTY.split("\n")
    CARD_EMPTY.remove("")

def read_ruleset(ruleset):
    global gamemode, waste_size, max_passthroughs, suits, empty_deal, win_assist

    ruleset = ruleset.replace(" ", "").replace("\n", "").replace("_", "").lower().split("-")

    for i, rule in enumerate(ruleset):
        if rule in ["klondike", "spider", "pyramid", "scrolltest"]:
            gamemode = rule

        elif rule == "turn":
            waste_size = int(ruleset[i+1])

        elif rule == "passthroughs":
            max_passthroughs = int(ruleset[i+1])

        elif rule == "suits":
            suits = int(ruleset[i+1]) 

        elif rule == "emptydeal":
            empty_deal = int(ruleset[i+1]) == 1

        elif rule == "winassist":
            win_assist = int(ruleset[i+1]) == 1

#game loop 
def read_input():
    def overlap(list1, list2):
        return any (x in list1 for x in list2)

    def key_press(keys, press_type="any"):
        global pressed_keys, pressed_down_keys

        if press_type == "down":
            return overlap(pressed_down_keys, keys)
        else:
            return overlap(pressed_keys, keys)

    global input_direction, interact_input, pressed_down_keys, number_input, modify_input

    input_direction = 0, 0
    interact_input = None
    number_input = 0

    if key_press(ESCAPE_KEYS, press_type="down"):
        interact_input = "escape"
    elif key_press(RESTART_KEYS, press_type="down"):
        interact_input = "restart"
    elif key_press(QUICK_ACTION_KEYS, press_type="down"):
        interact_input = "quick_action"
    elif key_press(INTERACT_KEYS, press_type="down"):
        interact_input = "interact"
    elif key_press(FORWARD_KEYS):
        input_direction = 0, 1
    elif key_press(BACKWARD_KEYS):
        input_direction = 0, -1
    elif key_press(RIGHT_KEYS):
        input_direction = 1, 0
    elif key_press(LEFT_KEYS):
        input_direction = -1, 0
    else:
        for i in range(0, 9):
            if key_press(NUMBER_KEYS[i], "down"):
                number_input = i + 1
                break

    modify_input = key_press(MODIFY_KEYS)

    pressed_down_keys = []

def handle_input():
    global should_render, cursor_position, pile_position, is_selected, selected_position, selected_pile_position

    #exit
    if interact_input == "escape":
        back_to_gamemode_selection()

    #restart
    elif interact_input == "restart":
        restart_game()

    #special quick action, finds and executes best valid move
    elif interact_input == "quick_action":
        if can_deal_stock():
            deal_stock()

        else:
            for to_pile in find_piles_by_type("foundation") + find_piles_by_type("tableau"):
                if can_select(highlighted_pile(), pile_position) and can_move_cards(from_pile=highlighted_pile(), from_pile_position=pile_position, to_pile=to_pile):
                    move_cards(from_pile=highlighted_pile(), from_pile_position=pile_position, to_pile=to_pile)
                    pile_position = highlighted_pile().card_count() - 1

                    if cursor_position == selected_position:
                        is_selected = False

                    return

    #selecting card for further movement
    elif interact_input == "interact":
        #check if stock can be dealt
        if can_deal_stock():
            deal_stock()
            
        #tries moving cards to highlighted pile
        elif is_selected and can_move_cards(from_pile=selected_pile(), from_pile_position=selected_pile_position, to_pile=highlighted_pile()):
            move_cards(from_pile=selected_pile(), from_pile_position=selected_pile_position, to_pile=highlighted_pile())
            pile_position = highlighted_pile().card_count() - 1
            is_selected = False
            should_render = True

        #deselects selected position if highlighted position is over it
        elif is_selected and cursor_position == selected_position and pile_position == selected_pile_position:
            is_selected = False
            should_render = True

        #tries selecting highlighted position
        elif can_select(highlighted_pile(), pile_position):
            selected_position = cursor_position
            selected_pile_position = pile_position
            is_selected = True
            should_render = True

    #number input
    elif number_input != 0 and number_input <= len(piles) and number_input - 1 != cursor_position[1]:
        if piles[number_input - 1][cursor_position[0]] != None or not JUMP_OVER_EMPTY_PILES:
            next_position = cursor_position[0], number_input - 1

        else:
            next_position = 0, number_input - 1

            while piles[next_position[1]][next_position[0]] == None and next_position[0] < len(piles[0]) - 1:
                next_position = next_position[0] + 1, next_position[1]
            
        if piles[next_position[1]][next_position[0]] != None:
            cursor_position = next_position
            pile_position = highlighted_pile().card_count() - 1

            should_render = True

    #horizontal
    elif input_direction[0] != 0:
        next_position = min(max(cursor_position[0] + input_direction[0], 0), len(piles[0]) - 1), cursor_position[1]
        
        while JUMP_OVER_EMPTY_PILES and piles[next_position[1]][next_position[0]] == None and 0 <= next_position[0] < len(piles[0]):
            next_position = next_position[0] + input_direction[0], next_position[1]
        
        if (piles[next_position[1]][0] != None or not JUMP_OVER_EMPTY_PILES) and cursor_position != next_position:
            cursor_position = next_position
            if highlighted_pile() != None:
                pile_position = highlighted_pile().card_count() - 1
            else:
                pile_position = 0
            should_render = True

    #vertical
    elif input_direction[1] != 0:
        next_pile_position = pile_position

        if modify_input and input_direction[1] == 1:
            next_pile_position = highlighted_pile().card_count() - 1

            while can_select(highlighted_pile(), next_pile_position - 1):
                next_pile_position -= 1
        
        elif modify_input and input_direction[1] == -1:
           next_pile_position = highlighted_pile().card_count() - 1

        else:
            next_pile_position -= input_direction[1]
        
        next_position = cursor_position

        #upward input when on top of the pile
        if next_pile_position < 0:
            next_position = next_position[0], max(next_position[1] - 1, 0)

        #downward input when at the bottom of the pile
        elif next_pile_position >= highlighted_pile().card_count():
            next_position = next_position[0], min(next_position[1] + 1, len(piles) - 1)

        if next_position != cursor_position:
            while JUMP_OVER_EMPTY_PILES and piles[next_position[1]][next_position[0]] == None and 0 < next_position[1] < len(piles) - 1:
                next_position = next_position[0], input_direction[1]

            if piles[next_position[1]][next_position[0]] != None or not JUMP_OVER_EMPTY_PILES:
                cursor_position = next_position
                if highlighted_pile() != None:
                    next_pile_position = highlighted_pile().card_count() - 1
                else:
                    next_pile_position = 0

                should_render = True

        next_pile_position = min(max(next_pile_position, 0), highlighted_pile().card_count() - 1)

        if next_pile_position != pile_position:
            pile_position = next_pile_position
            should_render = True

def handle_scrolling():
    def highlighted_boundries():
        start = row_starts[cursor_position[1]] + pile_position * SLICE_HEIGHT

        if pile_position == highlighted_pile().card_count() - 1:
            end = start + CARD_HEIGHT - 1
        
        else:
            end = start + SLICE_HEIGHT - 1
        
        return start, end


    global scroll_offset

    card_boundries = highlighted_boundries()
    screen_boundries = scroll_offset, RENDER_HEIGHT - 1 + scroll_offset

    #top of screen is aligned with the top of highlighted card
    if card_boundries[0] < screen_boundries[0]:
        scroll_offset = card_boundries[0]

    #bottom of screen is aligned with the bottom of highlighted card
    elif card_boundries[1] > screen_boundries[1]:
        scroll_offset = card_boundries[1] - screen_boundries[1] + OVER_SCROLL

def try_win_assist():
    if not win_assist:
        return False

    if gamemode == "klondike":
        if len(find_piles_by_type("stock")[0].cards) == 0 and len(find_piles_by_type("waste")[0].cards) == 0:
            for tableau in find_piles_by_type("tableau"):
                for foundation in find_piles_by_type("foundation"):
                    if can_move_cards(tableau, tableau.card_count() - 1, foundation):
                        move_cards(tableau, tableau.card_count() - 1, foundation)
                        return True

    elif gamemode == "spider":
        for tableau in find_piles_by_type("tableau"):
            if len(tableau.cards) < 13:
                continue
            
            start_i = len(tableau.cards) - 13

            for card_i in range(start_i + 1, len(tableau.cards)):
                if tableau.cards[card_i - 1].rank != tableau.cards[card_i].rank + 1 or tableau.cards[card_i].suit != tableau.cards[card_i].suit:
                    return False

            empty_foundation = None
            for foundation in find_piles_by_type("foundation"):
                if len(foundation.cards) == 0:
                    empty_foundation = foundation
                    break

            move_cards(tableau, start_i, empty_foundation)

            return True

    return False

def render():
    #constructing the render buffer virtually takes no time, the main performance bottlenecks are the print and clean calls
    def height_of_row(pile_line):
        #get the height of the highest pile in the row
        max_height = 1

        for pile in pile_line:
            if pile != None and pile.get_height() > max_height:
                max_height = pile.get_height() + LINES_BETWEEN_ROWS

        return max_height

    def update_row_starts():
        global row_starts
        row_starts = []

        current_line = 0

        for row in piles:
            row_starts.append(current_line)
            row_height = height_of_row(row)
            current_line += row_height

    def colored_string_to_buffer(string):
        buffer = []

        i = 0
        new_element = True

        while i < len(string):
            element = string[i]
            has_found_color = False

            for color in COLORS:
                if string[i:i+len(color)] == color:
                    element = color
                    has_found_color = True
                    break

            if new_element:
                buffer.append(element)
            else:
                buffer[-1] += element

            i+=len(element)
            new_element = not has_found_color

        return buffer

    update_row_starts()
    
    handle_scrolling()

    clear_screen()
    
    render_buffer = []
    
    for height in range(RENDER_HEIGHT):
        row = []
        for i in range(RENDER_WIDTH):
            if i == 0 and (height == 0 or FORCE_START_LINES_COLORED):
                row.append(BACKGROUND_COLOR + CARD_TEXT_COLOR + " ")
            else:
                row.append(" ")

        render_buffer.append(row)

    if gamemode == "pyramid":
        pass
    else:
        for row_i, row in enumerate(piles):
            row_height = height_of_row(row)
            start = row_starts[row_i]

            for height in range(row_height):
                y_pos = start + height - scroll_offset
                if not(0 <= y_pos < len(render_buffer)):
                    continue

                for pile_i, pile in enumerate(row):
                    if pile != None:
                        card_line_buffer = colored_string_to_buffer(pile.get_line(height + 1))
                        x_pos = SCREEN_BORDER_WIDTH + pile_i * (CARD_WIDTH + SPACE_BETWEEN_PILES)
                        for i in range(len(card_line_buffer)):
                            if x_pos + i >= RENDER_WIDTH:
                                break

                            render_buffer[y_pos][x_pos + i] = str(card_line_buffer[i])
    
    to_print = ""
    for i, row in enumerate(render_buffer):
        to_print += ("".join(row))
        to_print += "\n"
    
    print(to_print, end="")

    if ENABLE_PERFORMANCE_LOGGING:
        print(f"Frame render time: {float.__round__((time.time() - update_start_time)*1000)}ms", end="")    

def main():
    global should_render, update_start_time, last_render_time

    setup_keyboard_listener()
    setup_card_textures()

    select_gamemode()
    reset_game_state()

    should_render = True
    last_render_time = 0

    while True:
        update_start_time = time.time()

        if last_render_time + FRAME_MIN_WAIT <= time.time():
            #if winassist is enabled, tries to complete automatic moves
            if try_win_assist():
                should_render = True

            #otherwise rely on player input
            else:
                read_input()
                handle_input()     

            #if something has changed render
            if should_render:
                render()
                should_render = False
                last_render_time = time.time()

            #check if the game has been won
            check_victory()

        time.sleep(max(UPDATE_LENGTH - (time.time() - update_start_time), 0))

#game state
def restart_game():
    reset_game_state()

def back_to_gamemode_selection():
    select_gamemode()
    reset_game_state()

def reset_game_state():
    global should_render, cursor_position, pile_position, selected_position, is_selected, selected_pile_position, remaining_passthroughs

    cursor_position = 0, 0
    pile_position = 0
    selected_position = 0, 0
    selected_pile_position = 0
    is_selected = False

    remaining_passthroughs = max_passthroughs - 1

    deal_cards()
    should_render = True

def deal_cards():
    def create_cards(sets, suits, ranks, shuffle = True):
        cards = []

        for _ in range(sets):
            for suit in suits:
                for rank in ranks:
                    cards.append(Card(suit, rank))

        if shuffle:
            random.shuffle(cards)

        return cards

    global piles, should_render
    should_render = True

    piles = []

    if gamemode == "klondike":
        cards = create_cards(1, range(1, 4 + 1), range(1, 13 + 1))
        
        piles = [[], []]
        stock = Pile("stock")
        piles[0].append(stock)
        stock.add(cards[:24])
        
        waste = Pile("waste")
        piles[0].append(waste)

        piles[0].append(None)

        for _ in range(4):
            foundation = Pile("foundation")
            piles[0].append(foundation)

        start = 24
        for i in range(1, 7 + 1):
            pile = Pile("tableau")
            piles[1].append(pile)
            pile.face_down = i - 1
            pile.add(cards[start : start + i])
            start += i

    elif gamemode == "spider":
        if suits in [1, 2, 4]:
            cards = create_cards(2 * int(4 / suits), range(1, suits + 1), range(1, 13 + 1))
        elif suits == 3:
            cards = create_cards(4, range(1, 1 + 1), range(1, 13 + 1)) + create_cards(2, range(2, 3 + 1), range(1, 13 + 1))
            random.shuffle(cards)

        piles = [[], []]
        stock = Pile("stock")
        piles[0].append(stock)
        stock.add(cards[:50])

        piles[0].append(None)

        for _ in range(8):
            foundation = Pile("foundation")
            piles[0].append(foundation)

        start = 50
        for i in range(1, 10 + 1):
            pile = Pile("tableau")
            piles[1].append(pile)
            number_of_cards = 5
            if i <= 4:
                number_of_cards = 6

            pile.add(cards[start : start + number_of_cards])
            pile.face_down = number_of_cards - 1
            start += number_of_cards

    elif gamemode == "scrolltest":
        cards = create_cards(10, range(1, 4+1), range(1, 13 + 1))

        piles = []

        i = 0
        for y in range(3):
            piles.append([])
            for x in range(7):
                number_of_cards = y * 7 + x

                pile = Pile("tableau")
                pile.add(cards[i:i+number_of_cards])
                piles[y].append(pile)
                i += number_of_cards

#cards
def can_select(pile, pile_position):
    if len(pile.cards) < 1 or pile == None or pile.face_down > pile_position:
        return False

    if gamemode == "klondike":
        if pile.pile_type in ["foundation"]:
            return True

        elif pile.pile_type == "waste":
            return pile_position == min(waste_size, len(pile.cards)) - 1

        elif pile.pile_type == "tableau":
            for i in range(pile_position, len(pile.cards) - 1):
                if pile.cards[i].rank != pile.cards[i + 1].rank + 1 or pile.cards[i].suit % 2 == pile.cards[i + 1].suit % 2:
                    return False

            return True

    elif gamemode == "spider":
        if pile.pile_type in ["foundation"]:
            return False

        elif pile.pile_type == "tableau":
            for i in range(pile_position, len(pile.cards) - 1):
                if pile.cards[i].rank != pile.cards[i + 1].rank + 1 or pile.cards[i].suit != pile.cards[i + 1].suit:
                    return False

            return True

    return False

def can_move_cards(from_pile, from_pile_position, to_pile):
    if len(from_pile.cards) == 0 or from_pile == to_pile or from_pile_position < from_pile.face_down or from_pile_position >= len(from_pile.cards):
        return False

    if gamemode == "klondike":
        #check foundation, ensured that only top card can be placed onto the foundation
        if to_pile.pile_type == "foundation" and from_pile_position + 1 == from_pile.card_count():
            return (len(to_pile.cards) == 0 and from_pile.cards[-1].rank == 1) or\
                   (len(to_pile.cards) != 0 and from_pile.cards[-1].rank == to_pile.cards[-1].rank + 1 and from_pile.cards[-1].suit == to_pile.cards[-1].suit)
           
        #empty tableau pile, king can be placed on it
        elif to_pile.pile_type == "tableau" and len(to_pile.cards) == 0:
            return from_pile.get_card(from_pile_position).rank == 13

        #placing cards on a tableau pile
        elif to_pile.pile_type == "tableau":
            return to_pile.cards[-1].rank == from_pile.get_card(from_pile_position).rank + 1 and to_pile.cards[-1].suit % 2 != from_pile.get_card(from_pile_position).suit % 2

    elif gamemode == "spider":
        #check if card belongs to a pile with a full set
        if to_pile.pile_type == "foundation" and len(to_pile.cards) == 0 and len(from_pile.cards) - from_pile_position == 13 and from_pile.cards[from_pile_position].rank == 13:
            for card_i in range(pile_position + 1, len(from_pile.cards)):
                if from_pile.cards[card_i - 1].rank != from_pile.cards[card_i].rank + 1 or from_pile.cards[card_i].suit != from_pile.cards[card_i].suit:
                    return False

            return True

        #virtually anything can be on an empty space
        elif to_pile.pile_type == "tableau" and len(to_pile.cards) == 0:
            return True

        #placing cards on a tableau pile
        elif to_pile.pile_type == "tableau":
            return to_pile.cards[-1].rank == from_pile.get_card(from_pile_position).rank + 1 and to_pile.cards[-1].suit == from_pile.get_card(from_pile_position).suit

    return False

def move_cards(from_pile, from_pile_position, to_pile):
    global is_selected, should_render

    to_pile.add(from_pile.remove_from_top(from_pile.card_count() - from_pile_position))
    should_render = True

def check_victory():
    global has_won

    if gamemode in ["klondike", "spider"]:
        for row in piles:
            for pile in row:
                if pile != None and pile.pile_type != "foundation" and len(pile.cards) != 0:
                    return
        
        has_won = True

    if has_won:
        print("\nCongrats, you've won!")
        input()

        has_won = False
        restart_game()

def can_deal_stock():
    return highlighted_pile().pile_type == "stock" or (highlighted_pile().pile_type == "waste" and len(highlighted_pile().cards) == 0)

def deal_stock():
    global should_render, pile_position, is_selected, remaining_passthroughs

    stock = find_piles_by_type("stock")[0]

    if gamemode == "klondike":
        waste = find_piles_by_type("waste")[0]
        if len(stock.cards) > 0:
            waste.add(stock.cards[0:waste_size])
            stock.cards = stock.cards[waste_size:]
            pile_position = highlighted_pile().card_count() - 1
            should_render = True

        elif len(waste.cards) > 0 and remaining_passthroughs != 0:
            stock.cards = copy(waste.cards)
            waste.cards = []
            remaining_passthroughs -= 1
            should_render = True
        
    elif gamemode == "spider":
        if len(stock.cards) > 0:
            #check if there are empty tableau piles before dealing stock
            for tableau in find_piles_by_type("tableau"):
                if len(tableau.cards) == 0 and not empty_deal:
                    return

            for tableau in find_piles_by_type("tableau"):
                tableau.add(stock.remove_from_top(1))
        
        should_render = True

    is_selected = False

#util
def clear_screen():
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")

def find_piles_by_type(pile_type):
    found_piles = []

    for row in piles:
        for pile in row:
            if pile != None and pile.pile_type == pile_type:
                found_piles.append(pile)

    return found_piles

def highlighted_pile():
    return piles[cursor_position[1]][cursor_position[0]]

def selected_pile():
    return piles[selected_position[1]][selected_position[0]]

#main
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(Fore.RED + f"Game has crashed. Exception: {e} If you're not the developer, please make sure to send him the exception!")
        print(Fore.WHITE + f"Detailed exception:\n{traceback.format_exc()}")
        while True:
            input()