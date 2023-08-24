from tensorflow import keras
import numpy as np
from mss import mss
import pydirectinput
import pynput
import cv2
import time

WIDTH = 96
HEIGHT = 96

TIMESTEPS = 5

SWING_KEY = 'z'

FPS = 18
DELAY = 1 / FPS

evaluate = False

model = keras.models.load_model('../resources/final_swing_model.h5')

sct = mss()
mon_id = 1 # second monitor
mon = sct.monitors[mon_id]
# Screenshot bounds. This is configured for a 720p display if you are using a different resolution then you need
# to update these values as necessary
monitor = {
    'top': mon['top'] + 213,
    'left': mon['left'] + 510,
    'width': 346,
    'height': 346,
    'mon': mon_id
}

pydirectinput.PAUSE = 0

# preprocess images for the swing model
def pre_process(image):
    # convert from BGR to HSV image in order to apply color mask
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    masked_im = cv2.inRange(hsv, (0, 0, 0), (179, 57, 255))
    masked_im = cv2.bitwise_and(image, image, mask=masked_im)

    # conver image to grayscale
    masked_im = cv2.cvtColor(masked_im, cv2.COLOR_BGR2GRAY)

    # resize image
    masked_im = cv2.resize(masked_im, (WIDTH, HEIGHT))

    # normalize values to be between 0 and 1
    masked_im = masked_im / 255

    masked_im = masked_im.reshape(WIDTH, HEIGHT, 1)
    return masked_im

# Always throws right splitters
# Since the model always throws right splitters, this function hard codes that functionality
# This function could be rewritten to use the actual pitching model
def pitch():
    pydirectinput.keyDown('right')

    start_time = time.perf_counter()
    while (time.perf_counter() - start_time) < 0.5:
        pass

    pydirectinput.keyUp('right')

    pydirectinput.keyDown('k')
    pydirectinput.keyDown('l')

    start_time = time.perf_counter()
    while (time.perf_counter() - start_time) < 0.2:
        pass

    pydirectinput.keyDown('z')

    start_time = time.perf_counter()
    while (time.perf_counter() - start_time) < 0.5:
        pass

    pydirectinput.keyUp('z')

    pydirectinput.keyUp('k')
    pydirectinput.keyUp('l')

# key press listener function to control swing and pitch
def on_press(key):
    global evaluate

    try:
        char = key.char
    except AttributeError:
        return

    # press p to start or evaluating a pitch, the model will evaluate if it should swing during this time
    if char == 'p':
        evaluate = not evaluate
    # press o to throw pitch
    elif char == 'o':
        pitch()


def main():
    print('Ready')

    # initialize keyboard listenter to listen for key presses
    keyboard_listener = pynput.keyboard.Listener(on_press=on_press)
    keyboard_listener.start()

    # evaluation loop runs forever until script is terminated
    while True:
        # not current evaluating a pitch, wait to evaluate
        if not evaluate:
            continue

        print('Evaluating...')

        # initialize the image sequence with screenshots to before starting
        window = []
        for _ in range(TIMESTEPS):
            image = np.array(sct.grab(monitor))
            image = pre_process(image)
            window.append(image)

        begin_time = time.time()
        count = 0
        while evaluate:
            start_time = time.perf_counter()
            image = np.array(sct.grab(monitor))
            image = pre_process(image)

            # delete first image in the sequence and append the new image to the sequence
            del window[0]
            window.append(image)

            # run the model on the image sequence
            prediction = model(np.array([window])).numpy()

            # pause in order to match the correct FPS
            while (time.perf_counter() - start_time) < DELAY:
                pass

            # swing if model predicts a swing
            if prediction[0][0] > 0.5:
                pydirectinput.keyDown(SWING_KEY)
                time.sleep(0.1)
                pydirectinput.keyUp(SWING_KEY)
            count += 1
        # calculate FPS of the evaluation. If there was a swing, the FPS will be slightly lower
        end_time = time.time()
        print(f'FPS: {count / (end_time - begin_time)}')

if __name__ == '__main__':
    main()