from flask_sqlalchemy import SQLAlchemy
from app import app,db
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
    wgust = []
    wdir = []
    solar = []
    precip = []
    strikes = []
    
    with open(filename) as f:
        for line in f:
            line = line.strip().split(',')
            
            if len(line) == 9:
                addon = 0
                wscale = 3 #multiply wind speed by 3 for anemometer calibration
                wgust.append(float(line[4])*wscale)
            elif len(line) == 10:
                addon = 1
                wgust.append(float(line[5]))
                wscale = 1
            
            dates.append(datetime.strptime(f"{line[0]}", "%Y%m%d%H%M%S"))
            ta.append(float(line[1]))
            rh.append(float(line[2]))
            pres.append(float(line[3]))
            wspd.append(float(line[4])*wscale)
            wdir.append(float(line[5+addon]))
            solar.append(float(line[6+addon]))
            precip.append(float(line[7+addon]))
            strikes.append(float(line[8+addon]))
            
            
    return dates, ta, rh, pres, wspd, wgust, wdir, solar, precip, strikes
            
            

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
    wgust = []
    wdir = []
    solar = []
    precip = []
    strikes = []
    
    for file in allfiles:
        
        if file[:3] == "WxO": #only csv files
            fdates, fta, frh, fpres, fwspd, fwgust, fwdir, fsolar, fprecip, fstrikes = readfile(csvdir + file)
                
            for (cdate,cta,crh,cpres,cwspd,cwgust,cwdir,csolar,cprecip,cstrikes) in zip(fdates, fta, frh, fpres, fwspd, fwgust, fwdir, fsolar, fprecip, fstrikes):
                dates.append(cdate)
                ta.append(cta)
                rh.append(crh)
                pres.append(cpres)
                wspd.append(cwspd)
                wgust.append(cwgust)
                wdir.append(cwdir)
                solar.append(csolar)
                precip.append(cprecip)
                strikes.append(cstrikes)
                
    return dates, ta, rh, pres, wspd, wgust, wdir, solar, precip, strikes

    


if __name__ == "__main__":
    
    #reading CSV files (WxStation formatted) into lists by variable
    csvdir = "../wxdata/initdata_2024/"
    dates, ta, rh, pres, wspd, wgust, wdir, solar, precip, strikes = csv_to_lists(csvdir)
    
    #creating db
    if os.path.exists('instance/wxobs.db'):
        os.remove('instance/wxobs.db')
        
    app.app_context().push()
    db.create_all()
    
    #appending data to database
    from app import wxobs
    
    #adding all entries to db
    i = 0
    for (cdate,cta,crh,cpres,cwspd,cwgust,cwdir,csolar,cprecip,cstrikes) in zip(dates, ta, rh, pres, wspd, wgust, wdir, solar, precip, strikes):
        i += 1
        entry = wxobs(id=i, date=cdate, temp=cta, rh=crh, pres=cpres, wspd = cwspd, wgust = cwgust, wdir = cwdir, precip=cprecip, solar=csolar, strikes=cstrikes)
        db.session.add(entry)
        
    db.session.commit()
    


