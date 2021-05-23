from flask_sqlalchemy import SQLAlchemy
from app import db
from datetime import datetime, timedelta
import os
import numpy as np
import netCDF4
        

def readfile(filename):
    
    dates = []
    ta = []
    rh = []
    pres = []
    wspd = []
    wdir = []
    solar = []
    precip = []
    strikes = []
    
    with open(filename) as f:
        for line in f:
            line = line.strip().split(',')
            
            dates.append(datetime.strptime(f"{line[0]}", "%Y%m%d %H:%M:%S"))
            ta.append(float(line[1]))
            rh.append(float(line[2]))
            pres.append(float(line[3]))
            wspd.append(float(line[4]))
            wdir.append(float(line[5]))
            solar.append(float(line[6]))
            precip.append(float(line[7]))
            strikes.append(float(line[8]))
            
    return dates, ta, rh, pres, wspd, wdir, solar, precip, strikes
            
            

def csv_to_lists(csvdir):

    #getting list of files to read from
    allfiles = os.listdir(csvdir)
    allfiles.sort() #numerical (chronological) order
        
    #reading in data from CSV files
    dates = []
    ta = []
    rh = []
    pres = []
    wspd = []
    wdir = []
    solar = []
    precip = []
    strikes = []
    
    for file in allfiles:
        
        if file[:3] == "d20": #only csv files
            fdates, fta, frh, fpres, fwspd, fwdir, fsolar, fprecip, fstrikes = readfile(csvdir + file)
                
            for (cdate,cta,crh,cpres,cwspd,cwdir,csolar,cprecip,cstrikes) in zip(fdates, fta, frh, fpres, fwspd, fwdir, fsolar, fprecip, fstrikes):
                dates.append(cdate)
                ta.append(cta)
                rh.append(crh)
                pres.append(cpres)
                wspd.append(cwspd)
                wdir.append(cwdir)
                solar.append(csolar)
                precip.append(cprecip)
                strikes.append(cstrikes)
                
    return dates, ta, rh, pres, wspd, wdir, solar, precip, strikes

    


if __name__ == "__main__":
    
    #reading CSV files (WxStation formatted) into lists by variable
    csvdir = "../wxdata/"
    dates, ta, rh, pres, wspd, wdir, solar, precip, strikes = csv_to_lists(csvdir)
    
    #creating db
    if os.path.exists('wxobs.db'):
        os.remove('wxobs.db')
    db.create_all()
    
    #appending data to database
    from app import wxobs
    
    #adding all entries to db
    i = 0
    for (cdate,cta,crh,cpres,cwspd,cwdir,csolar,cprecip,cstrikes) in zip(dates, ta, rh, pres, wspd, wdir, solar, precip, strikes):
        i += 1
        entry = wxobs(id=i, date=cdate, temp=cta, rh=crh, pres=cpres, wspd = cwspd, wdir = cwdir, precip=cprecip, solar=csolar, strikes=cstrikes)
        db.session.add(entry)
        
    db.session.commit()
    


