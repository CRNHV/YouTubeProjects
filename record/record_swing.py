from mss import mss
import numpy as np
import cv2
import csv
import pynput
import time

IMAGE_DIR = 'swing_ims/'
CSV_DIR = 'swing_csvs/'

FPS = 18 # frames per second of recording
DELAY = 1 / FPS

# recording statuses
WAITING = 0
SAVE = 1
DISCARD = 2

record = False
status = WAITING
hit = False

# key press listener function to control recording state
# You can change these keys, but these work well with the emulator control profile provided
def on_press(key):
    global record
    global status
    global hit

    try:
        char = key.char
    except AttributeError:
        return

    # Toggle recording state. Press a to start and stop recording
    if char == 'a':
        record = not record
    # Press s to save recording after it's complete
    elif char == 's':
        status = SAVE
    # Press d to discard recording after it's complete
    elif char == 'd':
        status = DISCARD
    # Press z to stop recording and mark it as a hit. This should be bound to the same key that you use to swing
    elif char == 'z':
        hit = True
        record = False


def main():
    global record
    global status
    global hit

    sct = mss()
    mon_id = 2 # second monitor
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
    # bounds for 1080p monitor
    # monitor = {
    #     'top': mon['top'] + 320,
    #     'left': mon['left'] + 765,
    #     'width': 520,
    #     'height': 520,
    #     'mon': mon_id
    # }

    # initialize keyboard listenter to listen for key presses
    keyboard_listener = pynput.keyboard.Listener(on_press=on_press)
    keyboard_listener.start()


    count = 0
    # recording loop runs forever until script is terminated
    while True:
        # not in recording state, wait for recording state to change
        if not record:
            continue

        print(f'----------- Starting recording for: {count} -----------')

        sequence = []
        label = []

        begin_time = time.time()
        while(record):
            start_time = time.perf_counter()

            # take screenshot
            image = np.array(sct.grab(monitor))
            sequence.append(image)

            # pause in order to match the correct FPS
            while (time.perf_counter() - start_time) < DELAY:
                pass

            # label the screenshot according to if it was hit or not
            if hit:
                label.append(1)
                hit = False
            else:
                label.append(0)

            # Uncomment this to display the screenshots in real time
            # cv2.imshow('Pitch', masked_im)
            # if cv2.waitKey(25) & 0xFF == ord("p"):
            #     cv2.destroyAllWindows()
            #     break

        # Pitch ended with a valid hit and the last screenshot has not yet been recorded
        if hit:
            image = np.array(sct.grab(monitor))
            sequence.append(image)
            label.append(1)
            hit = False

        # Calculate FPS of the recording
        end_time = time.time()
        print(f'FPS: {len(label) / (end_time - begin_time)}')
        print(f'Ending recording for: {count}')
        
        # Waiting for input to determine if the recording should be saved or not
        status = WAITING
        while status == WAITING:
            continue
        
        # save recording screenshots and annotations
        if status == SAVE:
            print('Saving recording')
            csv_path = f'{CSV_DIR}{count}.csv'
            with open(csv_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter=',')
                
                for i in range(len(sequence)):
                    im_name = f'{count}_{i}.jpg'
                    im_path = f'{IMAGE_DIR}{im_name}'
                    cv2.imwrite(im_path, sequence[i])
                    writer.writerow([im_name, label[i]])
            print('Recording saved')
            count += 1
        # discard recording
        else:
            print('Discarding recording')
        print(f'---------------------------------------------------')
        
if __name__ == '__main__':
    main()