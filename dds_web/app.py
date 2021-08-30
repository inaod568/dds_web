"Web API for Data Delivery System"

# IMPORTS ########################################################### IMPORTS #

# Standard library

# Installed

# Own modules
from dds_web import create_app

# CONFIG ############################################################# CONFIG #

app = create_app()

# INITIATE ######################################################### INITIATE #

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
