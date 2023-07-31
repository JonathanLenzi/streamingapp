import uuid
from datetime import datetime, timedelta

from flask_admin import BaseView, expose
from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table, Boolean, Interval, func
from sqlalchemy.orm import relationship, validates, backref
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.ext.declarative import declarative_base

import db

Base = declarative_base()


user_profile = Table('user_profile', Base.metadata,
                     Column('user_id', Integer, ForeignKey('custom_users.id'), primary_key=True),
                     Column('profile_id', Integer, ForeignKey('profiles.id'), primary_key=True)
                     )
favorites = Table(
    'favorites',
    Base.metadata,
    Column('profile_id', Integer, ForeignKey('profiles.id')),
    Column('movie_id', Integer, ForeignKey('movies.id')),
    Column('serie_id', Integer, ForeignKey('series.id')),
    extend_existing=True
)

vistas_total = Table(
    'vistas_total',
    Base.metadata,
    Column('profile_id', Integer, ForeignKey('profiles.id')),
    Column('movie_id', Integer, ForeignKey('movies.id')),
    Column('serie_id', Integer, ForeignKey('series.id')),
    extend_existing=True
)

favorited_movies = Table(
    'favorited_movies',
    Base.metadata,
    Column('profile_id', Integer, ForeignKey('profiles.id')),
    Column('movie_id', Integer, ForeignKey('movies.id'))
)
favorited_series = Table(
    'favorited_series',
    Base.metadata,
    Column('profile_id', Integer, ForeignKey('profiles.id')),
    Column('serie_id', Integer, ForeignKey('serie.id'))
)

class CustomUser(UserMixin, Base):
    __tablename__ = 'custom_users'

    id = Column(Integer, primary_key=True)
    email = Column(String(120), unique=True, nullable=False)
    username = Column(String(80), unique=True, nullable=False)
    password = Column(String(80), nullable=False)
    profile = relationship('Profile', backref='user')
    profiles_custom = relationship('Profile', secondary=user_profile, backref='custom_users', overlaps="profile,user",
                                   viewonly=True)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class AdminModel(Base, UserMixin):
    __tablename__ = 'admins'

    id = Column(Integer, primary_key=True)
    email = Column(String(120), unique=True, nullable=False)
    username = Column(String(80), unique=True, nullable=False)
    password = Column(String(80), nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def get_email(self):
        return self.email


class EstadisticasAdminView(BaseView):
    @expose('/')
    def index(self):
        # Obtén los perfiles y los tiempos abiertos de la base de datos
        perfiles = db.session.query(Profile).all()
        tiempos_abiertos = db.session.query(func.coalesce(Profile.tiempo_abierta, 0)).all()

        # Preparar los datos para las gráficas
        labels_24h = []
        values_24h = []
        labels_semana = []
        values_semana = []
        labels_mes = []
        values_mes = []

        today = datetime.now()
        one_day_ago = today - timedelta(days=1)
        one_week_ago = today - timedelta(weeks=1)
        one_month_ago = today - timedelta(days=30)

        for perfil, tiempo_abierto in zip(perfiles, tiempos_abiertos):
            labels_24h.append(perfil.name)
            values_24h.append(tiempo_abierto[0])

            # Obtener los tiempos abiertos en las últimas 24 horas
            tiempo_abierta_24h = db.session.query(func.coalesce(Profile.tiempo_abierta, 0)).filter(Profile.id == perfil.id, Profile.inicio_sesion >= one_day_ago).scalar()
            values_24h.append(tiempo_abierta_24h)

            # Obtener los tiempos abiertos en la última semana
            tiempo_abierta_semana = db.session.query(func.coalesce(Profile.tiempo_abierta, 0)).filter(Profile.id == perfil.id, Profile.inicio_sesion >= one_week_ago).scalar()
            values_semana.append(tiempo_abierta_semana)
            labels_semana.append(perfil.name)

            # Obtener los tiempos abiertos en el último mes
            tiempo_abierta_mes = db.session.query(func.coalesce(Profile.tiempo_abierta, 0)).filter(Profile.id == perfil.id, Profile.inicio_sesion >= one_month_ago).scalar()
            values_mes.append(tiempo_abierta_mes)
            labels_mes.append(perfil.name)

        # Renderizar la vista de administrador con las gráficas
        return self.render('admin/estadisticas_admin.html', labels_24h=labels_24h, values_24h=values_24h,
                           labels_semana=labels_semana, values_semana=values_semana,
                           labels_mes=labels_mes, values_mes=values_mes)



class Profile(Base):
    __tablename__ = 'profiles'

    id = Column(Integer, primary_key=True)
    name = Column(String(1000))
    age_limit = Column(Boolean)  # True: Todas las edades, False: Para niños
    uuid = Column(String(36), unique=True, nullable=False, default=uuid.uuid4)
    tiempo_abierta = Column(Integer)
    inicio_sesion = Column(Integer)
    cierro_sesion = Column(Integer)
    custom_user_id = Column(Integer, ForeignKey('custom_users.id'))
    custom_user = relationship('CustomUser', backref='profiles', overlaps="profile,user", viewonly=True)
    favorite_movies = relationship(
        "Movie",
        secondary=favorites,
        back_populates="favorites_profiles",
        overlaps="favorite_series"
    )
    favorite_series = relationship(
        "Serie",
        secondary=favorites,
        back_populates="favorites_profiles",
        overlaps="favorite_movies")

    def __str__(self):
        return self.name



class Movie(Base):
    __tablename__ = 'movies'

    id = Column(Integer, primary_key=True)
    title = Column(String(1000))
    description = Column(Text)
    created = Column(DateTime, default=datetime.utcnow)
    uuid = Column(String(36), default=str(uuid.uuid4()), unique=True)

    type = Column(String(10))
    image = Column(String(255))
    age_limit = Column(Integer)
    genre = Column(String(100))
    video = Column(String(100))
    duration = Column(Integer)

    favorites_profiles = relationship("Profile", secondary=favorites, back_populates="favorite_movies",
         overlaps="favorite_series")

    @validates('age_limit')
    def validate_age_limit(self, key, age_limit):
        if age_limit == 1:
            return True
        elif age_limit == 0:
            return False
        else:
            raise ValueError("Invalid age_limit value: {}. Allowed values are 1 or 0.".format(age_limit))




    def __str__(self):
        return self.title


class Video(Base):
    __tablename__ = 'videos'

    id = Column(Integer, primary_key=True)
    title = Column(String(1000))
    file = Column(String(255))

    def __str__(self):
        return self.title

class Serie(Base):
    __tablename__ = 'series'

    id = Column(Integer, primary_key=True)
    title = Column(String(1000))
    description = Column(Text)
    created = Column(DateTime, default=datetime.utcnow)
    uuid = Column(String(36), default=str(uuid.uuid4()), unique=True)

    type = Column(String(10))
    image = Column(String(255))
    age_limit = Column(Integer)
    genre = Column(String(100))
    video = Column(String(100))

    seasons = relationship('Season', backref='serie', cascade='all, delete-orphan', overlaps="favorite_movies,favorites_profiles")

    favorites_profiles = relationship(
        "Profile",
        secondary=favorites,
        back_populates="favorite_series",
        overlaps="favorite_movies, favorites_profiles")

    @validates('age_limit')
    def validate_age_limit(self, key, age_limit):
        if age_limit == 1:
            return True
        elif age_limit == 0:
            return False
        else:
            raise ValueError("Invalid age_limit value: {}. Allowed values are 1 or 0.".format(age_limit))

    def __str__(self):
        return self.title


class Season(Base):
    __tablename__ = 'seasons'

    id = Column(Integer, primary_key=True)
    number = Column(Integer)
    serie_id = Column(Integer, ForeignKey('series.id'))
    image = Column(String(255))
    video = Column(String(100))

    episodes = relationship('Episode', backref='season', cascade='all, delete-orphan')

    def __str__(self):
        return f"Season {self.number}"


class Episode(Base):
    __tablename__ = 'episodes'

    id = Column(Integer, primary_key=True)
    title = Column(String(1000))
    number = Column(Integer)
    season_id = Column(Integer, ForeignKey('seasons.id'))
    image = Column(String(255))
    video = Column(String(100))
    duration= Column(Integer)

    def __str__(self):
        return f"Episode {self.number}: {self.title}"

