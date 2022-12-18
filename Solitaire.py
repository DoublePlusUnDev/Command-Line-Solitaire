CONFIG_OVERRIDE = ""

INPUT_SYSTEM = "curses"
'''the game can utilize one of three ways of detecting keyboard and/or mouse presses:   curses: curses libary is required by default to play the game, it is also able to detect mouse click, however it's unable to detect seimulatneous keypresses
                                                                                        pynput: a windows-only library, can detect multiple keypresses at the same time, however can't utilize the mouse
                                                                                        keyboard: supposed to work on Linux, may also be able to detect mtultiple simultaneous button presses
'''

#IMPORTS
#note that the pynput and keyboard modules will only get imported, if they get imported at all, at setup
from copy import copy
import curses
from curses import wrapper
import random
import time
import traceback

#CONFIG
DEFAULT_RULESET = "klondike-passthroughs-0-turn-1-suits-1-empty_deal-0-winassist-1" 
'''available games and modifications:   klondike-passthroughs-0-turn-1
                                        spider-suits-1-empty_deal-0
                                        scrolltest
                                        extras: winassist-1, color_enabled-1
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
ENABLE_PERFORMANCE_LOGGING = False
FORCE_START_LINES_COLORED = False #prevents color overflow in case part of a pile is chopped off, at the price of some marginal performance

#KEYBINDINGS
INTERACT_KEYS = ["Key.space", "Key.enter", "space", "enter", " "]
QUICK_ACTION_KEYS = ["Key.shift", "Key.backspace", "shift", "backspace"]
FORWARD_KEYS = ["'w'", "Key.up", "w", "up"]
BACKWARD_KEYS = ["'s'", "Key.down", "s", "down"]
RIGHT_KEYS = ["'d'", "Key.right", "d", "right"]
LEFT_KEYS = ["'a'", "Key.left", "a", "left"]
RESTART_KEYS = ["'r'", "r"]
ESCAPE_KEYS = ["Key.esc", "esc", "^[", "\x1b"]
NUMBER_KEYS = [["'1'"], ["'2'"], ["'3'"], ["'4'"], ["'5'"], ["'6'"], ["'7'"], ["'8'"], ["'9'"]] + list(map(str, range(1, 9 + 1)))
MODIFY_KEYS = ["Key.alt_l", "alt"]

#NAVIGATION
JUMP_OVER_EMPTY_PILES = True
OVER_SCROLL = 1

#GRAPHICS
#COLORS
COLORS = {"BLACK" : 0, "BLUE" : 1, "GREEN" : 2, "CYAN" : 3, "RED" : 4, "MAGENTA" : 5, "YELLOW" : 6, "WHITE" : 7,
        "LIGHTBLACK" : 8, "LIGHTBLUE" : 9, "LIGHTGREEN" : 10, "LIGHTCYAN" : 11, "LIGHTRED" : 12, "LIGHTMAGENTA" : 13, "LIGHTYELLOW" : 14, "LIGHTWHITE" : 15}

COLORING_FORMAT = "&c"

BACKGROUND_COLOR = "GREEN"
CARD_BACKGROUND_COLOR = "LIGHTWHITE"
EMPTY_PILE_COLOR = "LIGHTGREEN"
HIGHLIGHTED_COLOR = "BLUE"
SELECTED_COLOR = "YELLOW"
CARD_TEXT_COLOR = "BLACK"
DEBUG_TEXT_COLOR = "LIGHTWHITE"

#CARD DATA
CARD_SUITS = [["♠", "BLACK"], ["♥", "LIGHTRED"], ["♣", "BLACK"], ["♦", "LIGHTRED"]]
CARD_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "0", "J", "Q", "K"]

#SPACING
LINES_BETWEEN_ROWS = 2
SPACE_BETWEEN_PILES = 3
SCREEN_BORDER_WIDTH = 1

#CARD DIMENSIONS
RENDER_HEIGHT = 30 - ENABLE_PERFORMANCE_LOGGING#53
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
#cursos data
cursor_position = 0, 0 #horizontal, verical
pile_position = 0 #card position inside pile

#selection data
is_selected = False
selected_position = 0, 0
selected_pile_position = 0 
last_click_position = 0, 0, 0

scroll_offset = 0

color_pairs = [[-1, -1]]

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
color_enabled = True

#debug and crash dumps
crash_dump_text = ""
logged_text = ""
 
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
            self.face_down = min(self.face_down, max(len(self.cards) - 1, 0))

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
                is_face_down = ((line_number - 2) // SLICE_HEIGHT + 1 <= self.face_down)

                slice_index = (line_number - 2) % SLICE_HEIGHT
                card_index = (line_number - 2) // SLICE_HEIGHT
                
                if is_face_down:
                    return self.format_card_line(CARD_BACK_SLICE[slice_index], None, card_background_color)
                else:
                    return self.format_card_line(CARD_FRONT_SLICE[slice_index], self.cards[-self.card_count() + card_index], card_background_color)
            #top cards
            elif line_number <= + CARD_HEIGHT + (self.card_count() - 1) * SLICE_HEIGHT:
                is_face_down = (self.card_count() * SLICE_HEIGHT <= self.face_down)
                if is_face_down:
                    return self.format_card_line(CARD_BACK[line_number - self.card_count()], None, card_background_color)
                else:
                    return self.format_card_line(CARD_FRONT[(line_number - 1) - SLICE_HEIGHT * (self.card_count() - 1)], self.cards[-1], card_background_color)
            #empty background
            else:
                return CARD_WIDTH * " "

    def format_card_line(self, line, card, card_background_color):
        #this function was originally meant to render the rank, the suit and its respective font color on the card line,
        #however now it handles the background coloring as well, sorry... :(
        #what's more now you've gotta use the format color function too just because fuck you
        line = line.replace("(b)", format_color(BACKGROUND_COLOR, "b")).replace("(n)", format_color(card_background_color, "b"))
        if card != None:
             line = line.replace("#", format_color(card.COLOR(), "f") + card.SUIT() + format_color(CARD_TEXT_COLOR, "f")).replace("?", format_color(card.COLOR(), "f") + card.RANK() + format_color(CARD_TEXT_COLOR, "f"))
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

    text_mode(True)

    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "Select a gamemode:")

        for i, gamemode in enumerate(GAMEMODES_TO_SELECT):
            stdscr.addstr(i + 1, 0, f"{i + 1}) {gamemode[1]}")
        stdscr.addstr(number_of_gamemodes, 0, f"{number_of_gamemodes}) custom ruleset")
        stdscr.refresh()

        selected_gamemode = stdscr.getstr(number_of_gamemodes + 1, 0).decode()
        
        if selected_gamemode in map(str, range(1, number_of_gamemodes)):
            read_ruleset(GAMEMODES_TO_SELECT[int(selected_gamemode) - 1][0])
            break
        
        elif selected_gamemode == str(number_of_gamemodes):
            stdscr.clear()
            stdscr.addstr(0, 0, "Add custom rules:")
            custom_ruleset = stdscr.getstr(1, 0).decode()

            read_ruleset(DEFAULT_RULESET)
            read_ruleset(custom_ruleset)
            break
    
    text_mode(False)

    pressed_down_keys = []

def init_curses(stdscr_instance):
    #makes stdscr globally accesible for all functions
    global stdscr

    stdscr = stdscr_instance

    curses.cbreak()
    curses.noecho()
    
    curses.curs_set(0) 
    stdscr.keypad(1) 
    curses.mousemask(1)
    
    curses.resize_term(RENDER_HEIGHT, RENDER_WIDTH + 1)
    curses.start_color()
    
def setup_input_listener():
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

    if INPUT_SYSTEM == "pynput":
        from pynput.keyboard import Listener as KeyboardListener
        keyboard_listener = KeyboardListener(on_press=on_press, on_release=on_release)
        keyboard_listener.start()

    elif INPUT_SYSTEM == "keyboard":
        import keyboard
        from keyboard._keyboard_event import KEY_DOWN, KEY_UP

        def on_action(event):
            if event.event_type == KEY_DOWN:
                on_press(event.name)

            elif event.event_type == KEY_UP:
                on_release(event.name)

        keyboard.hook(lambda e: on_action(e))

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
    global gamemode, waste_size, max_passthroughs, suits, empty_deal, win_assist, color_enabled

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

        elif rule == "colorenabled":
            color_enabled = int(ruleset[i+1]) == 1

def text_mode(enable):
    if enable:
        curses.echo()
        curses.nocbreak()

    else:
        curses.noecho()
        curses.cbreak()

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

    global input_direction, interact_input, pressed_keys, pressed_down_keys, number_input, modify_input

    input_direction = 0, 0
    interact_input = None
    number_input = 0
    modify_input = None

    #handles input from curses, mouse included
    #curses can only detect a single keypress at a time, so the list of pressed keys can be simply overwritten
    if INPUT_SYSTEM == "curses":
        curses.flushinp()
        char = stdscr.getch()

        if char == curses.KEY_MOUSE:
            handle_mouse_click()

        else:
            key = str(chr(char))

            pressed_keys = [key]
            pressed_down_keys = [key]

            #global logged_text, should_render
            #should_render = True
            #logged_text = str(pressed_keys) + str(pressed_down_keys)

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

def handle_mouse_click():
    global cursor_position, pile_position, selected_position, selected_pile_position, is_selected, should_render, interact_input, pressed_keys, last_click_position

    pressed_keys = []
    _, mx, my,_, _ = curses.getmouse()

    click_position = screen_to_card_position(mx, my)

    if click_position[0] == -1 or click_position[1] == -1 or click_position[2] == -1:
        return

    cursor_position = click_position[0], click_position[1]
    pile_position = click_position[2]

    if last_click_position == click_position:
        interact_input = "quick_action"

    else:
        interact_input = "interact"
    
    last_click_position = click_position
    should_render = True

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
    #if scrolling breaks, then likely these two lines are at fault
    elif card_boundries[1] > screen_boundries[1] - OVER_SCROLL:
        scroll_offset = card_boundries[1] - RENDER_HEIGHT + 1 + OVER_SCROLL

def try_win_assist():
    if not win_assist:
        return False

    if gamemode == "klondike":
        if len(find_piles_by_type("stock")[0].cards) != 0 or len(find_piles_by_type("waste")[0].cards) != 0:
            return False

        for tableau in find_piles_by_type("tableau"):
            if tableau.face_down != 0:
                return False

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
    #or at least it was, before I implemented curses, so now only god knows...

    def colored_string_to_buffer(string):
        buffer = []

        i = 0
        new_element = True
        
        while i < len(string):
            element = string[i]
            has_found_color = False

            #color check
            if string[i : i + len(COLORING_FORMAT)] == COLORING_FORMAT:
                element = string[i : i + len(COLORING_FORMAT) + 2]
                has_found_color = True

            if new_element:
                buffer.append(element)
            else:
                buffer[-1] += element

            i+=len(element)
            new_element = not has_found_color

        return buffer

    def parse_buffer_element(string):
        foreground_color = None
        background_color = None

        colors = string[:-1].split(COLORING_FORMAT)

        for i in range(1, len(colors)):
            color = colors[i]

            if color[1] == "f":
                foreground_color = int(ord(color[0]))

            elif color[1] == "b":
                background_color = int(ord(color[0]))

        return string[-1], foreground_color, background_color
    
    handle_scrolling()
    
    render_buffer = []
    
    for height in range(RENDER_HEIGHT):
        row = []
        for i in range(RENDER_WIDTH):
            if i == 0 and (height == 0 or FORCE_START_LINES_COLORED):
                row.append(" ")
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
    
    #display buffer on screen
    foreground_color = get_color(CARD_TEXT_COLOR)
    background_color = get_color(BACKGROUND_COLOR)
    if color_enabled:
        curses.init_pair(10, foreground_color, background_color)

    for i, row in enumerate(render_buffer):
        for j, element in enumerate(row):
            char, fore, back = parse_buffer_element(element)

            if fore != None:
                foreground_color = fore
            if back != None:
                background_color = back

            if color_enabled:
                stdscr.addstr(i, j, char, get_color_pair(foreground_color, background_color))
            else:
                stdscr.addstr(i, j, char)

    if ENABLE_PERFORMANCE_LOGGING:
        frame_time = time.time() - update_start_time
        text = f"Frame render time: {float.__round__(frame_time*1000)}ms {logged_text}"
        if color_enabled:
            stdscr.addstr(RENDER_HEIGHT - 1, 0, text, get_color_pair(DEBUG_TEXT_COLOR, BACKGROUND_COLOR))   
        else:
            stdscr.addstr(RENDER_HEIGHT - 1, 0, text)
    
    stdscr.refresh()

def main(stdscr):
    global should_render, update_start_time, last_render_time

    try:
        init_curses(stdscr)

        setup_input_listener()
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

            #curses based input seems to work better with timing disabled
            if INPUT_SYSTEM != "curses":
                sleep_time = max(UPDATE_LENGTH - (time.time() - update_start_time), 0) 
                time.sleep(sleep_time)

    #create crashdump file when game crashes
    except Exception as e:
        #create dump file
        crash_dump = open("solitaire_crashdump.txt", "w")
        crash_dump.write(f"Game has crashed. Exception: {e} If you're not the developer, please make sure to send him the exception!\n")
        crash_dump.write(f"Detailed exception:\n{traceback.format_exc()}")
        crash_dump.write(f"Additional information: {crash_dump_text}")
        crash_dump.close()

        #warn user
        stdscr.clear()
        stdscr.addstr(0, 0, "Program crashed! See crashdump for details.")
        stdscr.refresh()
        stdscr.getkey()

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

    update_row_starts()

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
                if from_pile.cards[card_i - 1].rank != from_pile.cards[card_i].rank + 1 or from_pile.cards[card_i - 1].suit != from_pile.cards[card_i].suit:
                    return False

            return True

        #virtually anything can be on an empty space
        elif to_pile.pile_type == "tableau" and len(to_pile.cards) == 0:
            return True

        #placing cards on a tableau pile
        elif to_pile.pile_type == "tableau":
            return to_pile.cards[-1].rank == from_pile.get_card(from_pile_position).rank + 1

    return False

def move_cards(from_pile, from_pile_position, to_pile):
    global is_selected, should_render

    to_pile.add(from_pile.remove_from_top(from_pile.card_count() - from_pile_position))

    should_render = True

    update_row_starts()

def check_victory():
    global has_won

    if gamemode in ["klondike", "spider"]:
        for row in piles:
            for pile in row:
                if pile != None and pile.pile_type != "foundation" and len(pile.cards) != 0:
                    return
        
        has_won = True

    if has_won:
        stdscr.getch()

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
    update_row_starts()

def screen_to_card_position(x, y):
    card_position = -1, -1, -1

    #check horizontally
    for card_x in range(len(piles[0])):
        card_x_boundries = SCREEN_BORDER_WIDTH + card_x * (CARD_WIDTH + SPACE_BETWEEN_PILES), SCREEN_BORDER_WIDTH + CARD_WIDTH + (card_x) * (CARD_WIDTH + SPACE_BETWEEN_PILES) - 1

        if card_x_boundries[0] <= x <= card_x_boundries[1]:
            card_position = card_x, -1, -1

    y += scroll_offset

    #checks vertically
    #also checks for the card position in the pile, not just for the pile's y position
    for card_y in range(len(piles)):
        #skips over pile if empty
        pile = piles[card_y][card_position[0]]
        if pile == None:
            continue

        card_y_boundries = row_starts[card_y], row_starts[card_y] + pile.get_height() - 1

        if card_y_boundries[0] <= y <= card_y_boundries[1]:
            card_position = card_position[0], card_y, -1
           
           #if the selected part is the bottom card of the pile
            if y > row_starts[card_y] + pile.get_height() - 1 - (CARD_HEIGHT - 1):
                card_position = card_position[0], card_position[1], pile.card_count() -1

            #and if it's not
            else:
                card_position = card_position[0], card_position[1], (y - row_starts[card_y] - 1) // SLICE_HEIGHT

    return card_position

#util
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

def height_of_row(pile_line):
    #get the height of the highest pile in the row
    #takes the pile slice as an input, instead of the index, perhaps later on I'll fix it
    #...or perhaps not...

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

def get_color(color):
    if type(color) is int:
        return color

    return COLORS[color]

def get_color_pair(fore, back):
    fore, back = get_color(fore), get_color(back)

    for i in range(len(color_pairs)):
        if color_pairs[i][0] == fore and color_pairs[i][1] == back:
            return curses.color_pair(i)

    curses.init_pair(len(color_pairs), fore, back)
    color_pairs.append([fore, back])
    return curses.color_pair(len(color_pairs) - 1)

def format_color(color, layer):
    #layer is either f or b
    #color number(0-255) is encoded as an ascii character in order to maintain constant length
    if curses.has_colors():
        return COLORING_FORMAT + chr(get_color(color)) + layer
    else:
        return ""

#main
if __name__ == "__main__":
    wrapper(main)
