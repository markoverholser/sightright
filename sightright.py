try:
    import pygame
    import time
    import sys
    import sqlite3
    import logging
    import os
    from time import gmtime, strftime
except e:
    print(e)

ACCEPT_INPUT = 1
PRESENT_WORD = 2
CORRECT_GUESS = 3
INCORRECT_GUESS = 4
DISPLAY_WAIT = 5
SKIP_WORD = 6

# Number of milliseconds to keep a word displayed on the screen after state change
SPLASH_DELAY = 500

debug_on = True

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
    cmd = "CREATE TABLE response_history (word_id, response_time_ms, response_correct);"
    cur.execute(cmd)
    conn.commit()

def print_debug(message):
    global debug_on
    if debug_on:
        print("DEBUG: %s" % message)

def word_display(word, background_color, text_color):
    global game_font
    global display_width
    global display_height
    global game_display

    print_debug("Displaying text %s with background %s and color %s" % (word, background_color, text_color))
    print_debug("Filling background")
    background = pygame.Surface(game_display.get_size())
    background = background.convert()
    background.fill(background_color)
    #game_display.fill(background_color)
    print_debug("Getting text surface")
    text_surface = game_font.render(word, True, text_color)
    print_debug("Getting text rectangle")
    text_rectangle = text_surface.get_rect()
    print_debug("Centering text rectangle in display")
    text_rectangle.center = ((display_width/2), (display_height/2))
    print_debug("Blitting text to background")
    background.blit(text_surface, text_rectangle)
    print_debug("Blitting background to screen")
    game_display.blit(background, (0,0))
    print_debug("Updating display")
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

print_debug("Initializing pygame")
pygame.init()
game_clock = pygame.time.Clock()

display_width = 800
display_height = 600

black = (0,0,0)
white = (255,255,255)
red = (255,0,0)
green = (46,172,102)

print_debug("Setting display mode")
game_display = pygame.display.set_mode((display_width,display_height))
print_debug("Setting window caption")
pygame.display.set_caption('Flash Cards')
print_debug("Initializing clock")
clock = pygame.time.Clock()
print_debug("Initializing font")
game_font = pygame.font.Font('freesansbold.ttf', 115)



def game_loop():
    global game_display
    # Hack, remove this at some point
    current_word = "Word"
    print_debug("Game loop beginning")

    game_exit = False
    # accepting_input = True
    game_state = ACCEPT_INPUT

    while game_exit == False:
        if game_state == PRESENT_WORD:
            print_debug("In PRESENT_WORD state")
            word_display("Word", white, black)
            # Clear the event queue
            pygame.event.clear()
            # Transition to next state
            print_debug("Transitioning to ACCEPT_INPUT state")
            game_state = ACCEPT_INPUT

        elif game_state == ACCEPT_INPUT:
            print_debug("In ACCEPT_INPUT state")
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    print_debug("Quit event detected")
                    pygame.quit()
                    quit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_DOWN:
                    # Down pressed
                    # Bad guess
                    print_debug("Keyboard `arrow down` detected")
                    game_state = INCORRECT_GUESS
                    pass
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_UP:
                    # Up pressed
                    # Good guess
                    print_debug("Keyboard `arrow up` detected")
                    game_state = CORRECT_GUESS
                    pass
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    print_debug("Keyboard `escape` detected")
                    pygame.quit()
                    quit()

        elif game_state == CORRECT_GUESS:
            print_debug("In CORRECT_GUESS state")
            # Clear the event queue
            #pygame.event.clear()
            # Render the word as correct
            print_debug("Rendering current word '%s' as correct" % current_word)
            word_display(current_word, green, white)

            # Set up timer
            print_debug("Setting new timer for display")
            pygame.time.set_timer(pygame.USEREVENT + 1, SPLASH_DELAY)

            # Advance to DISPLAY_WAIT state
            game_state = DISPLAY_WAIT

        elif game_state == INCORRECT_GUESS:
            print_debug("In INCORRECT_GUESS state")
            # Clear the event queue
            #pygame.event.clear()
            # Render the word as incorrect
            print_debug("Rendering current word '%s' as incorrect" % current_word)
            word_display(current_word, black, white)

            # Set up timer
            print_debug("Setting new timer for display")
            pygame.time.set_timer(pygame.USEREVENT + 1, SPLASH_DELAY)

            # Advance to DISPLAY_WAIT state
            game_state = DISPLAY_WAIT

        elif game_state == DISPLAY_WAIT:
            print_debug("In DISPLAY_WAIT state")

            for event in pygame.event.get():
                # print(event)
                # Check to see if the timer has lapsed
                if event.type == pygame.USEREVENT + 1:
                    print_debug("Timer lapsed")
                    # Timer has happened
                    # Unset timer
                    pygame.time.set_timer(pygame.USEREVENT + 1, 0)
                    # Change back to PRESENT_WORD state
                    game_state = PRESENT_WORD
                elif event.type == pygame.QUIT:
                    print_debug("Quit event detected")
                    pygame.quit()
                    quit()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    print_debug("Keyboard `escape` detected")
                    pygame.quit()
                    quit()

        elif game_state == SKIP_WORD:
            print_debug("In SKIP_WORD state")
            pass
            # Clear the event queue
            #pygame.event.clear()

            # Set up timer
            print_debug("Setting new timer for display")
            pygame.time.set_timer(pygame.USEREVENT + 1, SPLASH_DELAY)

            # Advance to DISPLAY_WAIT state
            game_state = DISPLAY_WAIT

        # print_debug("Ticking clock")
        game_clock.tick(60)

    print_debug("Game loop end")

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

print_debug("Starting game loop")
game_loop()
pygame.quit()
quit_sightright(0)
