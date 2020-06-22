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

    def __repr__(self): #keyword function for everytime the database is updated
        return f'{self.id},{self.date},{self.temp},{self.rh},{self.pres}'
        
        
def parsedboutput(obs):
    date = []
    temp = []
    rh = []
    pres = []
    
    for entry in obs:
        date.append(replacetimezone(entry.date,fromzone,tozone)) #local time
        temp.append(entry.temp)
        rh.append(entry.rh)
        pres.append(entry.pres)
            
    return date,temp,rh,pres


    
        


        
        
        
#######################################################################################
#                                    SITE ROUTING                                     #
#######################################################################################
    
    
#default website link loads current conditions
@app.route('/', methods=['POST','GET']) 
@app.route('/current', methods=['POST','GET']) 
def index():
    
    enddate = datetime(2020,6,20,2,53,0) #TO DEPLOY: replace w/ datetime.utcnow()
    startdate = enddate - timedelta(hours=8)
    
    tableobs = wxobs.query.order_by(-wxobs.id).filter(wxobs.date >= startdate) #observations for plot/table
    obsplot = observations_plot(tableobs) #building plot components given observations
    
    lastob = wxobs.query.order_by(-wxobs.id).first() #orders by recent ob first
    lastobdate = replacetimezone(lastob.date, fromzone, tozone)
    lastobdict = {"date":lastobdate.strftime("%Y-%m-%d %H:%M %Z"), "temp":lastob.temp, "rh":lastob.rh, "pres":lastob.pres}
    
    return render_template('current.html',ob=lastobdict, div_plot=obsplot, tableobs=tableobs) #GET request- show content
    

    
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
    
    
    
    
#TODO: route to update database with new information







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
    date,temp,rh,pres = parsedboutput(obstoplot)
    source = ColumnDataSource(data={"date":date, "temp":temp, "rh":rh, "pres":pres}) #organizing data into columndatasource format
    
    
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
    
    
    #adding legend
    p.legend.location = "top_left"
    p.legend.click_policy="hide"
    
    
    #adding hover tool
    TOOLTIPS=[("Date", "@date{%Y-%m-%d %H:%M}"), ("Temperature (C)", "@temp{00.0}"), ("Humidity (%)", "@rh{00.0}"), ("Pressure (mb)", "@pres{0000.0}")] #setting tooltips for interactive hover
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

    
    
    
