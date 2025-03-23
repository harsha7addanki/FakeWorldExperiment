# Fake World Project

## How to use
The app requires a Google AI studio API key which you can get [here](https://aistudio.google.com/apikey)  
after you get your key create a `.env` file.
the file should look like this:
```environment
GOOGLE_GENAI_API_KEY=<PUT YOUR KEY HERE>
```
after the environment variables are set up install the packages
the project requires only the [python SDK](https://pypi.org/project/google-genai/) for google genai.
if you want a render then you can install [pygame](https://pypi.org/project/pygame/) too.

* `terminalWorld.py`: the fake world in the terminal basic stuff is very buggy.
* `guiWorld.py`: Terminal world but gui. Much better recommended if you don't like renders.
* `pygameWorld.py`: Render for non-tech people. very good for showing off.
