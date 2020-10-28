from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm 
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import InputRequired, Email, Length
from flask_sqlalchemy  import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from database_setup import Department, Base, Req_Status, Req_Priorities, Time_Units, Req_Type, Requests, User, Printers, Vlans, Vlan_Devices
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from flask import session as Session
from sqlalchemy import desc
from flask_wtf import Form
from wtforms.fields.html5 import DateField
from datetime import datetime
from datetime import timedelta
from sqlalchemy import exc
#from threading import RLock
import random
#from multiprocessing import Process, Value
import threading
import time
import urllib
import pyodbc 
import datetime as DateTime
import businesstimedelta
#sql_lock=RLock()
NetThresh=60 # 2 minutes
HWThresh=720
SWThresh=720
OnlineSuppThresh=60
extPend=240
extTh=240
NetPen=30
hwpen=480
swpen=480
onlinepen=10
app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#SQLALCHEMY_TRACK_MODIFICATIONS = False
bootstrap = Bootstrap(app)
params = urllib.parse.quote_plus("DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;PORT=1433;DATABASE=IT_DB;UID=SA;PWD=P@ssw0rd;MARS_Connection=Yes;")
engine = create_engine("mssql+pyodbc:///?odbc_connect=%s" % params ,pool_size=20, max_overflow=0)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def monitoring_loop():
    workday = businesstimedelta.WorkDayRule(start_time=DateTime.time(8),
                                            end_time=DateTime.time(16),
                                            working_days=[0,1,2,3,5,6])
    lunchbreak = businesstimedelta.LunchTimeRule(start_time=DateTime.time(12),end_time=DateTime.time(13),working_days=[0,1,2,3,5,6])                                            
    businesshours = businesstimedelta.Rules([workday, lunchbreak])
    while True:
        #if datetime.now().strftime("%H:%M:%S")=="15:59:59" or datetime.now().strftime("%H:%M:#%S")=="12:30:00":
        session = DBSession()  
        UserRequests= session.query(Requests).filter(Requests.Status_Name!="Solved").all()     
        currentTime=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        #print("Saving Changes")
        datetimeFormat = '%Y-%m-%d %H:%M:%S'
        for req in UserRequests:
            if req.Status_Name=="Opened" :
                bdiff=businesshours.difference(datetime.strptime(str(req.Record_Created), datetimeFormat) ,datetime.strptime(currentTime, datetimeFormat))
                req.OpenedToPending =bdiff.hours*60+bdiff.seconds/60
                req.PendingToSolved =0
                session.add(req)
            elif req.Status_Name=="Pending" :
                pdiff=businesshours.difference(datetime.strptime(str(req.FirstResponseAt), datetimeFormat) ,datetime.strptime(currentTime, datetimeFormat))
                req.PendingToSolved =pdiff.hours*60+pdiff.seconds/60
                session.add(req)
        session.expire_on_commit = False####################>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        session.commit()
        session.close()
        print("Changed Saved Successfully")
        time.sleep(60)

monitoring_thread = threading.Thread(target = monitoring_loop)
monitoring_thread.daemon=True
monitoring_thread.start()

#class User(UserMixin, db.Model):
  #  id = db.Column(db.Integer, primary_key=True)
    #username = db.Column(db.String(15), unique=True)
   # email = db.Column(db.String(50), unique=True)
  #  password = db.Column(db.String(80))


@login_manager.user_loader
def load_user(user_id):
    return session.query(User).get(int(user_id))

class LoginForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(), Length(min=4, max=80)])
    password = PasswordField('password', validators=[InputRequired(), Length(min=1, max=80)])
    remember = BooleanField('remember me')

class RegisterForm(FlaskForm):
    #email = StringField('email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])
    username = StringField('username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('password', validators=[InputRequired(), Length(min=8, max=80)])

#@app.route('/')
#def index():
#    return render_template('index.html')
@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    session = DBSession()
    form = LoginForm()

    if form.validate_on_submit():
        try:
            user = session.query(User).filter_by(name=form.username.data).first()
        finally:
            if user:
                if user.Password== form.password.data:
                    login_user(user, remember=form.remember.data)
                    Session['user_id']=user.id
                    Session['dept_id']=user.dept_id
                    if user.dept_id==1:
                        return redirect(url_for('Cases'))
                    else :
                        return redirect(url_for('UserRequests'))
            flash('Incorrect Username Or PassWord')
            return render_template('loginInvalid.html', form=form)
    return render_template('login.html', form=form)

@app.route('/ITMODE/', methods=['GET', 'POST'])
@app.route('/ITMODE/Cases/', methods=['GET', 'POST'])
@login_required
def Cases():
        if Session.get('user_id') is None or Session['dept_id']!=1:
            return redirect(url_for('login'))
            
        else:
            Page='Cases'
            session = DBSession()
            connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
            session.close()
            if request.method == 'GET':
                session = DBSession()
                status= session.query(Req_Status.Status_name)
                session.close()
                return render_template('DefaultAdmin.html', page=Page, title='All User Cases', conn=connUser,St=status)
            else:
                Status = request.form.get('Status')
                session = DBSession()                
                status= session.query(Req_Status.Status_name)
                UserRequests= session.query(Requests).filter_by(Status_Name=Status).order_by(desc(Requests.Record_Created)).all()              
                session.close()
                return render_template('DefaultAdmin.html', page=Page, title='All User Cases',conn=connUser, rows=UserRequests,St=status,NThreshHold=NetThresh, OThreshHold=OnlineSuppThresh, SWThreshHold=SWThresh, HWThreshHold=HWThresh, swpend=swpen, hwpend=hwpen, NetPend=NetPen, onlinepend=onlinepen, exPend=extPend, exTh=extTh)

@app.route('/ITMODE/Report/', methods=['GET', 'POST'])
@login_required
def FullReport():
        if Session.get('user_id') is None or Session['dept_id']!=1:
            return redirect(url_for('login'))
        else:
            Page='Report'
            session = DBSession()
            connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
            session.close()
            currentDate=datetime.now().strftime("%Y-%m-%d")
            if request.method == 'GET':
                session = DBSession()
                fullreq=session.query(Requests).order_by(desc(Requests.id)).all()
                session.close()
                return render_template('FullReport.html', page=Page, title='All User Cases',conn=connUser, defrows=fullreq, NThreshHold=NetThresh, OThreshHold=OnlineSuppThresh, SWThreshHold=SWThresh, HWThreshHold=HWThresh, swpend=swpen, hwpend=hwpen, NetPend=NetPen, onlinepend=onlinepen, exPend=extPend, exTh=extTh, crdate=currentDate)
            else:
                session = DBSession()
                try:
                    DateFrom= request.form['From']
                    DateTo = request.form['To']
                    DateToTh=datetime.strptime(request.form['To'], "%Y-%m-%d")+timedelta(days=1)
                except ValueError:
                    DateFrom=currentDate
                    DateTo=currentDate
                    DateToTh=datetime.strptime(DateTo, "%Y-%m-%d")+timedelta(days=1)
                    flash("please Enter Valid Date", 'error')
                AllReq= session.query(Requests).filter(Requests.Record_Created>=DateFrom).filter(Requests.Record_Created<=DateToTh).order_by(desc(Requests.id)).all()
                session.close()
                return render_template('FullReport.html', page=Page, title='All User Cases',conn=connUser, rows=AllReq, NThreshHold=NetThresh, OThreshHold=OnlineSuppThresh, SWThreshHold=SWThresh, HWThreshHold=HWThresh, Dfrom=DateFrom, Dto=DateTo, swpend=swpen, hwpend=hwpen, NetPend=NetPen, onlinepend=onlinepen, exPend=extPend, exTh=extTh, crdate=currentDate)

@app.route('/ITMODE/Users/New/', methods=['GET', 'POST'])
@login_required
def AddNewUser():
    session = DBSession()
    dept= session.query(Department).order_by(Department.Dept_name)
    session.close()
    if Session.get('user_id') is None or Session['dept_id']!=1:
        return redirect(url_for('login'))
    else:
        Page='User'
        session = DBSession()
        connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
        session.close()
        if request.method == 'GET':
            return render_template('RegisterNewUser.html', page=Page, Dept=dept, conn=connUser)
        else:
            session = DBSession()
            Name= request.form['Name']
            PassWord= request.form['Password']
            Departments = request.form['Department']
            IP= request.form['ip']
            newUser = User(name=Name, Password=PassWord, dept_id=Departments, ip=IP )
            session.add(newUser)
            session.commit()
            flash('New User %s Successfully Created' % newUser.name)
            session.close()
            return redirect(url_for('UserModifier'))

@app.route('/ITMODE/Users/', methods=['GET',  'POST'])
@login_required
def UserModifier():
        if Session.get('user_id') is None or Session['dept_id']!=1:
            return redirect(url_for('login'))
        else:
            Page='User'
            session = DBSession()
            connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
            departments= session.query(Department).order_by(Department.Dept_name)
            session.close()
            if request.method == 'GET':
                return render_template('DefaultAdminSelectDepartment.html', page=Page, title='Users' ,conn=connUser,dept=departments)
            else:
                session = DBSession()
                department_id = request.form.get('departments')
                depname=session.query(Department).filter(Department.id==department_id).one()
                Users=session.query(User).filter(User.dept_id==department_id).order_by(User.name)
                session.close()
                return render_template('DefaultAdminSelectDepartment.html', page=Page, title='Users' ,conn=connUser,users=Users,dept=departments, dname=depname)

@app.route('/ITMODE/Printers/', methods=['GET',  'POST'])
@login_required
def PrinterModifier():
        if Session.get('user_id') is None or Session['dept_id']!=1:
            return redirect(url_for('login'))
        else:
            Page='Printer'
            session = DBSession()
            connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
            departments= session.query(Department).order_by(Department.Dept_name)
            session.close()
            if request.method == 'GET':
                return render_template('DefaultAdminPrinterDepartment.html', page=Page, title='Printers' ,conn=connUser,dept=departments)
            else:
                session = DBSession()
                department_id = request.form.get('departments')
                depname=session.query(Department).filter(Department.id==department_id).one()
                Pr=session.query(Printers).filter(Printers.Dept_ID==department_id).order_by(Printers.Type)
                session.close()
                return render_template('DefaultAdminPrinterDepartment.html', page=Page, title='Printers' ,conn=connUser,pr=Pr,dept=departments, dname=depname)


@app.route('/ITMODE/Vlans/', methods=['GET',  'POST'])
@login_required
def VlanModifier():
        if Session.get('user_id') is None or Session['dept_id']!=1:
            return redirect(url_for('login'))
        else:
            Page='Vlan'
            session = DBSession()
            connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
            vlans= session.query(Vlans).order_by(Vlans.Vlan)
            session.close()
            if request.method == 'GET':
                return render_template('DefaultAdminSelectVlan.html', page=Page, title='Vlans' ,conn=connUser,vname=vlans)
            else:
                session = DBSession()
                department_id = request.form.get('departments')
                depname=session.query(Department).filter(Department.id==department_id).one()
                Pr=session.query(Printers).filter(Printers.Dept_ID==department_id).order_by(Printers.Type)
                session.close()
                return render_template('DefaultAdminPrinterDepartment.html', page=Page, title='Printers' ,conn=connUser,pr=Pr,dept=departments, dname=depname)


@app.route('/ITMODE/Printers/New/', methods=['GET', 'POST'])
@login_required
def AddNewPrinter():
    session = DBSession()
    dept= session.query(Department).order_by(Department.Dept_name)
    session.close()
    if Session.get('user_id') is None or Session['dept_id']!=1:
        return redirect(url_for('login'))
    else:
        Page='Printer'
        session = DBSession()
        connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
        session.close()
        if request.method == 'GET':
            return render_template('RegisterNewPrinter.html', page=Page,Dept=dept,conn=connUser)
        else:
            session = DBSession()
            Ptype= request.form['Type']
            description= request.form['Description']
            Departments = request.form['Department']
            ip= request.form['ip']
            newPrinter = Printers(Type=Ptype, Description=description, Dept_ID=Departments, IP=ip )
            session.add(newPrinter)
            session.commit()
            flash('New Printer %s Successfully Created' % newPrinter.Type)
            session.close()
            return redirect(url_for('PrinterModifier'))

@app.route('/ITMODE/Printers/<int:Printer_ID>/AdminPrinterEdit', methods=['GET', 'POST'])
@login_required
def EditPrinterAdmin(Printer_ID):
    if Session.get('user_id') is None or Session['dept_id']!=1:
            return redirect(url_for('login'))           
    else:
        Page='Printer'
        session = DBSession()
        connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
        Printerdata = session.query(Printers).filter(Printers.ID==Printer_ID).one()
        session.close()
        if request.method == 'POST':
            if request.form['Type']:
                Printerdata.Type = request.form['Type']
            if request.form['IP']:
                Printerdata.IP = request.form['IP']
            if request.form['Dept_ID']:
                Printerdata.Dept_ID = request.form['Dept_ID']
            if request.form['Description']:
                Printerdata.Description = request.form['Description']
            session = DBSession()
            session.add(Printerdata)
            session.commit()
            flash('Printer Successfully Edited')
            session.close()
            return redirect(url_for('PrinterModifier'))
        else:
            session = DBSession()
            Printerdata = session.query(Printers).filter(Printers.ID==Printer_ID).one()
            dept=session.query(Department).order_by(Department.Dept_name)
            session.close()
            return render_template('editPrinterAdmin.html', page=Page,conn=connUser, printerData=Printerdata,Dept=dept )

@app.route('/ITMODE/Printers/<int:Printer_ID>/AdminPrinterDelete/', methods=['GET', 'POST'])
@login_required
def DeletePrinterAdmin(Printer_ID):
    session = DBSession()
    deletedPrinter = session.query(Printers).filter_by(ID=Printer_ID).one()
    session.close()
    if Session.get('user_id') is None or Session['dept_id']!=1:
        return redirect(url_for('login'))      
    else:
        Page='Printer'
        session = DBSession()
        connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
        session.close()
        if request.method == 'POST':
            session = DBSession()
            session.delete(deletedPrinter)
            session.commit()
            flash('Printer '+'%s Successfully Deleted' % deletedPrinter.Type)
            session.close()
            return redirect(url_for('PrinterModifier'))
        else:        
            return render_template('deletePrinterAdmin.html', page=Page,conn=connUser, Printer=deletedPrinter) 

@app.route('/ITMODE/Users/AllUsers/', methods=['GET'])
@login_required
def AllUserSearch():
        if Session.get('user_id') is None or Session['dept_id']!=1:
            return redirect(url_for('login'))
        else:
            Page='User'
            session = DBSession()
            connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
            allUsers= session.query(User.id,User.name,User.Device_Specs,User.ip,Department.Dept_name).join(Department,User.dept_id==Department.id).order_by(User.name).all()
            
            dept=session.query(Department)
            session.close()
            return render_template('DefaultAdminSearchUser.html', page=Page, title='Users' ,conn=connUser,usr=allUsers, dep=dept)
           
            #elif request.method == 'POST' :
             #   session = DBSession()
               #uName = request.form['UserName']
              #  try:
             #       search = "%{}%".format(uName)
             #   except UnicodeEncodeError:
               #     session.close()
               #     flash("Please Use Only English Letters", 'error')
              #  except UnicodeEncodeError:
               #     session.close()
                #    flash("Please Use Only English Letters", 'error')
                 #   return redirect(url_for('AllUserSearch'))
                #Users=session.query(User.id,User.name,User.ip,User.Device_Specs,Department.Dept_name).join(Department,User.dept_id==Department.id).filter(User.name.like(search)).order_by(User.name).all()
                #session.close()
                #return render_template('DefaultAdminSearchUser.html', page=Page, title='Users' ,conn=connUser,usr=Users, dep=dept, un=uName)
            #elif request.method == 'POST' and request.form.get("UserIP",False) :
            #    session = DBSession()
            #    uIP = request.form['UserIP']
            #    searchIP = "%{}%".format(uIP)
            #    Users=session.query(User.id,User.name,User.ip,User.Device_Specs,Department.Dept_name).join(Department,User.dept_id==Department.id).filter(User.ip.like(searchIP)).order_by(User.name).all()
            #    session.close()
            #    return render_template('DefaultAdminSearchUser.html', page=Page, title='Users' ,conn=connUser,usr=Users, dep=dept, ui=uIP)
            #else :
            #    return render_template('DefaultAdminSearchUser.html', page=Page, title='Users' ,conn=connUser,usr=allUsers, dep=dept)
                #return '<h1> Internal Error, We Are Working On Solving It, Please Call 2503</h1>'

@app.route('/ITMODE/Users/AllUserSearchName/', methods=['POST'])
@login_required
def AllUserSearchName():
    re = request.form
    try:
        for key in re.keys():
            d = key.strip('"')
        search = "%{}%".format(d)
    except UnicodeEncodeError:
        er = {
            "Error" : "Please Use Only English Letters"
        }
        return jsonify(er)
    session = DBSession()
    allUsers= session.query(User.id,User.   name,User.ip,User.Device_Specs,Department.Dept_name).join(Department,User.dept_id==Department.id).filter(User.name.like(search)).order_by(User.name).all()
    session.close()
    userjson ={}
    countuser = 0
    for user in allUsers:
        userjson[countuser] ={
            "id" : user.id,
            "name" : user.name,
            "Device_Specs" : user.Device_Specs,
            "ip" : user.ip,
            "Dept_name" : user.Dept_name
        }
        countuser+=1
    return jsonify(userjson)


@app.route('/ITMODE/Users/AllUserSearchIp/', methods=['POST'])
@login_required
def AllUserSearchIp():
    re = request.form
    try:
        for key in re.keys():
            d = key.strip('"')
        searchIP = "%{}%".format(d)
       # print(searchIP)
    except UnicodeEncodeError:
        er = {
            "Error": "Please Use Only Numbers"
        }
        return jsonify(er)
    session = DBSession()
    allUsers=session.query(User.id,User.name,User.ip,User.Device_Specs,Department.Dept_name).join(Department,User.dept_id==Department.id).filter(User.ip.like(searchIP)).order_by(User.ip).all()
    session.close()
    userjson = {}
    countuser = 0
    for user in allUsers:
        userjson[countuser] = {
            "id": user.id,
            "name": user.name,
            "Device_Specs": user.Device_Specs,
            "ip": user.ip,
            "Dept_name": user.Dept_name
        }
        countuser += 1
    return jsonify(userjson)

@app.route('/ITMODE/Printers/AllPrinters/', methods=['GET'])
@login_required
def AllPrinterSearch():
        if Session.get('user_id') is None or Session['dept_id']!=1:
            return redirect(url_for('login'))
        else:
            Page='Printer'
            session = DBSession()
            connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
            allPrinters= session.query(Printers.ID,Printers.Type,Printers.IP,Printers.Description,Department.Dept_name).join(Department,Printers.Dept_ID==Department.id).order_by(Printers.Type).all()
            dept=session.query(Department).order_by(Department.Dept_name)
            session.close()
            return render_template('DefaultAdminSearchPrinter.html', page=Page, title='Printers' ,conn=connUser,prnt=allPrinters, dep=dept)

            # elif request.method == 'POST' and request.form.get("PrinterType",False) :
            #     session = DBSession()
            #     prType = request.form['PrinterType']
            #     try:
            #         search = "%{}%".format(prType)
            #     except UnicodeEncodeError:
            #         session.close()
            #         flash("Please Use Only English Letters", 'error')
            #         return redirect(url_for('AllPrinterSearch'))
            #     Printerss=session.query(Printers.ID,Printers.Type,Printers.IP,Printers.Description,Department.Dept_name).join(Department,Printers.Dept_ID==Department.id).filter(Printers.Type.like(search)).order_by(Printers.Type).all()
            #     session.close()
            #     return render_template('DefaultAdminSearchPrinter.html', page=Page, title='Printers' ,conn=connUser,prnt=Printerss, dep=dept, pt=prType)
            # elif request.method == 'POST' and request.form.get("PrinterIP",False) :
            #     session = DBSession()
            #     pIP = request.form['PrinterIP']
            #     searchIP = "%{}%".format(pIP)
            #     Printerss=session.query(Printers.ID,Printers.Type,Printers.IP,Printers.Description,Department.Dept_name).join(Department,Printers.Dept_ID==Department.id).filter(Printers.IP.like(searchIP)).order_by(Printers.Type).all()
            #     session.close()
            #     return render_template('DefaultAdminSearchPrinter.html', page=Page, title='Printers' ,conn=connUser,prnt=Printerss, dep=dept, prI=pIP)
            # else :
            #     return render_template('DefaultAdminSearchPrinter.html', page=Page, title='Printers' ,conn=connUser,prnt=allPrinters, dep=dept)
            #     #return '<h1> Internal Error, We Are Working On Solving It, Please Call 2503</h1>'


@app.route('/ITMODE/Users/AllPrinterSearchType/', methods=['POST'])
@login_required
def AllPrinterSearchType():
    re = request.form
    try:
        for key in re.keys():
            pt = key.strip('"')
        searchType = "%{}%".format(pt)
    except UnicodeEncodeError:
        er = {
            "Error" : "Please Use Only English Letters"
        }
        return jsonify(er)
    session = DBSession()
    Printerss=session.query(Printers.ID,Printers.Type,Printers.IP,Printers.Description,Department.Dept_name).join(Department,Printers.Dept_ID==Department.id).filter(Printers.Type.like(searchType)).order_by(Printers.Type).all()
    session.close()
    prjson ={}
    countuser = 0
    for printer in Printerss:
        prjson[countuser] ={
            "id" : printer.ID,
            "type" : printer.Type,
            "ip" : printer.IP,
            "Description" : printer.Description,
            "Dept_name" : printer.Dept_name
        }
        countuser+=1
    return jsonify(prjson)

@app.route('/ITMODE/Users/AllPrinterSearchIP/', methods=['POST'])
@login_required
def AllPrinterSearchIP():
    re = request.form
    try:
        for key in re.keys():
            pIP = key.strip('"')
        searchIP = "%{}%".format(pIP)
    except UnicodeEncodeError:
        er = {
            "Error" : "Please Use Only English Letters"
        }
        return jsonify(er)
    session = DBSession()
    Printerss=session.query(Printers.ID,Printers.Type,Printers.IP,Printers.Description,Department.Dept_name).join(Department,Printers.Dept_ID==Department.id).filter(Printers.IP.like(searchIP)).order_by(Printers.Type).all()
    session.close()
    prjson ={}
    countuser = 0
    for printer in Printerss:
        prjson[countuser] ={
            "id" : printer.ID,
            "type" : printer.Type,
            "ip" : printer.IP,
            "Description" : printer.Description,
            "Dept_name" : printer.Dept_name
        }
        countuser+=1
        print(prjson)
    return jsonify(prjson)

@app.route('/ITMODE/Users/<int:User_ID>/AdminDeleteUser/', methods=['GET', 'POST'])
@login_required
def DeleteUserAdmin(User_ID):
    session = DBSession()
    deleteduser = session.query(User).filter_by(id=User_ID).one()
    session.close()
    if Session.get('user_id') is None or Session['dept_id']!=1:
        return redirect(url_for('login'))      
    else:
        Page='User'
        session = DBSession()
        connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
        session.close()
        if request.method == 'POST':
            session = DBSession()
            session.delete(deleteduser)
            session.commit()
            flash('User '+'%s Successfully Deleted' % deleteduser.name)
            session.close()
            return redirect(url_for('UserModifier'))
        else:        
            return render_template('deleteUserAdmin.html', page=Page,conn=connUser, user=deleteduser) 

@app.route('/ITMODE/Cases/<int:Request_id>/AdminDeleteCase/', methods=['GET', 'POST'])
@login_required
def DeleteUserRequestsAdmin(Request_id):
    session = DBSession()
    deleteduser_Req = session.query(Requests).filter_by(id=Request_id).one()
    session.close()
    if Session.get('user_id') is None or Session['dept_id']!=1:
        return redirect(url_for('login'))      
    else:
        Page='Cases'
        session = DBSession()
        connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
        session.close()
        if request.method == 'POST':
            session = DBSession()
            session.delete(deleteduser_Req)
            session.commit()
            flash('Request No. '+'%s Successfully Deleted' % deleteduser_Req.id)
            session.close()
            return redirect(url_for('Cases'))
        else:        
            return render_template('deleteRequestAdmin.html', page=Page,conn=connUser, req=deleteduser_Req) 

@app.route('/ITMODE/Users/<int:User_ID>/AdminUserEdit', methods=['GET', 'POST'])
@login_required
def EditUserAdmin(User_ID):
    if Session.get('user_id') is None or Session['dept_id']!=1:
            return redirect(url_for('login'))           
    else:
        Page='User'
        session = DBSession()
        connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
        userdata = session.query(User).filter(User.id==User_ID).one()
        session.close()
        if request.method == 'POST':
            if request.form['Name']:
                userdata.name = request.form['Name']
            if request.form['Password']:
                userdata.Password = request.form['Password']
            if request.form['Department']:
                userdata.dept_id = request.form['Department']
            if request.form['ip']:
                userdata.ip = request.form['ip']
            if request.form['Device']:
                userdata.Device_Specs = request.form['Device']
            session = DBSession()
            session.add(userdata)
            session.commit()
            flash('User Successfully Edited')
            session.close()
            return redirect(url_for('UserModifier'))
        else:
            session = DBSession()
            userdata = session.query(User).filter(User.id==User_ID).one()
            dept=session.query(Department).order_by(Department.Dept_name)
            session.close()
            return render_template('editUserAdmin.html', page=Page,conn=connUser, UserData=userdata,Dept=dept )

@app.route('/ITMODE/Cases/NewRequest/', methods=['GET', 'POST'])
@login_required
def NewAdminRequest():
    Page='Cases'
    session = DBSession()
    connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
    session.close()
    if request.method == 'GET':
        session = DBSession()
        Types = session.query(Req_Type.id,Req_Type.Type_name)
        Pr = session.query(Req_Priorities.id,Req_Priorities.Priority_name)
        session.close()
        return render_template('NewAdminRequest.html', page=Page,conn=connUser,name=current_user.name, items=Types,priorities=Pr)
    else:
        session = DBSession()
        name= request.form['Name']
        Description= request.form['Description']
        Type = request.form.get('Type')
        Priority = request.form.get('Priority')
        newRequest = Requests(name=name, Record_Created=datetime.now().strftime("%Y-%m-%d %H:%M"), Description=Description, Assigned_To=None, Type_Name=str(Type), Priority_Name=str(Priority), Status_Name='Opened', User_ID=Session.get('user_id') )
        session.add(newRequest)
        session.commit()
        flash('New Request With Name %s Successfully Created' % newRequest.name)
        session.close()
        return redirect(url_for('Cases'))

@app.route('/NewRequest', methods=['GET', 'POST'])
@login_required
def NewRequest():
    session = DBSession()
    connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
    session.close()
    if request.method == 'GET':
        session = DBSession()
        Types = session.query(Req_Type.id,Req_Type.Type_name)
        Pr = session.query(Req_Priorities.id,Req_Priorities.Priority_name)
        connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
        dept=session.query(Department.Dept_name).filter(Department.id==connUser.dept_id).one()
        session.close()
        return render_template('NewRequest.html',conn=connUser ,name=current_user.name, items=Types,priorities=Pr,Dept=dept )
    else:
        session = DBSession()
        name= request.form['Name']
        Description= request.form['Description']
        Type = request.form.get('Type')
        Priority = request.form.get('Priority')
        newRequest = Requests(name=name, Record_Created=datetime.now().strftime("%Y-%m-%d %H:%M"), Description=Description, Assigned_To=None, Type_Name=str(Type), Priority_Name=str(Priority), Status_Name='Opened', User_ID=Session.get('user_id') )
        session.add(newRequest)
        session.commit()
        flash('New Request With Name %s Successfully Created' % newRequest.name)
        UserRequests= session.query(Requests).filter_by(User_ID=Session.get('user_id')).filter(Requests.Status_Name!='Solved').all()
        session.close()
        return render_template('ReqData.html',conn=connUser , title='User Requests', rows=UserRequests)

@app.route('/UserRequests/User/<int:User_ID>/editPassUser/', methods=['GET', 'POST'])
@login_required
def editPasswordUser(User_ID):
    if Session.get('user_id') is None:
            return redirect(url_for('login'))           
    else:
        session = DBSession()
        connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
        userdata = session.query(User).filter(User.id==User_ID).one()
        session.close()
        if connUser.id!=User_ID:
           return redirect(url_for('logout'))
        else:
            if request.method == 'POST':
                if request.form['Password']:
                    userdata.Password = request.form['Password']
                session = DBSession()
                session.add(userdata)
                session.commit()
                flash('User Password Successfully Edited')
                session.close()
                return redirect(url_for('UserRequests'))
            else:
                session = DBSession()
                userdata = session.query(User).filter(User.id==User_ID).one()
                dept=session.query(Department.Dept_name).filter(Department.id==userdata.dept_id).one()
                session.close()
                return render_template('editPassUser.html',conn=connUser, UserData=userdata,Dept=dept )

@app.route('/UserRequests/', methods=['GET', 'POST'])
@login_required
def UserRequests():
        if Session.get('user_id') is None:
            return redirect(url_for('login'))
            
        else:
            session = DBSession()
            connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
            UserRequests= session.query(Requests).filter_by(User_ID=Session.get('user_id')).filter(Requests.Status_Name!='Solved').all()
            dept=session.query(Department.Dept_name).filter(Department.id==connUser.dept_id).one()
            session.close()
            return render_template('ReqData.html', title='User Requests',conn=connUser , rows=UserRequests,Dept=dept )

@app.route('/ITMODE/Cases/<int:Request_id>/AdminEdit', methods=['GET', 'POST'])
@login_required
def EditUserRequestsAdmin(Request_id):
    if Session.get('user_id') is None or Session['dept_id']!=1:
            return redirect(url_for('login')) 
    else:
        Page='Cases'
        session = DBSession()
        connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
        editeduser_Req = session.query(Requests).filter_by(id=Request_id).one()
        reqOldStat=editeduser_Req.Status_Name
        session.close()
        if request.method == 'POST':
            session = DBSession()
            if request.form['Name']:
                editeduser_Req.name = request.form['Name']
            if request.form['Description']:
                editeduser_Req.Description = request.form['Description']
            if request.form['Type']:
                editeduser_Req.Type_Name = request.form['Type']
            if request.form['Priority']:
                editeduser_Req.Priority_Name = request.form['Priority']
                if request.form['Assigned_To'] is not None:
                    if request.form['Assigned_To']:
                        editeduser_Req.Assigned_To = request.form['Assigned_To']
            if request.form['Status']:
                if request.form['Status']!=reqOldStat:
                    editeduser_Req.Status_Name = request.form['Status']
                    if editeduser_Req.Status_Name == "Pending":
                        editeduser_Req.FirstResponseAt=datetime.now().strftime("%Y-%m-%d %H:%M")
                    if editeduser_Req.Status_Name == "Solved":
                        editeduser_Req.ResolvedAt= datetime.now().strftime("%Y-%m-%d %H:%M")
            if request.form['Time']:
                editeduser_Req.Time_To_Solve = request.form['Time']
            if request.form['Unit']:
                editeduser_Req.UNIT_Name = request.form['Unit']
                session.add(editeduser_Req)
                session.commit()
                flash('Request Successfully Edited')
                session.close()
                return redirect(url_for('Cases'))
        else:
            session = DBSession()
            Types = session.query(Req_Type.Type_name)
            Pr = session.query(Req_Priorities.Priority_name)
            status= session.query(Req_Status.Status_name)
            unit= session.query(Time_Units.Unit_name)
            IT_Mem=session.query(User).filter(User.dept_id==1 ).order_by(User.name)
            session.close()
            return render_template('editRequestAdmin.html', page=Page,conn=connUser,request=editeduser_Req, items=Types,priorities=Pr,mem=IT_Mem, sts=status, units=unit )
    
@app.route('/UserRequests/<int:Request_id>/delete/', methods=['GET', 'POST'])
@login_required
def DeleteUserRequest(Request_id):
    session = DBSession()
    connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
    User_ID=session.query(Requests.User_ID).filter(Requests.id==Request_id).one()
    session.close()
    try:
        if connUser.id!=User_ID[0]:
            #redirect(url_for('logout'))
            Session['user_id']=None
            logout_user()
            return redirect(url_for('login'))
            #return '<h1> YouAre Not Authorized To Do This Action </h1>'
            #return '<h1> conn: '+ str(connUser.id) + ' and usi is : ' + str(User_ID[0]) + '</h1>'
    except TypeError:
        #return '<h1> conn: '+ str(connUser.id) + ' and usi is : ' + str(User_ID[0]) + '</h1>'
        return '<h1> Error Please Call The IT Department </h1>'
    else:
        if request.method == 'POST':
            session = DBSession()
            deleted_Req = session.query(Requests).filter_by(id=Request_id).one()
            session.delete(deleted_Req)
            session.commit()
            flash('Request No. '+'%s Successfully Deleted' % deleted_Req.id)
            session.close()
            return redirect(url_for('UserRequests'))
        else:
            session = DBSession()
            deleted_Req = session.query(Requests).filter_by(id=Request_id).one()
            session.close()        
            return render_template('deleteRequest.html',conn=connUser, req=deleted_Req) ###########################>>

@app.route('/UserRequests/<int:Request_id>/edit/', methods=['GET', 'POST'])
@login_required
def EditUserRequests(Request_id):
    session = DBSession()
    connUser=session.query(User).filter(User.id==Session.get('user_id')).one()
    editeduser_Req = session.query(Requests).filter_by(id=Request_id).one()
    User_ID=session.query(Requests.User_ID).filter(Requests.id==Request_id).one()
    session.close()
    try:
        if connUser.id!=User_ID[0]:
            #redirect(url_for('logout'))
            Session['user_id']=None
            logout_user()
            return redirect(url_for('login'))
            #return '<h1> YouAre Not Authorized To Do This Action </h1>'
            #return '<h1> conn: '+ str(connUser.id) + ' and usi is : ' + str(User_ID[0]) + '</h1>'
    except TypeError:
        #return '<h1> conn: '+ str(connUser.id) + ' and usi is : ' + str(User_ID[0]) + '</h1>'
        return '<h1> Error Please Call The IT Department </h1>'
    else:
        if request.method == 'POST':
            session = DBSession()
            if request.form['Name']:
                editeduser_Req.name = request.form['Name']
            if request.form['Description']:
                editeduser_Req.Description = request.form['Description']
            if request.form['Type']:
                editeduser_Req.Type_Name = request.form['Type']
            if request.form['Priority']:
                editeduser_Req.Priority_Name = request.form['Priority']
            session.add(editeduser_Req)
            session.commit()
            flash('Request Successfully Edited')
            session.close()
            return redirect(url_for('UserRequests'))
        else:
            session = DBSession()
            Types = session.query(Req_Type.Type_name)
            Pr = session.query(Req_Priorities.Priority_name)
            session.close()
            return render_template('editRequest.html',conn=connUser,request=editeduser_Req, items=Types,priorities=Pr)
##############################################################################################
# class ReqTable(Table):
#     name = Col('Name')
#     description = Col('Description')
#     Type = Col('Type')
#     Priority = Col('Priority')
#     Status = Col('Status')

@app.route('/logout')
@login_required
def logout():
    Session['user_id']=None
    session.close()
    logout_user()
    return redirect(url_for('login'))


#def record_loop(loop_on):
  # while True:
      #if loop_on.value == True:
   #   if datetime.now().strftime("%H:%M:%S")=="13:19:00":
    #    print("Commiting Changes")
    #    session.commit()
    #    time.sleep(1)

if __name__ == '__main__':
    FLASK_DEBUG=1
    #app.secret_key = 'super_secret_key'
    #app.debug = True
    #app.run(host='127.0.0.1', port=5000)
