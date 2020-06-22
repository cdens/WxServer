from flask_sqlalchemy import SQLAlchemy
from app import db
from datetime import datetime
from dateutil import tz
import os


tozone = tz.gettz('UTC')
fromzone = tz.gettz('America/New York')
def replacetimezone(inputdate,inputzone,outputzone):
    
    inputdate = inputdate.replace(tzinfo=inputzone)
    outputdate = inputdate.astimezone(outputzone)
    
    return outputdate


def readfile(filename):
    
    dates = []
    T = []
    RH = []
    pres = []
    
    with open("data/" + filename) as f:
        for line in f:
            line = line.strip().split()
            
            cdt = datetime.strptime(f"{filename[1:9]} {line[0]} {line[1]}", "%Y%m%d %I:%M %p")
            cdatetime = replacetimezone(cdt,fromzone,tozone)
            
            dates.append(cdatetime)
            T.append(float(line[2]))
            RH.append(float(line[6]))
            pres.append(np.round(33.8639*float(line[13]),1))
        
    return dates, T, RH, pres


#creating db
if os.path.exists('wxobs.db'):
    os.remove('wxobs.db')
db.create_all()

#appending data to database
from app import wxobs

allfiles = ["d20200613.txt", "d20200614.txt", "d20200615.txt", "d20200616.txt", "d20200617.txt", "d20200618.txt", "d20200619.txt"]

i = 0
for file in allfiles:
    dates,T,RH,pressure = readfile(file)
    
    for (d,t,q,p) in zip(dates, T, RH, pressure):
        i += 1
        entry = wxobs(id=i, date=d, temp=t, rh=q, pres=p)
        db.session.add(entry)
    
db.session.commit()


#check that data has been added successfully
print(wxobs.query.all())