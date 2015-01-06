import os
from flask import Flask

app = Flask(__name__)

# log to stderr
import logging
app.logger.setLevel(logging.DEBUG)
app.logger.addHandler(logging.StreamHandler())

def check_config():
    """Returns a bool indicating whether we have enough configuration
    to serve a request."""

    keys_desired = set(['API_SECRET', 'AWS_ACCESS', 'AWS_SECRET'])

    app.logger.info("Verifying config contains these keys: %s", " ".join(keys_desired))

    keys_provided = set(os.environ.keys())
    keys_missing = keys_desired.difference(keys_provided)
    
    if len(keys_missing) > 0:
        app.logger.info("Config is missing at least one key: %s", " ".join(keys_missing))
        return False
    else:
        app.logger.info("Config passes basic check.")
        return True

@app.route('/')
def root():
    if check_config():
        return 'OK'
    else:
        return 'Config not OK, check logs.'

@app.route('/add/', methods = ['POST'])
def add():
    # Read in long URL and auth token
    # Validate auth token
    # Create short path ID
    # Save
    # Return full short URL (domain + short path) to user.
    return "lols"

@app.route('/<path:short>')
@app.route('/<preview>/<path:short>')
def lookup(short, preview = None):
    # Look up long URL from short path ID
    # If not preview:
    # Redirect user.
    # If preview:
    # Show the user a page with the long URL and let them take themselves there.
    return "lookup"


