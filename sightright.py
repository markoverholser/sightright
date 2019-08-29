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
#WAIT_FOR_NEW_WORD = 70
BATCH_END = 80

# Number of milliseconds to keep a word displayed on the screen after state change
SPLASH_DELAY = 70

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

################################################################################
# Classes                                                                      #
################################################################################

class phrase:
	phrase_id = ''
	text = ''
	batch_id = ''
	
def does_database_exist(curr_loc):
    """
    Checks for presence of database in curr_loc folder
    Returns 1 if database exists, 0 if it does not
    """
    db_name = "SightRight.db"
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
    cmd = "CREATE TABLE batches (batch_id INT NOT NULL, start_time, end_time);"
    cur.execute(cmd)
    cmd = "CREATE TABLE response_history (batch_id INT NOT NULL, phrase_id INT NOT NULL, response_time_ms INT, response_status);"
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

    global current_phrase
    global game_state
    global score
    global background_color
    global text_color

    background = pygame.Surface(game_display.get_size())
    background = background.convert()
    
    if game_state == BATCH_START:
        background_color = white
        text_color = black
        word = ""
        
        background.fill(background_color)
        
        press_key_to_begin_text = "Press any key to begin"
        press_key_to_begin_surface = controls_font.render(press_key_to_begin_text, True, text_color)
        press_key_to_begin_rectangle = press_key_to_begin_surface.get_rect()
        press_key_to_begin_rectangle.center = (int(display_width/2), int(display_height/2))
        background.blit(press_key_to_begin_surface, press_key_to_begin_rectangle)
    
    elif game_state == PRESENT_WORD:
        background_color = white
        text_color = black
        word = current_phrase.text

        background.fill(background_color)

    elif game_state == CORRECT_GUESS:
        background_color = green
        text_color = white
        word = current_phrase.text

        answer_delay_text = "Answer time: %d ms" % answer_delay_ms

        background.fill(background_color)

        answer_delay_surface = controls_font.render(answer_delay_text, True, text_color)
        answer_delay_rectangle = answer_delay_surface.get_rect()
        answer_delay_rectangle.center = (display_width/2, int(display_height*3/4))
        background.blit(answer_delay_surface, answer_delay_rectangle)

    elif game_state == INCORRECT_GUESS:
        background_color = black
        text_color = white
        word = current_phrase.text

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
    
    elif game_state == BATCH_END:
        background_color = white
        text_color = black
        word = ""
        
        background.fill(background_color)
        
        press_key_to_end_text = "Round complete. Press Q or Esc to quit"
        press_key_to_end_surface = controls_font.render(press_key_to_end_text, True, text_color)
        press_key_to_end_rectangle = press_key_to_end_surface.get_rect()
        press_key_to_end_rectangle.center = (int(display_width/2), int(display_height/2))
        background.blit(press_key_to_end_surface, press_key_to_end_rectangle)
        
    #elif game_state == WAIT_FOR_NEW_WORD:
        ## Don't change colors, reuse from before
        ## background_color = white
        ## text_color = black
        #word = current_phrase.text

        #answer_delay_text = "Answer time: %d ms" % answer_delay_ms
        
        #background.fill(background_color)
        
        #answer_delay_surface = controls_font.render(answer_delay_text, True, text_color)
        #answer_delay_rectangle = answer_delay_surface.get_rect()
        #answer_delay_rectangle.center = (display_width/2, int(display_height*3/4))
        #background.blit(answer_delay_surface, answer_delay_rectangle)

        #continue_control_text = "Press Space to continue"
        #continue_control_surface = controls_font.render(continue_control_text, True, text_color)
        #continue_control_rectangle = continue_control_surface.get_rect()
        #continue_control_rectangle.midbottom = (display_width/2, display_height)
        #background.blit(continue_control_surface, continue_control_rectangle)

    quit_control_text = "Esc: Quit"
    quit_control_surface = controls_font.render(quit_control_text, True, text_color)
    quit_control_rectangle = quit_control_surface.get_rect()
    quit_control_rectangle.topleft = (0, 0)
    background.blit(quit_control_surface, quit_control_rectangle)

    score_control_text = "Score: %d (%d%%)" % (score, int((score/max(current_phrase_number-1, 1))*100))
    score_control_surface = controls_font.render(score_control_text, True, text_color)
    score_control_rectangle = score_control_surface.get_rect()
    score_control_rectangle.topright = (display_width, 0)
    background.blit(score_control_surface, score_control_rectangle)

    progress_control_text = "Word: %d of %d" % (current_phrase_number, total_words)
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

def log_phrase_result(cur, conn, batch_id, phrase_id, time_to_result, result):
    global logger
    
    try:
        cmd = 'INSERT INTO response_history (batch_id, phrase_id, response_time_ms, response_status) VALUES (%s, %s, %s, "%s")' % (batch_id, phrase_id, time_to_result, result)
        cur.execute(cmd)
        conn.commit()
    except sqlite3.OperationalError:
        logger.error("Could not log results into database: (%s, %s, %s, %s)" % (batch_id, phrase_id, time_to_result, result))
        return None
	
def get_phrase_batch(cur, conn, num_of_words):
    global logger
    
    try:
        cmd = 'SELECT max(batch_id) FROM batches'
        cur.execute(cmd)
        conn.commit()
        
        batch_id = cur.fetchall()[0][0]
        logger.debug(batch_id)
        batch_id += 1
    except:
        logger.warn("There are no current batches")
        batch_id = 1
    
    try:
        cmd = 'INSERT INTO batches (batch_id) VALUES (%s)' % batch_id
        cur.execute(cmd)
        conn.commit()
    except:
        logger.error("Could not add batch %s to database" % batch_id)
        return None
    
    try:
        cmd = 'SELECT rowid,phrase FROM phrases WHERE enabled="True" ORDER BY RANDOM() LIMIT %s' % num_of_words
        cur.execute(cmd)
        conn.commit()
        
        phrases = []
        for returned_phrase in cur.fetchall():
            phrase_obj = phrase()
            
            phrase_obj.phrase_id = returned_phrase[0]
            phrase_obj.text = returned_phrase[1]
            phrase_obj.batch_id = batch_id
            
            phrases.append(phrase_obj)
        
        return phrases
    except:
        logger.error("Something bad happened") # This is what happens when you write code at midnight

def add_phrase_to_database(cur, conn, phrase, origin_list):
    global logger
    
    try:
        cmd = 'SELECT rowid,phrase FROM phrases where phrase="%s"' % phrase
        cur.execute(cmd)
        conn.commit()
        
        returned = cur.fetchall()[0]
        # If we make it this far, that means that there *is* already that phrase present in the database, so we should return None to signal that
        logger.debug("Phrase '%s' is already present in the database" % phrase)
        return None
    except:
        # There are no items in the database with that phrase
        logger.debug("Phrase '%s' does not exist in the database, adding" % phrase)
        pass
    
    # Now we can try to add it to the database
    try:
        cmd = 'INSERT INTO phrases (phrase, list, enabled) VALUES ("%s", "%s", "True")' % (phrase, origin_list)
        cur.execute(cmd)
        conn.commit()
    except sqlite3.OperationalError:
        logger.error("Error inserting '%s' into the database" % phrase)
        return None
    
    # Now we get the rowid of the phrase to return it
    try:
        cmd = 'SELECT rowid,phrase FROM phrases where phrase="%s"' % phrase
        cur.execute(cmd)
        conn.commit()
        
        rowid = cur.fetchall()[0][0]
        return rowid
    except:
        pass

def quit_sightright(error_level):
    global logger
    if error_level != 0:
        logger.warning("SightRight is exiting with a non-zero exit code: %d" % error_level)
    logger.info('SightRight execution finished')
    sys.exit(error_level)

# Set up argument parser
parser = argparse.ArgumentParser(description='A flash card game for parents and children to play together')

parser.add_argument('-l', '--list-phrases',
                    action="store_const", const="LIST-PHRASES",
                    dest="list_phrases",
                    help='List phrases stored in the database')

parser.add_argument('-i', '--import-phrases',
                    action="store", dest="import_phrases",
                    help='Import a CSV file of phrases into the database')

parser.add_argument('-d', '--debug',
                    action="store_const",
                    const="DEBUG",
                    dest="debug",
                    help='Enable debug output, for more verbosity')

arguments = parser.parse_args()

if arguments.debug or debug_on:
    logger.setLevel(logging.DEBUG)
    console_log_stream_handler.setLevel(logging.DEBUG)

def game_loop():
    global game_display
    # Hack, remove this at some point
    global current_phrase
    global phrases
    global game_state
    global total_words
    global current_phrase_number
    global score
    global answer_delay_ms

    logger.debug("Game loop beginning")
    logger.debug("Current word is: %s" % current_phrase.text)

    game_exit = False

    while game_exit == False:
        if game_state == BATCH_START:
            # Don't update the display here, it makes the debug logs too chatty
            # Instead update the display immediately after setting the state to BATCH_END
            # elsewhere in the code
            # update_display()
            
            # Wait for a keypress to continue
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
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
                elif event.type == pygame.KEYDOWN:
                    logger.debug("Setting state to PRESENT_WORD")
                    game_state = PRESENT_WORD
                    
        elif game_state == PRESENT_WORD:
            current_phrase_number += 1
            # Choose the next word and set it
            current_phrase = phrases[current_phrase_number - 1]

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
            logger.debug("Rendering current word '%s' as correct" % current_phrase.text)
            update_display()
            
            # Log to database
            log_phrase_result(cursor, connection, current_phrase.batch_id, current_phrase.phrase_id, answer_delay_ms, "Correct")

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
            logger.debug("Rendering current word '%s' as incorrect" % current_phrase.text)
            update_display()
            
            # Log to database
            log_phrase_result(cursor, connection, current_phrase.batch_id, current_phrase.phrase_id, answer_delay_ms, "Incorrect")

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
                    
                    if current_phrase_number == total_words:
                        # We have reached the target number of words
                        # Time to leave the user no option but to quit
                        logger.debug("Setting state to BATCH_END")
                        game_state = BATCH_END
                        # Update the display here so that we don't have to do it in the game_state == BATCH_END
                        # That causes unnecessarily chatty debug logs
                        update_display()
                    else:
                        # Change back to PRESENT_WORD state
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

        #elif game_state == WAIT_FOR_NEW_WORD:
            #update_display()

            ## Check to see if any key is pressed
            #for event in pygame.event.get():
                ## print(event)
                ## Check to see if the timer has lapsed
                #if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    #logger.debug("Spacebar pressed")
                    #logger.debug("Setting state to PRESENT_WORD")
                    #game_state = PRESENT_WORD
                #elif event.type == pygame.QUIT:
                    #logger.debug("Quit event detected")
                    #pygame.quit()
                    #quit()
                #elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    #logger.debug("Keyboard `escape` detected")
                    #pygame.quit()
                    #quit()
                #elif event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                    #logger.debug("Keyboard `q` detected")
                    #pygame.quit()
                    #quit()
        
        elif game_state == BATCH_END:
            # Don't update the display here, it makes the debug logs too chatty
            # Instead update the display immediately after setting the state to BATCH_END
            # elsewhere in the code
            # update_display()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
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

if arguments.import_phrases:
    try:
        import csv
    except:
        logger.error("Error importing CSV module")
    
    #try:
    with open(arguments.import_phrases) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            result = add_phrase_to_database(cursor, connection, row['phrase'], row['list'])
            logger.debug(result)
            if result != None:
                logger.debug("Successfully added '%s' to database with id '%s'" % (row['phrase'], result))
            else:
                logger.warn("Skipped adding '%s' to database" % row['phrase'])
    #except e:
    #    print(e)
    #logger.error("Something bad happened")
    quit_sightright(0)

logger.debug("Initializing pygame")
pygame.init()
game_clock = pygame.time.Clock()

display_width = 480
display_height = 272

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

phrases = get_phrase_batch(cursor, connection, 30)

total_words = 30
current_phrase_number = 0
score = 0

current_phrase = phrases[current_phrase_number]

logger.debug("Setting state to BATCH_START")

game_state = BATCH_START
# Update the display now before starting the loop
# Otherwise we need an update_display() call in the loop for BATCH_START
# which makes it unnecessarily chatty in the debug logs
update_display()

#logger.debug("Current word is: %s" % current_phrase.text)

logger.debug("Starting game loop")
game_loop()
pygame.quit()
quit_sightright(0)
