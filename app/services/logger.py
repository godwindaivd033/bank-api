import logging

#---Configuring the log---
logging.basicConfig(format= "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                    level= logging.INFO,
                    handlers= [logging.StreamHandler()])

logger= logging.getLogger(__name__)