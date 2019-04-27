import pygame
import time
import sys
import sqlite3
import logging
import os
import argparse
from time import gmtime, strftime

# Constants for game states (not necessarily listed in order)
BATCH_START = 0
ACCEPT_INPUT = 10
PRESENT_WORD = 20
CORRECT_GUESS = 30
INCORRECT_GUESS = 40
DISPLAY_WAIT = 50
SKIP_WORD = 60
WAIT_FOR_NEW_WORD = 70
BATCH_END = 80

# Number of milliseconds to keep a word displayed on the screen after state change
SPLASH_DELAY = 500

# Force debug mode on all the time?
debug_on = False

################################################################################
# Error constants                                                              #
################################################################################

CANNOT_CONNECT_TO_DATABASE = 1

# Get the directory that we're currently running from
current_directory = os.path.realpath(os.path.dirname(sys.argv[0]))

start_time = gmtime()
log_directory = current_directory + os.sep + "logs"

log_file_name = log_directory + os.sep + "sightright_"
log_file_name += str(start_time.tm_year).zfill(4)
log_file_name += str(start_time.tm_mon).zfill(2)
log_file_name += str(start_time.tm_mday).zfill(2)
log_file_name += "_"
log_file_name += str(start_time.tm_hour).zfill(2)
log_file_name += str(start_time.tm_min).zfill(2)
log_file_name += str(start_time.tm_sec).zfill(2)
log_file_name += ".log"

################################################################################
# Check and create log directory                                               #
################################################################################
if not os.path.isdir(log_directory):
    try:
        os.mkdir(log_directory)
    except:
        logger.error("Log directory does not exist and could not be created. Exiting...")
        quit_sightright(2)

################################################################################
# Set up logger                                                                #
################################################################################
logger = logging.getLogger('sightright')

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

disk_file_handler = logging.FileHandler(filename=log_file_name)
disk_file_handler.setFormatter(formatter)
console_log_stream_handler = logging.StreamHandler()
console_log_stream_handler.setFormatter(formatter)

logger.setLevel(logging.INFO)
console_log_stream_handler.setLevel(logging.INFO)

# Print log messages to the console, also
logger.addHandler(console_log_stream_handler)
logger.addHandler(disk_file_handler)

def does_database_exist(curr_loc):
    """
    Checks for presence of database in curr_loc folder
    Returns 1 if database exists, 0 if it does not
    """
    db_name = "sightright.db"
    if os.path.exists(curr_loc + os.sep + db_name):
        return 1
    else:
        return 0

def setup_database(cur, conn):
    """
    Set up the tables in the database.
    """
    cmd = "CREATE TABLE phrases (phrase, list, enabled, difficulty);"
    cur.execute(cmd)
    cmd = "CREATE TABLE batches (batch_id, start_time, end_time);"
    cur.execute(cmd)
    cmd = "CREATE TABLE response_history (batch_id, phrase_id, response_time_ms, response_status);"
    cur.execute(cmd)
    conn.commit()

# def print_debug(message):
#     global debug_on
#     if debug_on:
#         print("DEBUG: %s" % message)

def update_display():
    global sight_word_font
    global display_width
    global display_height
    global game_display

    global current_word
    global game_state
    global score

    background = pygame.Surface(game_display.get_size())
    background = background.convert()

    if game_state == PRESENT_WORD:
        background_color = white
        text_color = black
        word = current_word

        background.fill(background_color)

    elif game_state == CORRECT_GUESS:
        background_color = green
        text_color = white
        word = current_word

        answer_delay_text = "Answer time: %d ms" % answer_delay_ms

        background.fill(background_color)

        answer_delay_surface = controls_font.render(answer_delay_text, True, text_color)
        answer_delay_rectangle = answer_delay_surface.get_rect()
        answer_delay_rectangle.center = (display_width/2, int(display_height*3/4))
        background.blit(answer_delay_surface, answer_delay_rectangle)

    elif game_state == INCORRECT_GUESS:
        background_color = black
        text_color = white
        word = current_word

        answer_delay_text = "Answer time: %d ms" % answer_delay_ms

        background.fill(background_color)

        answer_delay_surface = controls_font.render(answer_delay_text, True, text_color)
        answer_delay_rectangle = answer_delay_surface.get_rect()
        answer_delay_rectangle.center = (display_width/2, int(display_height*3/4))
        background.blit(answer_delay_surface, answer_delay_rectangle)
    elif game_state == SKIP_WORD:
        background_color = white
        text_color = black
        word = ""

        background.fill(background_color)
    elif game_state == WAIT_FOR_NEW_WORD:
        background_color = white
        text_color = black
        word = ""

        background.fill(background_color)

        continue_control_text = "Press Space to continue"
        continue_control_surface = controls_font.render(continue_control_text, True, text_color)
        continue_control_rectangle = continue_control_surface.get_rect()
        continue_control_rectangle.midbottom = (display_width/2, display_height)
        background.blit(continue_control_surface, continue_control_rectangle)

    quit_control_text = "Esc: Quit"
    quit_control_surface = controls_font.render(quit_control_text, True, text_color)
    quit_control_rectangle = quit_control_surface.get_rect()
    quit_control_rectangle.topleft = (0, 0)
    background.blit(quit_control_surface, quit_control_rectangle)

    score_control_text = "Score: %d (%d%%)" % (score, int((score/total_words)*100))
    score_control_surface = controls_font.render(score_control_text, True, text_color)
    score_control_rectangle = score_control_surface.get_rect()
    score_control_rectangle.topright = (display_width, 0)
    background.blit(score_control_surface, score_control_rectangle)

    progress_control_text = "Word: %d of %d" % (current_word_number, total_words)
    progress_control_surface = controls_font.render(progress_control_text, True, text_color)
    progress_control_rectangle = progress_control_surface.get_rect()
    progress_control_rectangle.bottomleft = (0, display_height)
    background.blit(progress_control_surface, progress_control_rectangle)

    lower_right_controls_text_3 = 'Right: Skip word'
    lower_right_controls_text_2 = 'Down: Incorrect'
    lower_right_controls_text_1 = 'Up: Correct'

    lower_right_controls_text_3_surface = controls_font.render(lower_right_controls_text_3, True, text_color)
    lower_right_controls_text_3_rectangle = lower_right_controls_text_3_surface.get_rect()
    lower_right_controls_text_3_rectangle.bottomright = ((display_width), (display_height))
    background.blit(lower_right_controls_text_3_surface, lower_right_controls_text_3_rectangle)

    lower_right_controls_text_2_surface = controls_font.render(lower_right_controls_text_2, True, text_color)
    lower_right_controls_text_2_rectangle = lower_right_controls_text_2_surface.get_rect()
    lower_right_controls_text_2_rectangle.bottomleft = lower_right_controls_text_3_rectangle.topleft
    background.blit(lower_right_controls_text_2_surface, lower_right_controls_text_2_rectangle)

    lower_right_controls_text_1_surface = controls_font.render(lower_right_controls_text_1, True, text_color)
    lower_right_controls_text_1_rectangle = lower_right_controls_text_1_surface.get_rect()
    lower_right_controls_text_1_rectangle.bottomleft = lower_right_controls_text_2_rectangle.topleft
    background.blit(lower_right_controls_text_1_surface, lower_right_controls_text_1_rectangle)

    main_word_surface = sight_word_font.render(word, True, text_color)
    main_word_rectangle = main_word_surface.get_rect()
    main_word_rectangle.center = ((display_width/2), (display_height/2))
    background.blit(main_word_surface, main_word_rectangle)

    # controls_surface = controls_font.render("Down = Incorrect, Up = Correct, Right = Skip, Esc = Quit", True, text_color)
    # logger.debug("Getting text rectangle for controls")
    # controls_rectangle = controls_surface.get_rect()
    # logger.debug("Centering text rectangle for controls in display horizontally")
    # controls_rectangle.center = ((display_width/2), (display_height - controls_rectangle.height))
    # logger.debug("Blitting text controls to background")
    # background.blit(controls_surface, controls_rectangle)

    logger.debug("Blitting background to screen")
    game_display.blit(background, (0,0))
    logger.debug("Updating display")
    pygame.display.flip()
    return

def connect_database(curr_loc):
    """
    Connects to the SQLite DB
    Returns the connection
    """
    conn = sqlite3.connect(curr_loc + os.sep + "SightRight.db")
    return conn

def quit_sightright(error_level):
    global logger
    if error_level != 0:
        logger.warning("SightRight is exiting with a non-zero exit code: %d" % error_level)
    logger.info('SightRight execution finished')
    sys.exit(error_level)

# Set up argument parser
parser = argparse.ArgumentParser(description='A flash card game for parents and children to play together')

parser.add_argument('-l', '--list-words',
                    action="store_const", const="LIST-WORDS",
                    dest="list_words",
                    help='List words/phrases stored in the database')

parser.add_argument('-d', '--debug',
                    action="store_const",
                    const="DEBUG",
                    dest="debug",
                    help='Enable debug output, for more verbosity')

arguments = parser.parse_args()

if arguments.debug or debug_on:
    logger.setLevel(logging.DEBUG)
    console_log_stream_handler.setLevel(logging.DEBUG)

logger.debug("Initializing pygame")
pygame.init()
game_clock = pygame.time.Clock()

display_width = 800
display_height = 600

black = (0,0,0)
white = (255,255,255)
red = (255,0,0)
green = (46,172,102)

logger.debug("Setting display mode")
game_display = pygame.display.set_mode((display_width,display_height))
logger.debug("Setting window caption")
pygame.display.set_caption('Flash Cards')
logger.debug("Initializing clock")
clock = pygame.time.Clock()
logger.debug("Initializing font")
sight_word_font = pygame.font.Font('freesansbold.ttf', 115)
controls_font = pygame.font.Font('freesansbold.ttf', 20)


current_word = "Word"
total_words = 30
current_word_number = 0
score = 0

logger.debug("Setting state to PRESENT_WORD")
game_state = PRESENT_WORD
logger.debug("Current word is: %s" % current_word)
def game_loop():
    global game_display
    # Hack, remove this at some point
    global current_word
    global game_state
    global total_words
    global current_word_number
    global score
    global answer_delay_ms

    logger.debug("Game loop beginning")
    logger.debug("Current word is: %s" % current_word)

    game_exit = False

    while game_exit == False:
        if game_state == PRESENT_WORD:
            current_word_number += 1
            # Choose the next word and set it

            # Display the word
            update_display()

            # Keep track of the tick when the word was rendered (for timekeeping)
            last_word_display_time = time.monotonic()
            # Clear the event queue
            pygame.event.clear()
            # Transition to next state
            logger.debug("Setting state to ACCEPT_INPUT")
            game_state = ACCEPT_INPUT

        elif game_state == ACCEPT_INPUT:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    logger.debug("Quit event detected")
                    pygame.quit()
                    quit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_DOWN:
                    # Down pressed
                    # Bad guess
                    logger.debug("Keyboard `arrow down` detected")
                    game_state = INCORRECT_GUESS
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_UP:
                    # Up pressed
                    # Good guess
                    logger.debug("Keyboard `arrow up` detected")
                    game_state = CORRECT_GUESS
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT:
                    # Right pressed
                    # Skipping word
                    logger.debug("Keyboard `arrow right` detected")
                    game_state = SKIP_WORD
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    logger.debug("Keyboard `escape` detected")
                    pygame.quit()
                    quit()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                    logger.debug("Keyboard `q` detected")
                    pygame.quit()
                    quit()

        elif game_state == CORRECT_GUESS:
            # Clear the event queue
            #pygame.event.clear()

            # Add to score
            score += 1

            # Calculate number of milliseconds since word was displayed
            answer_time = time.monotonic()
            answer_delay_ms = int((answer_time - last_word_display_time) * 1000)

            # Render the word as correct
            logger.debug("Rendering current word '%s' as correct" % current_word)
            update_display()

            # Set up timer
            logger.debug("Setting new timer for display")
            pygame.time.set_timer(pygame.USEREVENT + 1, SPLASH_DELAY)

            # Advance to DISPLAY_WAIT state
            logger.debug("Setting state to DISPLAY_WAIT")
            game_state = DISPLAY_WAIT

        elif game_state == INCORRECT_GUESS:
            # Clear the event queue
            #pygame.event.clear()

            # Calculate number of milliseconds since word was displayed
            answer_time = time.monotonic()
            answer_delay_ms = int((answer_time - last_word_display_time) * 1000)

            # Render the word as incorrect
            logger.debug("Rendering current word '%s' as incorrect" % current_word)
            update_display()

            # Set up timer
            logger.debug("Setting new timer for display")
            pygame.time.set_timer(pygame.USEREVENT + 1, SPLASH_DELAY)

            # Advance to DISPLAY_WAIT state
            logger.debug("Setting state to DISPLAY_WAIT")
            game_state = DISPLAY_WAIT

        elif game_state == DISPLAY_WAIT:
            for event in pygame.event.get():
                # print(event)
                # Check to see if the timer has lapsed
                if event.type == pygame.USEREVENT + 1:
                    logger.debug("Timer lapsed")
                    # Timer has happened
                    # Unset timer
                    pygame.time.set_timer(pygame.USEREVENT + 1, 0)
                    # Change back to PRESENT_WORD state
                    logger.debug("Setting state to PRESENT_WORD")
                    game_state = WAIT_FOR_NEW_WORD
                elif event.type == pygame.QUIT:
                    logger.debug("Quit event detected")
                    pygame.quit()
                    quit()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    logger.debug("Keyboard `escape` detected")
                    pygame.quit()
                    quit()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                    logger.debug("Keyboard `q` detected")
                    pygame.quit()
                    quit()

        elif game_state == SKIP_WORD:
            pass
            # Clear the event queue
            #pygame.event.clear()

            # Display nothing but a white background
            update_display()

            # Set up timer
            logger.debug("Setting new timer for display")
            pygame.time.set_timer(pygame.USEREVENT + 1, SPLASH_DELAY)

            # Advance to DISPLAY_WAIT state
            logger.debug("Setting state to DISPLAY_WAIT")
            game_state = DISPLAY_WAIT

        elif game_state == WAIT_FOR_NEW_WORD:
            update_display()

            # Check to see if any key is pressed
            for event in pygame.event.get():
                # print(event)
                # Check to see if the timer has lapsed
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    logger.debug("Spacebar pressed")
                    logger.debug("Setting state to PRESENT_WORD")
                    game_state = PRESENT_WORD
                elif event.type == pygame.QUIT:
                    logger.debug("Quit event detected")
                    pygame.quit()
                    quit()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    logger.debug("Keyboard `escape` detected")
                    pygame.quit()
                    quit()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                    logger.debug("Keyboard `q` detected")
                    pygame.quit()
                    quit()
        # logger.debug("Ticking clock")
        game_clock.tick(60)

    logger.debug("Game loop end")

if does_database_exist(current_directory):
    # Database was found
    logger.debug("Database file is present")
    connection = connect_database(current_directory)

    if not connection:
        # Error connecting to database
        logger.error("Could not connect to SightRight database file!")
        quit_sightright(CANNOT_CONNECT_TO_DATABASE)
    else:
        # Database connection successful
        logger.debug("Database connection successful")
        cursor = connection.cursor()
else:
    # Database was not found
    logger.info("SightRight database missing. Creating...")

    # Create the database
    connection = connect_database(current_directory)

    if not connection:
        # Error connecting to newly-created database
        logger.critical("Could not connect to SightRight database file!")
        quit_sightright(CANNOT_CONNECT_TO_DATABASE)
    else:
        # Successful creating and connecting to database
        logger.info("SightRight database created")
        cursor = connection.cursor()
        setup_database(cursor, connection)
        logger.info("Database setup complete")

logger.debug("Starting game loop")
game_loop()
pygame.quit()
quit_sightright(0)
