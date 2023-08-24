# Wii Sports Baseball AI

## Associated Videos

- [Original YouTube video](https://youtu.be/mTPqIuEM-ug)
- [Code walkthrough video](https://youtu.be/tDL-Tt671Zg)
- [Full gameplay](https://youtu.be/8OjLLPJgfPA)

## Setup
This project was optimized for running on a 720p display on Windows with a GPU. If your specs are different from this then some changes may be required to make it work for you.
### Dolphin Emulator
For this project I used Dolphin Emulator to play Wii Sports using a mouse and keyboard on my computer. You can download the latest version of Dolphin Emulator from [their website](https://dolphin-emu.org/). Once Dolphin Emulator has been installed you need to add the baseball controller profile to located in this project at `resources/baseball.ini` to Dolphin. To do this, go to the directory: `\Users\Your User\Documents\Dolphin Emulator\Config\Profiles\Wiimote` on your computer and add the `baseball.ini` controller profile to this directory. You may need to create the directory if it doesn't exist. Then, when you open Dolphin, go to the controller settings, select `Emulate the Wii's Bluetooth adapter` and configure an `Emulated Wii Remote`. Then load the profile from the dropdown in the top right. You can now emulate the Wiimote's motion controls using your keyboard. The important key bindings you need to know are:
- Wiimote A: `k`
- Wiimote B: `l`
- Swing/Pitch: `z`
- Wiimote D-Pad: arrow keys
You will need to obtain your own ROM of Wii Sports to play it with the emulator.

### Install dependencies
Once you've cloned/downloaded this project, navigate to it and then run the following command to install all the necessary packages:
```
pip install -r requirements.txt
```

## Usage
This project is split into different directories for recording data, training the AI on the data, and finally testing the AI.

### Recording swing data
```
cd record
python record_swing.py
```
This is used to collect data for swinging at pitches. It saves all images to one directory, and annotates these images in csvs in a separate directory. A separate CSV is created for each pitch. The naming convention for images is `pitchNumber_frameNumber.jpg` and for csvs is `pitchNumber.csv`. The csvs are formatted like: `imageName, label` where `label` is `1` if a swing was initiated during that image fram, and `0` otherwise. Examples are located in the `examples` directory. I recorded the data for pitches where I swung, and data for pitches where I didn't swing, separately to make training easier. This script will run until you terminate it and can be controlled with keypresses:
- `a`: Used to start and stop a recording for a swing
- `z`: This key is used to swing, and will automatically end a recording when it is pressed
- `s`: Saves the recording once it is complete
- `d`: Discards a recording once it is complete. This can be used to discard swings where you missed the ball

### Record pitching data
```
cd record
python record_pitch.py
```
This is used to collect data for pitching. It saves all data to csvs with a separate csv file for each new batter. The naming convention is like `batterNumber.csv`. The csvs are formatted like `outcome, pitchType, pitchDirection, strikes, balls, batterHandedness`. Examples are located in the `examples` directory. This script will run until you terminate it and can be controlled with keypresses:
- `i`: Start recording for a new batter
- `p`: Record a new pitch for the batter
- `o`: End recording for the batter
- `1`: Record outcome as a home run
- `2`: Record outcome as a double/triple
- `3`: Record outcome as a single/walk
- `4`: Record outcome as a ball
- `5`: Record outcome as a foul
- `6`: Record outcome as an out
- `7`: Record outcome as a foul strike
- `8`: Record outcome as a strike/strikeout

###  Train swing data
```
jupyter notebook
```
Open the notebook for training swinging at `train/train_swing.ipynb`. The notebook is annotated with explanations of the code.

###  Train pitch data
Note: in the video I mention that using AI is probably not the best method for this, and a simple statistical analysis works better. Aditionally, I found that only throwing right splitters works very well, so this notebook is not really needed, but it is included since it what I used.
```
jupyter notebook
```
Open the notebook for training swinging at `train/train_pitch.ipynb`. The notebook is annotated with explanations of the code.

### Test the AI
**IMPORTANT:** The model used in the video is located at `resources/final_swing_model.h5` and is used in the following script. This model was trained at 18 frames per second (FPS). The following script will output how many FPS it is running at during analysis. If it cannot run at 18 FPS then the model will not work properly and probably mistime its swing. I used [Tensorflow GPU](https://www.tensorflow.org/guide/gpu) and you may need to as well to achieve this speed. Additionally, the model was trained at 720p display resolution. If your display is different from this you will need to adjust the screenshot bounds in the code.
```
cd test
python play.py
```
This script is used to play an actual game. This script will run until you terminate it and can be controlled with keypresses:
`p`: Start/stop swing analysis to determine if the AI should swing. While analysis is active, the AI will swing automatically if it determines it should.
`o`: Throws a right splitter pitch