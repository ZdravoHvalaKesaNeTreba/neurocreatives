from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Boolean, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    channel = Column(String(255), nullable=False)
    telegram_post_id = Column(Integer, nullable=False)
    text = Column(Text)
    date = Column(DateTime, nullable=False)
    views = Column(Integer, default=0)
    forwards = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    reactions = Column(Integer, default=0)
    engagement = Column(Integer, default=0)
    er = Column(Float, default=0.0)
    image_path = Column(String(500))
    post_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    images = relationship("Image", back_populates="post", cascade="all, delete-orphan")


class Image(Base):
    __tablename__ = 'images'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=False)
    file_path = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    post = relationship("Post", back_populates="images")
    analysis = relationship("Analysis", back_populates="image", uselist=False, cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = 'analysis'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey('images.id'), nullable=False)
    scene = Column(String(500))
    objects = Column(Text)
    emotion = Column(String(255))
    creative_type = Column(String(255))
    text_present = Column(String(50))
    visual_strength_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    image = relationship("Image", back_populates="analysis")


class Settings(Base):
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScheduleLog(Base):
    __tablename__ = 'schedule_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    run_type = Column(String(20), default='auto', nullable=False)  # auto/manual
    status = Column(String(50), nullable=False)  # success/error
    images_parsed = Column(Integer, default=0)
    images_analyzed = Column(Integer, default=0)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
