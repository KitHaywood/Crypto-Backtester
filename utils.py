from google.cloud.sql.connector import Connector
import sqlalchemy
import os
import pdb
import numpy as np


def db_credential_organiser():
    """
    Adds environment keys and variables for db connection objs
    """
    # THOMAS - you will need to target the correct space for the ssh keys
    if 'Crypto-Dash' in os.getcwd(): # this is my main working folder
        path = r"""/Users/kithaywood/Crypto-Dash/goodkeys2.json"""
    elif "WSL_DISTRO_NAME" in os.environ: # this one will be missed unless your in colab
        path = r"""/mnt/c/Users/kit.haywood/Documents/Crypto-Project/CryptoFourier/goodkeys2.json"""
    else: # suggest you replace this with a local abs path if it cannot see the ssh keys. 
        path =  os.path.join(os.getcwd(),'goodkeys2.json')
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
    os.environ['DB_USER'] = "kit-root"
    os.environ['DB_PROJECTID']  ="principal-sonar-232616:europe-west1:crypto-analysis"
    os.environ["DB_NAME"] = "TEST"
    os.environ["DB_PASS"] = "mulberry-1206"
    return None

db_credential_organiser()
connector = Connector()

def getconn():
    """
    sql connector object constructor
    """
    conn = connector.connect(
        os.environ["DB_PROJECTID"],
        "pg8000",
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
        db=os.environ["DB_NAME"],
    )
    return conn

db = sqlalchemy.create_engine(
        "postgresql+pg8000://",
        creator=getconn,
    )
con = db.connect()

def fourier(x, *a):
    """
    Fourier function, takes variable num of coefs and evaluates an arbitrary
    degree fourier function at a unique numeric value of x (representing time)

    Returns: Float post-evaluation. Main usage is in fitfunc (coefs) & devobs (signalling)
    """
    # in format that curve_fit accepts *a is how you create degree variation
    ret = a[0]
    for deg in range(2, len(a)):
        ret += a[deg] * np.sin((deg + 1) * x * 0.01)  # optimisation parameter - unrestrainedFourier uses a[-1] in place of 0.01 (ano opter dimension)
    return ret
