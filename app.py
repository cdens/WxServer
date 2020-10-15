#!/usr/bin/env python3

from flask import Flask, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy

from bokeh.embed import components
from bokeh.models import ColumnDataSource, HoverTool, PrintfTickFormatter, DatetimeTickFormatter, LinearAxis, Range1d
from bokeh.plotting import figure
from bokeh.transform import factor_cmap

from datetime import datetime, timedelta
from dateutil import tz
import numpy as np
from hashlib import sha1





#######################################################################################
#                                     INITIALIZATION                                  #
#######################################################################################


app = Flask(__name__) #creating app instance
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wxobs.db' #3 slashes = relative path, 4 slashes = absolute
app.add_template_global(np.round, name='round') #allows HTML templates to use np.round() to round values in tables
db = SQLAlchemy(app) #initialize database






#######################################################################################
#                                   DATABASE CONFIGURATION                            #
#######################################################################################


#to initialize database, from cmd line do "from app import db", then "db.create_all()"
class wxobs(db.Model): #class for database
    id = db.Column(db.Integer, primary_key=True) #primary key for database
    date = db.Column(db.DateTime, default=datetime.utcnow)
    temp = db.Column(db.Float, nullable=False) 
    rh = db.Column(db.Float, nullable=False) 
    pres = db.Column(db.Float, nullable=False) 
    wspd = db.Column(db.Float, nullable=False)
    wdir = db.Column(db.Float, nullable=False)
    precip = db.Column(db.Float, nullable=False)
    solar = db.Column(db.Float, nullable=False)
    strikes = db.Column(db.Float, nullable=False)
    
    def __repr__(self): #keyword function for everytime the database is updated
        return f'Entry {self.id}: {self.date.strftime("%y%m%d %H:%M:%S")}'
        
        
def parsedboutput(obs):
    date = []
    temp = []
    rh = []
    pres = []
    wspd = []
    wdir = []
    precip = []
    solar = []
    strikes = []
    
    for entry in obs:
        date.append(replacetimezone(entry.date,fromzone,tozone)) #local time
        temp.append(entry.temp)
        rh.append(entry.rh)
        pres.append(entry.pres)
        wspd.append(entry.wspd)
        wdir.append(entry.wdir)
        precip.append(entry.precip)
        solar.append(entry.solar)
        strikes.append(entry.strikes)
            
    return date,temp,rh,pres,wspd,wdir,precip,solar,strikes


    
        
    
        
        
#######################################################################################
#                                    SITE ROUTING                                     #
#######################################################################################

#default website link loads current conditions
@app.route('/', methods=['POST','GET']) 
@app.route('/current', methods=['POST','GET']) 
def index():
    
    enddate = datetime(2020,7,31,23,0,0)
    #enddate = datetime.utcnow() #current date
    startdate = enddate - timedelta(hours=8)
    
    tableobs = wxobs.query.order_by(-wxobs.id).filter(wxobs.date >= startdate) #observations for plot/table
    obsplot = observations_plot(tableobs) #building plot components given observations
    lastob = wxobs.query.order_by(-wxobs.id).first() #orders by recent ob first
    
    return render_template('current.html',lastob=lastob, div_plot=obsplot, tableobs=tableobs) #GET request- show content
    

    
#route for historical observations #TODO: ADD QUERY BY DATE
@app.route('/historical', methods=['POST','GET']) #create index route so it doesn't ERROR 404
def historical():
    
    #parsing input arguments 
    if request.method == 'GET':
        startdate = parsedatestr(request.args.get('start',False))
        enddate = parsedatestr(request.args.get('end',False))
    elif request.method == 'POST':
        startdate = parsedatestr(request.form['start'])
        enddate = parsedatestr(request.form['end'])
    else:
        startdate = False
        enddate = False
        
    print(startdate)
    print(enddate)
            
    #if one date missing- return 14 day window. If both missing, return 14 day window from present
    if not startdate and not enddate:
        enddate = datetime(2020,6,20,2,53,0) #TO DEPLOY: replace w/ datetime.utcnow()
        startdate = enddate - timedelta(days=14)
    elif not startdate:
        startdate = enddate - timedelta(days=14)
    elif not enddate:
        enddate = startdate + timedelta(days=14)
    elif startdate == enddate:
        startdate -= timedelta(days=1)
        enddate += timedelta(days=1)
            
    #pulling observations
    tableobs = wxobs.query.order_by(wxobs.id).filter((wxobs.date >= startdate) & (wxobs.date <= enddate)) #observations for plot/table
    obsplot = observations_plot(tableobs) #building plot components given observations
    
    #pulling date constraints for date selection tool
    dates = {}
    dates['startdate'] = wxobs.query.order_by(wxobs.id).first().date.strftime("%Y-%m-%d")
    dates['enddate'] = wxobs.query.order_by(-wxobs.id).first().date.strftime("%Y-%m-%d")
    
    return render_template('historical.html', div_plot=obsplot, tableobs=tableobs, dates=dates) #GET request- show content
    
    
    
#route to static overview page of system
@app.route('/piwxoverview', methods=['GET'])
def piwxoverview():
    return render_template('piwxoverview.html') 
        
    
    
#route to static blog page for how to build the wx station
@app.route('/howto', methods=['GET']) 
def howto():
    return render_template('howto.html') 
    
    
    
#route to update database with new information
#73d2be97af11e8ce2144cca61dc2749e643fa6d5 is SHA1 checksum for passphrase required for observation
@app.route('/addnewob', methods=['POST'])
def addnewob():
    
    if sha1(request.form['credential'].encode('utf-8')).hexdigest() == "73d2be97af11e8ce2144cca61dc2749e643fa6d5":
        
        try:
            cdate = datetime.strptime(request.form['date'],"%Y%m%d %H:%M:%S")
            cta = request.form["ta"]
            crh = request.form["rh"]
            cpres = request.form["pres"]
            cwspd = request.form["wspd"]
            cwdir = request.form["wdir"]
            csolar = request.form["solar"]
            cprecip = request.form["precip"]
            cstrikes = request.form["strikes"]
        except KeyError:
            return "MISSING_POST_FIELD"
            
        #adding to database
        lastID = wxobs.query.order_by(-wxobs.id).first().id
        entry = wxobs(id=lastID + 1, date=cdate, temp=cta, rh=crh, pres=cpres, wspd = cwspd, wdir = cwdir, precip=cprecip, solar=csolar, strikes=cstrikes)
        db.session.add(entry)
        db.session.commit()
        
        #return success message to indicate data was added
        return "SUCCESS"
    else:
        return "INVALID_CREDENTIAL"




#######################################################################################
#                                   INTERACTIVE PLOTTING                              #
#######################################################################################


chart_font = 'Helvetica'
chart_title_font_size = '16pt'
chart_title_alignment = 'center'
axis_label_size = '14pt'
axis_ticks_size = '12pt'
default_padding = 30
chart_inner_left_padding = 0.015
chart_font_style_title = 'bold italic'
fig_sizing_mode = "scale_width"
gridcolor = None

def plot_styler(p):
    
    xtickformat = DatetimeTickFormatter(hourmin = ['%H:%M'], hours = ['%H:%M'], days = ['%d %b'], months = ['%b %Y'])
    p.sizing_mode = fig_sizing_mode
    p.title.text_font_size = chart_title_font_size
    p.title.text_font  = chart_font
    p.title.align = chart_title_alignment
    p.title.text_font_style = chart_font_style_title
    p.x_range.range_padding = chart_inner_left_padding
    p.xaxis.formatter = xtickformat
    p.xaxis.axis_label_text_font = chart_font
    p.xaxis.major_label_text_font = chart_font
    p.xaxis.axis_label_standoff = default_padding
    p.xaxis.axis_label_text_font_size = axis_label_size
    p.xaxis.major_label_text_font_size = axis_ticks_size
    p.yaxis.axis_label_text_font = chart_font
    p.yaxis.major_label_text_font = chart_font
    p.yaxis.axis_label_text_font_size = axis_label_size
    p.yaxis.major_label_text_font_size = axis_ticks_size
    p.yaxis.axis_label_standoff = default_padding
    p.xgrid.grid_line_color = gridcolor
    p.ygrid.grid_line_color = gridcolor
    p.background_fill_alpha = 0
    p.border_fill_alpha = 0
    p.toolbar.logo = None
    p.outline_line_color = "black"

    
    
def observations_plot(obstoplot):
    
    #parsing out observations in range to be plotted
    date,temp,rh,pres,wspd,wdir,precip,solar,strikes = parsedboutput(obstoplot)
    source = ColumnDataSource(data={"date":date, "temp":temp, "rh":rh, "pres":pres, "wspd":wspd, "wdir":wdir, "precip":precip, "solar":solar, "strikes":strikes}) #organizing data into columndatasource format
    
    
    #initializing figure
    p = figure(height=400, width=1500, title='', x_axis_type="datetime", toolbar_location="above",
        tools="pan,wheel_zoom,box_zoom,reset")
    p.extra_y_ranges = {}
    p.yaxis.visible = False #drop default y axis
    
    #temperature
    p.extra_y_ranges["temp"] = Range1d(start=np.floor(np.min(temp))-1, end=np.ceil(np.max(temp))+1)
    p.add_layout(LinearAxis(y_range_name="temp", axis_line_color="red"), 'left')
    p.line(x="date", y="temp", source=source, line_color="red", name="Temperature", y_range_name="temp", legend_label="Temperature")
    p.circle(x="date", y="temp", source=source, color="red", name="Temperature", y_range_name="temp",  legend_label="Temperature")
    
    #humidity
    p.extra_y_ranges["rh"] = Range1d(start=np.floor(np.min(rh))-1, end=np.ceil(np.max(rh))+1)
    p.add_layout(LinearAxis(y_range_name="rh", axis_line_color="blue"), 'left')
    p.line(x="date", y="rh", source=source, line_color="blue", name="Humidity", y_range_name="rh", legend_label="Humidity")
    p.circle(x="date", y="rh", source=source, color="blue", name="Humidity", y_range_name="rh", legend_label="Humidity")
    
    #pressure
    p.extra_y_ranges["pres"] = Range1d(start=np.floor(np.min(pres))-1, end=np.ceil(np.max(pres))+1)
    p.add_layout(LinearAxis(y_range_name="pres", axis_line_color="green"), 'left')
    p.line(x="date", y="pres", source=source, line_color="green", name="Pressure", y_range_name="pres", legend_label="Pressure")
    p.circle(x="date", y="pres", source=source, color="green", name="Pressure", y_range_name="pres", legend_label="Pressure")
    
    #wind speed
    p.extra_y_ranges["wspd"] = Range1d(start=np.floor(np.min(wspd))-1, end=np.ceil(np.max(wspd))+1)
    p.add_layout(LinearAxis(y_range_name="wspd", axis_line_color="orange"), 'left')
    p.line(x="date", y="wspd", source=source, line_color="orange", name="Wind Speed", y_range_name="wspd", legend_label="Wind Speed")
    p.circle(x="date", y="wspd", source=source, color="orange", name="Wind Speed", y_range_name="wspd", legend_label="Wind Speed")
    
    #wind direction
    p.extra_y_ranges["wdir"] = Range1d(start=np.floor(np.min(wdir))-1, end=np.ceil(np.max(wdir))+1)
    p.add_layout(LinearAxis(y_range_name="wdir", axis_line_color="purple"), 'left')
    p.circle(x="date", y="wdir", source=source, color="purple", name="Wind Direction", y_range_name="wdir", legend_label="Wind Direction")
    
    #precipitation TODO- MAKE BAR
    p.extra_y_ranges["precip"] = Range1d(start=np.floor(np.min(precip)), end=np.ceil(np.max(precip))+1)
    p.add_layout(LinearAxis(y_range_name="precip", axis_line_color="blue"), 'left')
    p.vbar(x="date",top="precip", width = .9, fill_alpha = .5, fill_color = 'blue', line_alpha = .5, line_color='blue', source=source, name="Precipitation", y_range_name="precip", legend_label="Precipitation")

    
    #solar radiation
    p.extra_y_ranges["solar"] = Range1d(start=np.floor(np.min(solar))-1, end=np.ceil(np.max(solar))+1)
    p.add_layout(LinearAxis(y_range_name="solar", axis_line_color="yellow"), 'left')
    p.line(x="date", y="solar", source=source, line_color="yellow", name="Solar Radiation", y_range_name="solar", legend_label="Solar Radiation")
    p.circle(x="date", y="solar", source=source, color="yellow", name="Solar Radiation", y_range_name="solar", legend_label="Solar Radiation")
    
    #lightning strikes
    p.extra_y_ranges["strikes"] = Range1d(start=np.floor(np.min(strikes)), end=np.ceil(np.max(strikes))+1)
    p.add_layout(LinearAxis(y_range_name="strikes", axis_line_color="yellow"), 'left')
    p.vbar(x="date",top="strikes", width = .9, fill_alpha = .5, fill_color = 'yellow', line_alpha = .5, line_color='yellow', source=source, name="Lightning Strikes", y_range_name="strikes", legend_label="Lightning Strikes")
    
    
    #adding legend
    p.legend.location = "top_left"
    p.legend.click_policy="hide"
    
    
    #adding hover tool
    TOOLTIPS=[("Date", "@date{%Y-%m-%d %H:%M}"), 
                ("Temperature (C)", "@temp{00.0}"), 
                ("Humidity (%)", "@rh{00.0}"), 
                ("Pressure (mb)", "@pres{0000.0}")] #setting tooltips for interactive hover
    hovertool = HoverTool(tooltips=TOOLTIPS, formatters={'@date': 'datetime'}) # use 'datetime' formatter for '@date' field
    p.add_tools(hovertool)
    
    plot_styler(p) #applying global stylings for plot
    
    script,div = components(p) #pulling javascript/html components to embed in webpage
    
    return script + div
    

    


        
        
    
    
    
#######################################################################################
#                                DATE FORMATTING                                      #
#######################################################################################


#time zone configuration
fromzone = tz.gettz('UTC')
tozone = tz.gettz('America/New York')
def replacetimezone(inputdate,inputzone,outputzone):
    
    inputdate = inputdate.replace(tzinfo=inputzone)
    outputdate = inputdate.astimezone(outputzone)
    
    return outputdate
    
    
    
def parsedatestr(datestr):
    if datestr:
        try:
            if len(datestr) == 4:
                date = datetime.strptime(datestr,'%Y')
                
            elif len(datestr) == 6:
                date = datetime.strptime(datestr,'%Y%m')
                
            elif len(datestr) == 8:
                date = datetime.strptime(datestr,'%Y%m%d')
                
            elif len(datestr) == 10:
                try:
                    date = datetime.strptime(datestr,'%Y-%m-%d')
                except ValueError:
                    date = datetime.strptime(datestr,'%Y%m%d%H')
                    
            elif len(datestr) == 12:
                date = datetime.strptime(datestr,'%Y%m%d%H%M')
            
            elif len(datestr) == 13:
                date = datetime.strptime(datestr,'%Y-%m-%d-%H')
                    
            elif len(datestr) == 14:
                date = datetime.strptime(datestr,'%Y%m%d%H%M%S')
                
            elif len(datestr) == 16:
                date = datetime.strptime(datestr,"%Y-%m-%d-%H-%M")
                
            elif len(datestr) == 19:
                date = datetime.strptime(datestr,"%Y-%m-%d-%H-%M-%S")
                
                
        except:
            date = False
    else:
        date = False
        
    return date
        
        
        
        
        
        
        
#######################################################################################
#                                   MAIN                                              #
#######################################################################################        

if __name__ == "__main__":
    app.run(debug=True)

    
    
    
