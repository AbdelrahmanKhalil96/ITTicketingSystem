import os
import sys
import datetime
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

Base = declarative_base()

class Vlans(Base):
    __tablename__ = 'vlans'
    id = Column(Integer, primary_key=True)
    Vlan = Column(String(50), nullable=False)

class Vlan_Devices(Base):
    __tablename__ = 'vlan_Devices'
    id = Column(Integer, primary_key=True)
    Vlan_id = Column(String(50), nullable=False)
    ip= Column(Integer, nullable=False)
    Status= Column(String(50), nullable=True)
    Description= Column(String(400), nullable=False)

class Department(Base):
    __tablename__ = 'department'

    id = Column(Integer, primary_key=True)
    Dept_name = Column(String(250), nullable=False)

class Req_Status(Base):
    __tablename__ = 'req_Status'

    id = Column(Integer, primary_key=True)
    Status_name = Column(String(250), nullable=False)

class Req_Type(Base):
    __tablename__ = 'req_Type'

    id = Column(Integer, primary_key=True)
    Type_name = Column(String(250), nullable=False)

class Req_Priorities(Base):
    __tablename__ = 'req_Priorities'

    id = Column(Integer, primary_key=True)
    Priority_name = Column(String(250), nullable=False)

class Time_Units(Base):
    __tablename__ = 'time_Units'

    id = Column(Integer, primary_key=True)
    Unit_name = Column(String(250), nullable=False)

class User(Base,UserMixin):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(250), nullable=False)
    Password = Column(String(250), nullable=False)
    dept_id = Column(Integer, ForeignKey('department.id'))
    department = relationship(Department, single_parent=True)
    ip= Column(String(400), nullable=True)
    Device_Specs=Column(String(4000), nullable=True)

class Requests(Base):
    __tablename__ = 'requests'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(250), nullable=False)
    Record_Created= Column(Integer, default=datetime.datetime.utcnow())
    FirstResponseAt= Column(Integer)
    ResolvedAt= Column(Integer)
    Description = Column(String(400), nullable= True)
    Assigned_To = Column(String(250), nullable=True)
    Time_To_Solve= Column(Integer, nullable=True)
    UNIT_Name =Column(String(10), nullable= True)
    Status_Name =Column(String(20), nullable= True)
    Type_Name = Column(String(20), nullable= True)
    Priority_Name =Column(String(20), nullable= True)
    User_ID =Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    OpenedToPending= Column(Integer)
    PendingToSolved= Column(Integer)
    ResolvedAt= Column(Integer)
    
class Printers(Base):
    __tablename__ = 'printers'

    ID = Column(Integer, primary_key=True, autoincrement=True)
    Type = Column(String(250), nullable=False)
    IP= Column(String(250),nullable=True)
    Dept_ID= Column(Integer, ForeignKey('department.id'), nullable= True)
    department = relationship(Department, single_parent=True)
    Description = Column(String(400), nullable= True)
    
#engine = create_engine('mysql:///SA:P@ssw0rd@localhost/Northwind')


#Base.metadata.create_all(engine)
