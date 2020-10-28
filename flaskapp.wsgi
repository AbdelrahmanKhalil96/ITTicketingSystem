#!/usr/bin/python3                                                                
activate_this = '/var/www/FlaskApp/FlaskApp/venv/bin/activate_this.py'
exec(open(activate_this).read(), dict(__file__=activate_this))
#execfile(activate_this, dict(__file__=activate_this))
import sys
import logging
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/var/www/FlaskApp/")

from FlaskApp import app as application
application.secret_key = 'super_secret_key!'
