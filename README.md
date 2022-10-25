# geotagger
Python script embeding in the photography an openstreetmap map fragment showing the location and direction where the photo was taken. It works only if the picture contains location metadata. For most of modern phones, such options can be enabled in the settings.

You can check if your camera saves such data, by right clicking on some photography, then choosing Properties, and then Details. If there is "GPS" section, it means that localization data is present.

## How to use it
1. Download and install python, using the default settings: [download page](https://www.python.org/downloads/)
2. Download this project
3. In the project directory, execute `pip install requirements.txt`
4. Execute `py geotagger.py --help` to see possible arguments
