from mss import mss
import numpy as np
import cv2
import pydirectinput
import random
import pynput
import time
import csv

# Pitch directions
LEFT = 'left'
CENTER = 'center'
RIGHT = 'right'
DIRECTIONS = [LEFT, CENTER, RIGHT]

# Pitch types
FASTBALL = 'fastball'
SCREWBALL = 'screwball'
CURVEBALL = 'curveball'
SPLITTER = 'splitter'
PITCH_TYPES = [FASTBALL, SCREWBALL, CURVEBALL, SPLITTER]

# Wiimote key mappings. These are set for the provided controller profile.
WIIMOTE_A = 'k'
WIIMOTE_B = 'l'
WIIMOTE_SHAKE = 'z'

# Key mappings for throwing different pitches
PITCH_BUTTONS = {
    FASTBALL: [],
    SCREWBALL: [WIIMOTE_A],
    CURVEBALL: [WIIMOTE_B],
    SPLITTER: [WIIMOTE_A, WIIMOTE_B]
}

# Pixel values for locations that will be used to automatically determine the game state. These are configured
# for a 720p display. These will need to be adjusted to different resolutions.
GAMESTATE_LOCATIONS = {
    'strike': {
        1: {
            'x': 100,
            'y': 100
        },
        2: {
            'x': 130,
            'y': 100
        }
    },
    'ball': {
        1: {
            'x': 100,
            'y': 70
        },
        2: {
            'x': 130,
            'y': 70
        },
        3: {
            'x': 160,
            'y': 70
        }
    },
    'batter': {
        'left': {
            'x': 735,
            'y': 465,
            'value_min': 43,
            'value_max': 50
        },
        'right': {
            'x': 925,
            'y': 455,
            'value_min': 44,
            'value_max': 51
        }
    }
}

# Map reward names to their values
REWARD_NAMES = {
    -1: 'Homerun',
    -0.75: 'Triple / Double',
    -0.5: 'Singe / Walk',
    -0.25: 'Ball',
    0: 'Foul not counted as strike',
    0.25: 'Out after hit',
    0.5: 'Foul counts as strike',
    1: 'Strike'
}

CSV_DIR = 'pitch_csvs/'

# recording variables
record_batter = False
awaiting_result = False
awaiting_pitch = False
result = 0

pydirectinput.PAUSE = 0

# Keypress listener to control recording state
def on_press(key):
    global awaiting_pitch
    global awaiting_result
    global record_batter
    global result

    try:
        char = key.char
    except AttributeError:
        return

    # press p to start recording new pitch for same batter
    if char == 'p':
        awaiting_pitch = False
    # press o to end recording for batter
    elif char == 'o':
        record_batter = False
        awaiting_pitch = False
    # press i to start recording a new batter
    elif char == 'i':
        record_batter = True
    # press 1 if outcome is homerun, end recording for batter
    elif char == '1':
        result = -1
        awaiting_result = False
        record_batter = False
        awaiting_pitch = False
    # press 2 if outcome is triple/double, end recording for batter
    elif char == '2':
        result = -0.75
        awaiting_result = False
        record_batter = False
        awaiting_pitch = False
    # press 3 if outcome is single/walk, end recording for batter
    elif char == '3':
        result = -0.5
        awaiting_result = False
        record_batter = False
        awaiting_pitch = False
    # press 4 if outcome is ball, do not explicitly end recording for batter
    elif char == '4':
        result = -0.25
        awaiting_result = False
    # press 5 if outcome is foul, do not explicitly end recording for batter
    elif char == '5':
        result = 0
        awaiting_result = False
    # press 6 if outcome is out, end recording for batter
    elif char == '6':
        result = 0.25
        awaiting_result = False
        record_batter = False
        awaiting_pitch = False
    # press 7 if outcome is foul strike, do not explicitly end recording for batter
    elif char == '7':
        result = 0.5
        awaiting_result = False
    # press 8 if outcome is foul strike/strikeout, do not explicitly end recording for batter
    elif char == '8':
        result = 1
        awaiting_result = False

# move pitch left or right
def move(direction):
    if direction == CENTER:
        return
    
    pydirectinput.keyDown(direction)
    
    # sleep for 0.5 seconds
    start_time = time.perf_counter()
    while (time.perf_counter() - start_time) < 0.5:
        pass

    pydirectinput.keyUp(direction)


# Send key inputs to pitch the specified pitch type in the specified direction
def pitch(pitch_type, direction):
    move(direction)

    for button in PITCH_BUTTONS[pitch_type]:
        pydirectinput.keyDown(button)
    
    start_time = time.perf_counter()
    while (time.perf_counter() - start_time) < 0.2:
        pass

    pydirectinput.keyDown(WIIMOTE_SHAKE)

    start_time = time.perf_counter()
    while (time.perf_counter() - start_time) < 0.5:
        pass

    pydirectinput.keyUp(WIIMOTE_SHAKE)

    for button in PITCH_BUTTONS[pitch_type]:
        pydirectinput.keyUp(button)


# Pitch a random pitch type in a random direction
def pitch_random():
    pitch_type = random.choice(PITCH_TYPES)
    direction = random.choice(DIRECTIONS)

    pitch(pitch_type, direction)

    return pitch_type, direction

# returns the current gamestate by taking a screenshot and analyzing pixel values
def get_gamestate(image):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    strikes = 0
    balls = 0
    # determine how many strikes there are
    strike_loc = GAMESTATE_LOCATIONS['strike']
    if image[strike_loc[2]['y']][strike_loc[2]['x']] > 200:
        strikes = 2
    elif image[strike_loc[1]['y']][strike_loc[1]['x']] > 200:
        strikes = 1
    
    # determine how many balls there are
    ball_loc = GAMESTATE_LOCATIONS['ball']
    if image[ball_loc[3]['y']][ball_loc[3]['x']] > 200:
        balls = 3
    elif image[ball_loc[2]['y']][ball_loc[2]['x']] > 200:
        balls = 2
    elif image[ball_loc[1]['y']][ball_loc[1]['x']] > 200:
        balls = 1

    # determine the handedness of the batter
    handedness = 'right'
    left_batter_loc = GAMESTATE_LOCATIONS['batter']['left']
    left_batter_pix = image[left_batter_loc['y']][left_batter_loc['x']]
    if left_batter_pix not in range(left_batter_loc['value_min'], left_batter_loc['value_max']):
        handedness = 'left'

    # return the current gamestate
    gamestate = {
        'strikes': strikes,
        'balls': balls,
        'handedness': handedness
    }
    return gamestate


def main():
    global awaiting_result
    global awaiting_pitch

    # initialize keyboard listenter to listen for key presses
    keyboard_listener = pynput.keyboard.Listener(on_press=on_press)
    keyboard_listener.start()

    # configure to take screenshot of entire monitor
    sct = mss()
    monitor = sct.monitors[2]

    count = 0
    # recording loop runs forever until script is terminated
    while(True):
        # not in recording state, wait for recording state to change
        if not record_batter:
            continue
        
        print(f'----------- Starting recording for: {count} -----------')

        # create new csv file to write data to
        csv_path = f'{CSV_DIR}{count}.csv'
        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')

            # record all pitches for a single batter
            while record_batter:
                # take screenshot and get gamestate from it
                screenshot = np.array(sct.grab(monitor))
                gamestate = get_gamestate(screenshot)
                print(f'Gamestate: {gamestate}')

                # pitch a random pitch
                pitch_type, direction = pitch_random()
                print(f'Threw: {direction} {pitch_type}')

                awaiting_result = True
                awaiting_pitch = True
                # Wait to record the outcome of the pitch
                while awaiting_result:
                    continue
                
                print(f'Result: {result}, {REWARD_NAMES[result]}')

                # Record the outcome of the pitch to the csv
                writer.writerow([result, pitch_type, direction, gamestate['strikes'], gamestate['balls'], gamestate['handedness']])

                # waits for next pitch to be thrown for the same batter
                while awaiting_pitch:
                    continue
        
        print(f'----------- Ending recording for: {count} -----------')
        count += 1


if __name__ == '__main__':
    main()