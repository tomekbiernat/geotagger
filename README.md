# geotagger
Python script embeding in the photography an openstreetmap map fragment showing the location and direction where the photo was taken. It works only if the picture contains location metadata. For most of modern phones, such options can be enabled in the settings.

You can check if your camera saves such data, by right clicking on some photography, then choosing Properties, and then Details. If there is "GPS" section, it means that location data is present. If no, and you have GPS turned on, try searching the Internet for "how to add location to photos"

## How to use it
1. Download and install python, using the default settings: [download page](https://www.python.org/downloads/)
2. Download this project (right upper corner - green button Code -> Download ZIP)
3. Extract downloaded project
4. Run a command prompt, navigate to the project directory, execute `py -m pip install -r requirements.txt`
5. To generate a picture with map preview, execute `py geotagger.py path_to_photo`. You can use wildcards (\*) in the path to match multiple files
6. Execute `py geotagger.py --help` to see possible arguments
