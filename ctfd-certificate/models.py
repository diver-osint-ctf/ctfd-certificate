from CTFd.models import db
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime


class CertificateSettings(db.Model):
    __tablename__ = 'certificate_settings'
    
    id = Column(Integer, primary_key=True)
    ctf_title = Column(String(255), default='CTF Certificate', nullable=False)
    template_type = Column(String(50), default='default', nullable=False)
    background_color = Column(String(7), default='#ffffff', nullable=False)
    text_color = Column(String(7), default='#000000', nullable=False)
    logo_path = Column(String(255), nullable=True)
    footer_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CertificateHistory(db.Model):
    __tablename__ = 'certificate_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=True)
    user_name = Column(String(255), nullable=False)
    team_name = Column(String(255), nullable=True)
    score = Column(Integer, nullable=False)
    rank = Column(Integer, nullable=False)
    ctf_title = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship('Users', backref='certificates')
    team = relationship('Teams', backref='certificates')