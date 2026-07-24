#---Building the helper method that aids in generating the reference---
import string
from datetime import datetime, UTC
import random

def generate_reference(prefix: str) -> str:
    set_time= datetime.now(UTC)

    #--Configuring the string format for the time--
    stamped_time= set_time.strftime("%Y%m%d%H%M%S")

    #--Assigning the random values--
    random_fix= "".join(random.choices(string.ascii_uppercase + string.digits, k=4))

    #---Combining everything together---
    return f"{prefix}{stamped_time}{random_fix}"