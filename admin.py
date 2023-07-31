import random
import uuid
from datetime import datetime, timedelta
from sqlite3 import IntegrityError

from flask import Flask, get_flashed_messages, current_app, \
    make_response, jsonify
from flask import flash, render_template, request
from flask import redirect, url_for
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import LoginManager, login_user, current_user
from flask_login import login_required
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import update, insert, func
from sqlalchemy.exc import NoResultFound
from werkzeug.security import check_password_hash

from db import engine, Base, Session, session
from forms import SignupForm, ProfileForm, LoginForm, RegisterForm, LogAdminForm, SearchForm
from models import Movie, Video, Profile, CustomUser, AdminModel, Serie, Season, Episode, favorited_movies, \
    favorited_series, vistas_total, EstadisticasAdminView

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database/tokiobase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'tu_clave_secreta'  # Agrega una clave secreta aquí

db = SQLAlchemy(app)
migrate = Migrate(app, db)
# Inicializar la extensión de administración
admin = Admin(app, name='Netflix App', template_mode='bootstrap3')
csrf = CSRFProtect(app)

# Crear las tablas en la base de datos
Base.metadata.create_all(bind=engine)

db_session = Session()
class SerieAdminView(ModelView):
    column_list = ('title', 'description', 'genre','seasons','image','age_limit','video')
    form_columns = ('title', 'description', 'genre', 'seasons','image','age_limit','video')

class SeasonAdminView(ModelView):
    column_list = ('number', 'serie', 'episodes','image','video')
    form_columns = ('number', 'serie', 'episodes','image','video')

class EpisodeAdminView(ModelView):
    column_list = ('number', 'title', 'season','image','video','duration')
    form_columns = ('number', 'title', 'season','image','video','duration')
# Agregar vistas de administrador para los modelos
def init_admin():
    admin.add_view(ModelView(Movie, db_session))
    admin.add_view(ModelView(Video, db_session))
    admin.add_view(ModelView(Profile, db_session))
    admin.add_view(ModelView(CustomUser, db_session))
    admin.add_view(SerieAdminView(Serie, db_session))
    admin.add_view(SeasonAdminView(Season, db_session))
    admin.add_view(EpisodeAdminView(Episode, db_session))
    admin.add_view(EstadisticasAdminView(name='Estadísticas', endpoint='estadisticas_admin'))

# Crear una instancia de LoginManager
login_manager = LoginManager(app)

# Configurar la vista de login
login_manager.login_view = 'login'  # 'login' es el nombre de la función o ruta para la página de inicio de sesión


# Definir la función load_user para cargar el usuario desde la base de datos
@login_manager.user_loader
def load_user(user_id):
    user = db_session.get(CustomUser, user_id)
    return user


def load_admin(email):
    with current_app.app_context():
        admin = db_session.query(AdminModel).filter_by(email=email).first()
        return admin

# Ruta para mostrar la página de inicio
@app.route('/')
def home():
    # Verificar si se ha establecido la cookie de sesión
    if 'session' in request.cookies and current_user.is_authenticated:
        return redirect('/profiles')  # Redirigir a profile_list si existe la cookie de sesión
    return render_template('home.html')

@app.route('/signup/', methods=['GET', 'POST'])
def signup():
    form = SignupForm()

    if form.validate_on_submit():
        email = form.email.data
        username = form.username.data
        password = form.password.data
        password2 = form.password2.data

        existing_user = db_session.query(CustomUser).filter_by(email=email).first()
        if existing_user:
            flash('El correo electrónico ya está registrado. Por favor, inicia sesión.', 'error')
            return redirect(url_for('login'))

        if password != password2:
            flash('Las contraseñas no coinciden. Por favor, inténtalo de nuevo.', 'error')
            return redirect(url_for('signup'))

        user = CustomUser(email=email, username=username)
        user.set_password(password)

        db_session.add(user)
        db_session.commit()

        flash('Registro exitoso. Por favor, inicia sesión.', 'success')
        return redirect(url_for('login'))

    # Eliminar los mensajes flash existentes solo si el formulario no se ha enviado
    if request.method == 'GET':
        for category, message in get_flashed_messages(with_categories=True):
            pass

    return render_template('signup.html', form=form)


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:  # Si el usuario ya está autenticado, redirigir a la lista de perfiles
        return redirect(url_for('profile_list'))

    form = LoginForm(request.form)

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = db_session.query(CustomUser).filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Inicio de sesión exitoso.', 'success')

            # Obtener el perfil actual del usuario autenticado
            current_profile = db_session.query(Profile).join(Profile.user).filter_by(id=current_user.id).first()

            if current_profile:
                inicio_sesion = current_profile.inicio_sesion
                if inicio_sesion is not None:
                    if not isinstance(inicio_sesion, str):
                        inicio_sesion = str(inicio_sesion)
                    inicio_sesion = datetime.fromisoformat(inicio_sesion)
                else:
                    inicio_sesion = datetime.now()
                current_profile.inicio_sesion = datetime.now()
                duracion_sesion = datetime.now() - inicio_sesion
                if current_profile.tiempo_abierta is not None:
                    current_profile.tiempo_abierta += duracion_sesion.total_seconds()
                else:
                    current_profile.tiempo_abierta = duracion_sesion.total_seconds()
                db_session.commit()

            return redirect(url_for('profile_list'))

    return render_template('login.html', form=form)

@app.route('/login_check', methods=['POST'])
def login_check():
    data = request.get_json()
    email = data['email']
    password = data['password']
    user = db_session.query(CustomUser).filter_by(email=email).first()

    if user and user.check_password(password):
        # La contraseña es correcta
        return jsonify({'success': True}), 200
    else:
        # La contraseña es incorrecta
        return jsonify({'success': False}), 401

db_session.execute(
    update(Profile)
    .where(Profile.age_limit == "0")
    .values(age_limit=False)
)

db_session.execute(
    update(Profile)
    .where(Profile.age_limit == "1")
    .values(age_limit=True)
)

db_session.commit()




@app.route('/profiles/')
@login_required
def profile_list():
    print("estoy en profiles")
    profiles = current_user.profiles
    current_profile = None
    print("antes del if")
    current_profile_id = request.args.get('profile_id')
    if current_profile_id:
        try:
            current_profile = db_session.query(Profile).filter_by(id=current_profile_id).one()
            if current_profile not in current_user.profiles:
                current_profile = None
        except NoResultFound:
            current_profile = None
    else:
        if current_user.profiles:
            current_profile = current_user.profiles[0]

    return render_template('profile_list.html', profiles=profiles, current_profile=current_profile, current_user=current_user)


@app.route('/create/profile', methods=['GET', 'POST'])
@login_required
def profile_create():
    form = ProfileForm()

    if form.validate_on_submit():
        try:
            # Convertir el valor del formulario a un valor booleano adecuado
            if form.age_limit.data == 'All':
                age_limit = True
            else:
                age_limit = False

            new_profile = Profile(name=form.name.data, age_limit=age_limit)
            new_profile.uuid = str(uuid.uuid4())  # Genera un nuevo uuid único
            current_user.profiles.append(new_profile)
            db_session.add(new_profile)
            new_profile.user = current_user
            db_session.commit()
            print("->>>>>",new_profile.age_limit)

            flash('Perfil creado exitosamente.', 'success')
            return redirect(url_for('profile_list'))
        except IntegrityError:
            db_session.rollback()
            flash('El perfil ya existe.', 'error')
            return redirect(url_for('profile_create'))

    return render_template('profile_create.html', form=form)


@app.route('/profile/delete/<int:profile_id>/', methods=['GET', 'POST'])
def profile_delete(profile_id):
    # Obtener el perfil a eliminar
    profile = db_session.query(Profile).get(profile_id)

    if profile:
        # Eliminar el perfil de la base de datos
        db_session.delete(profile)
        db_session.commit()

    # Redirigir a la página de la lista de perfiles
    return redirect(url_for('profile_list'))




def filter_all_by_profile(movies, series, profile):
    if profile.age_limit == False:
        # Filtrar las películas solo para niños
        filtered_movies = [movie for movie in movies if movie.age_limit == False]
        # Filtrar las series solo para niños
        filtered_series = [serie for serie in series if serie.age_limit == False]
    else:
        # Mostrar todas las películas para otros perfiles
        filtered_movies = movies
        # Mostrar todas las series para otros perfiles
        filtered_series = series

    return filtered_movies, filtered_series

def filter_movies_by_profile(movies, profile):
    if profile.age_limit == False:
        # Filtrar las películas solo para niños
        filtered_movies = [movie for movie in movies if movie.age_limit == False]
    else:
        # Mostrar todas las películas para otros perfiles
        filtered_movies = movies

    return filtered_movies

def filter_series_by_profile(series, profile):
    if profile is not None and profile.age_limit == False:
        # Filtrar las series solo para niños
        filtered_series = [serie for serie in series if serie.age_limit == False]
    else:
        # Mostrar todas las series para otros perfiles
        filtered_series = series

    return filtered_series



@app.route('/all_list/<profile_id>/')
def all_list(profile_id):
    # Obtener el perfil actual basado en el ID proporcionado
    current_profile = db_session.query(Profile).get(profile_id)
    age_limit = bool(current_profile.age_limit)
    print(current_profile.name, "age limit ->", age_limit)

    # Obtener la lista de películas y series (reemplaza 'get_movies()' y 'get_series()' con tus propias funciones para obtener las películas y series)
    movies = db_session.query(Movie).all()
    series = db_session.query(Serie).all()

    # Filtrar películas y series según el perfil actual
    filtered_movies, filtered_series = filter_all_by_profile(movies, series, current_profile)

    # Obtener las mejores películas para mostrar en la parte superior (puedes ajustar esta lógica según tus necesidades)
    top_movies = []
    if current_profile is not None:
        for movie in movies:
            if movie.age_limit <= current_profile.age_limit:
                top_movies.append(movie)
    else:
        top_movies = movies

    top_movies = top_movies[0:1]
    background_image = top_movies[0].image if top_movies else url_for('static', filename='assets/netflix_kid.png')

    search_form = SearchForm()
    movies = []
    series = []

    if search_form.validate_on_submit():
        search_query = search_form.search_query.data
        # Realiza la búsqueda en la base de datos o cualquier otra lógica de búsqueda
        movies = db_session.query(Movie).filter(Movie.title.ilike(f'%{search_query}%')).all()
        series = db_session.query(Serie).filter(Serie.title.ilike(f'%{search_query}%')).all()



    return render_template('all_list.html', profile_id=profile_id, current_profile=current_profile,
                           movies=filtered_movies,
                           series=filtered_series, top_movies=top_movies, background_image=background_image, item=None, search_form=search_form)


@app.route('/search/<profile_id>', methods=['GET', 'POST'])
def search(profile_id):
    current_profile = db_session.query(Profile).get(profile_id)

    search_form = SearchForm()
    movies = []
    series = []

    if search_form.validate_on_submit():
        search_query = search_form.search_query.data
        # Realiza la búsqueda en la base de datos o cualquier otra lógica de búsqueda
        movies = db_session.query(Movie).filter(Movie.title.ilike(f'%{search_query}%')).all()
        series = db_session.query(Serie).filter(Serie.title.ilike(f'%{search_query}%')).all()

    return render_template('all_list.html', movies=movies, series=series, search_form=search_form,current_profile=current_profile)


@app.route('/watch/<profile_id>/')
def watch_series(profile_id):
    # Obtener el perfil actual basado en el ID proporcionado
    current_profile = db_session.query(Profile).get(profile_id)
    age_limit = None
    if current_profile is not None:
        age_limit = bool(current_profile.age_limit)


    # Obtener la lista de series (reemplaza 'get_series()' con tu propia función para obtener las series)
    series = db_session.query(Serie).all()
    # Filtrar las series según el perfil actual
    filtered_series = filter_series_by_profile(series, current_profile)
    for i in filtered_series:
        print(i, i.age_limit)

    top_series = []

    if current_profile is not None:
        for serie in series:
            if serie.age_limit <= current_profile.age_limit:
                top_series.append(serie)
    else:
        top_series = series
        top_series = top_series[0:1]

    top_series = top_series[0:1]
    background_image = top_series[0].image if top_series else url_for('static', filename='assets/netflix_kid.png')
    return render_template('serie_list.html', profile_id=profile_id, current_profile=current_profile, serie=filtered_series,
                           top_series=top_series, background_image=background_image)



@app.route('/watch_movies/<profile_id>/')
def watch_movies(profile_id):
    # Obtener el perfil actual basado en el ID proporcionado
    current_profile = db_session.query(Profile).get(profile_id)
    age_limit = bool(current_profile.age_limit)
    print(current_profile.name, "age limit ->", age_limit)

    # Obtener la lista de películas (reemplaza 'get_movies()' con tu propia función para obtener las películas)
    movies = db_session.query(Movie).all()
    # Filtrar las películas según el perfil actual
    filtered_movies = filter_movies_by_profile(movies, current_profile)

    top_movies = []

    if current_profile is not None:
        for movie in movies:
            if movie.age_limit <= current_profile.age_limit:
                top_movies.append(movie)
    else:
        top_movies = movies
        top_movies = top_movies[0:1]

    top_movies = top_movies[0:1]
    background_image = top_movies[0].image if top_movies else url_for('static', filename='assets/netflix_kid.png')
    return render_template('movie_list.html', profile_id=profile_id, current_profile=current_profile, movies=filtered_movies,
                           top_movies=top_movies, background_image=background_image)




@app.route('/watch/detail/<int:movie_id>/')
def movie_detail(movie_id):
    # Obtener la película actual basada en el ID proporcionado
    movie = db_session.query(Movie).get(movie_id)
    # Obtener el perfil asociado a la película
    current_profile = db_session.query(Profile).join(Profile.custom_user).filter(Profile.favorite_movies.contains(movie)).first()

    return render_template('movie_detail.html', movie=movie, current_profile=current_profile)

@app.route('/watch/details/<serie_id>/')
def serie_detail(serie_id):
    # Obtener la serie actual basada en el ID proporcionado
    serie = db_session.query(Serie).filter(Serie.id == serie_id).first()
    # Obtener el perfil asociado a la serie
    current_profile = db_session.query(Profile).join(Profile.custom_user).filter(Profile.favorite_series.contains(serie)).first()
    return render_template('serie_detail.html', serie=serie, current_profile=current_profile)

@app.route('/season/<season_id>/episodes')
def get_season_episodes(season_id):
    season = db_session.query(Season).filter(Season.id == season_id).first()
    if season:
        episodes = season.episodes
        return jsonify([{
            'id': episode.id,
            'title': episode.title,
            'number': episode.number,
            'image': episode.image,
            'video': episode.video
        } for episode in episodes])
    else:
        return jsonify([])

@app.route('/watch/play/<movie_id>/')
def play_movie(movie_id):
    # Obtener la película basada en el ID proporcionado
    movie = db_session.query(Movie).filter(Movie.id == movie_id).first()

    return render_template('play_movie.html', movie=movie)

@app.route('/play/<serie_id>/')
def play_serie(serie_id):
    # Obtener la serie basada en el ID proporcionado
    serie = db_session.query(Serie).filter(Serie.id == serie_id).first()

    # Obtener la URL del video de la consulta de parámetros en la URL
    video_url = request.args.get('video')

    return render_template('play_serie.html', serie=serie, video_url=video_url)

@app.route('/play/<episode_id>/')
def play_episode(episode_id):
    episode = db_session.query(Episode).filter(Episode.id == episode_id).first()
    video_url = episode.video
    return render_template('play_serie.html', video_url=video_url)



@app.route('/logout')
def logout():
    print("Estoy en logout")
    # Obtener el perfil actual del usuario autenticado
    current_user_id = current_user.id
    current_profile = db_session.query(Profile).join(Profile.user).filter_by(id=current_user.id).first()

    if current_profile:
        cierro_sesion = current_profile.cierro_sesion
        if cierro_sesion is not None:
            if not isinstance(cierro_sesion, str):
                cierro_sesion = str(cierro_sesion)
            cierro_sesion = datetime.fromisoformat(cierro_sesion)
        current_profile.cierro_sesion = datetime.now()

        # Obtener el valor de inicio_sesion de la base de datos
        inicio_sesion = db_session.query(func.coalesce(Profile.inicio_sesion, datetime.now())).filter_by(id=current_user_id).first()[0]
        if isinstance(inicio_sesion, str):
            inicio_sesion = datetime.fromisoformat(inicio_sesion)

        duracion_sesion = datetime.now() - (inicio_sesion or datetime.now())
        if current_profile.tiempo_abierta is not None:
            current_profile.tiempo_abierta += duracion_sesion.total_seconds()
        else:
            current_profile.tiempo_abierta = duracion_sesion.total_seconds()
        db_session.commit()



    # Eliminar la cookie de sesión
    response = make_response(redirect('/'))
    response.set_cookie('session', '', expires=0)
    return response



@app.route('/addMovFav/<profile_id>/<movie_id>')
def addMovFav(profile_id, movie_id):
    print("addfav")
    # Obtener el perfil actual basado en el ID proporcionado
    current_profile = db_session.query(Profile).get(profile_id)

    # Insertar un nuevo registro en la tabla favorited_movies
    stmt = insert(favorited_movies).values(profile_id=current_profile.id, movie_id=movie_id)
    db_session.execute(stmt)
    db_session.commit()

    return jsonify(), 204  # Devolver respuesta vacía con código de estado 204 (No Content)




@app.route('/addfavoritas/<profile_id>/<serie_id>')
def addSerFav(profile_id,serie_id):
    print("addserfav")
   # Verificar si el item es una película o una serie
    current_profile = db_session.query(Profile).get(profile_id)

    stmt = insert(favorited_series).values(profile_id=current_profile.id, serie_id=serie_id)
    db_session.execute(stmt)
    db_session.commit()

    return jsonify(), 204  # Devolver respuesta vacía con código de estado 204 (No Content)




@app.route('/addMovvistas/<profile_id>/<movie_id>')
def addMovVistas(profile_id,movie_id):
    print("add mov vistas")
    # Verificar si el item es una película o una serie
    current_profile = db_session.query(Profile).get(profile_id)

    stmt = insert(vistas_total).values(profile_id=current_profile.id, movie_id=movie_id)
    db_session.execute(stmt)
    db_session.commit()
    return jsonify(), 204  # Devolver respuesta vacía con código de estado 204 (No Content)

@app.route('/addServistas/<profile_id>/<serie_id>')
def addSerVistas(profile_id,serie_id):
    print("add ser vistas")
    current_profile = db_session.query(Profile).get(profile_id)

    stmt = insert(vistas_total).values(profile_id=current_profile.id, serie_id=serie_id)
    db_session.execute(stmt)
    db_session.commit()
    return jsonify(), 204  # Devolver respuesta vacía con código de estado 204 (No Content)

@app.route('/ver_favoritas/<profile_id>/<serie_id>/<movie_id>')
def ver_favoritas(profile_id, serie_id, movie_id):
    current_profile = db_session.query(Profile).get(profile_id)

    favorite_movies_query = db_session.query(Movie).join(favorited_movies).filter(
        favorited_movies.c.profile_id == current_profile.id)

    favorite_series_query = db_session.query(Serie).join(favorited_series, Serie.id == favorited_series.c.serie_id).filter(
        favorited_series.c.profile_id == current_profile.id)

    favorite_movies = favorite_movies_query.all()
    favorite_series = favorite_series_query.all()

    # Filtra las películas y series favoritas según el age_limit del perfil
    filtered_movies = [movie for movie in favorite_movies if movie.age_limit is None or movie.age_limit <= current_profile.age_limit]
    filtered_series = [serie for serie in favorite_series if serie.age_limit is None or serie.age_limit <= current_profile.age_limit]

    favoritas = filtered_movies + filtered_series
    serie = db_session.query(Serie).get(serie_id)
    movie = db_session.query(Movie).get(movie_id)

    return render_template('favoritas.html', current_profile=current_profile,
                           favoritas=favoritas,
                           peliculas_favoritas=filtered_movies,
                           series_favoritas=filtered_series, serie_id=serie, movie_id=movie)



@app.route('/ver_vistas/<profile_id>/<serie_id>/<movie_id>')
def ver_vistas(profile_id, serie_id, movie_id):
    # Obtén el perfil actual basado en el profile_id proporcionado
    print("obtener vistas")
    current_profile = db_session.query(Profile).get(profile_id)

    # Obtiene las películas vistas del perfil actual
    vistas_movies = db_session.query(Movie).join(vistas_total).filter(
        vistas_total.c.profile_id == current_profile.id).all()
    print("fav movies ->", vistas_movies)

    # Obtiene las series vistas del perfil actual
    vistas_series = db_session.query(Serie).join(vistas_total, Serie.id == vistas_total.c.serie_id).filter(
        vistas_total.c.profile_id == current_profile.id).all()

    print("fav series ->",vistas_series)

    vistas = vistas_movies + vistas_series
    print("vistas ->", vistas)

    serie = db_session.query(Serie).get(serie_id)
    movie = db_session.query(Movie).get(movie_id)

    return render_template('vistas.html', current_profile=current_profile,
                           peliculas_vistas=vistas_movies,series_vistas=vistas_series, serie_id=serie, movie_id=movie)

#==========================GRAFICAS=====================


@app.route('/estadisticas/<profile_id>')
def estadisticas(profile_id):
    # Obtén los datos de visualización del usuario actual (ejemplo usando un modelo User)
    current_profile = db_session.query(Profile).get(profile_id)

    # Verifica si tiempo_abierta tiene un valor válido
    if current_profile.tiempo_abierta is None:
        tiempo_abierta_str = "00:00:00"
    else:
        tiempo_abierta = current_profile.tiempo_abierta

        # Convierte el tiempo a un formato adecuado
        tiempo_abierta_str = str(timedelta(seconds=tiempo_abierta))

    # Genera los datos para las gráficas
    datos_24h = random.randint(0, 24)
    datos_semana = [random.randint(0, 24) for _ in range(7)]
    datos_mes = [random.randint(0, 24) for _ in range(30)]

    # Pasa los datos a la plantilla
    return render_template('estadisticas.html', tiempo_abierta=tiempo_abierta_str, datos_24h=datos_24h, datos_semana=datos_semana, datos_mes=datos_mes)







#=========================ADMIN========================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        username = form.username.data
        password = form.password.data
        password2 = form.password2.data

        existing_admin = db_session.query(AdminModel).filter_by(email=email).first()

        if existing_admin:
            flash('Ya existe un administrador con ese correo electrónico. Inicie sesión', 'error')
            return redirect(url_for('admin_login'))
        if password != password2:
            flash('Las contraseñas no coinciden. Por favor, inténtalo de nuevo.', 'error')
            return redirect(url_for('register'))
        else:
            admin1 = AdminModel(email=email,username=username)
            admin1.set_password(password)
            db_session.add(admin1)
            db_session.commit()
            flash('Registro exitoso. Ahora puedes iniciar sesión como administrador.', 'success')
            return redirect(url_for('admin_login'))

    flash('Regístrese como usuario.', 'info')
    return render_template('admin/register.html', form=form)




@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    form = LogAdminForm()
    print("adminlogin")
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        print("primer if")
        # Verificar las credenciales del administrador
        admin = db_session.query(AdminModel).filter_by(email=email).first()

        if admin:
            print("segundo if")
            if check_password_hash(admin.password, password):
                print("tercer if")
                # Iniciar sesión de administrador utilizando Flask-Login
                login_user(admin)
                flash('Inicio de sesión exitoso como administrador.', 'success')

                # Redirigir al usuario al dashboard de administrador
                print("pal return")
                return redirect(url_for('admin.index'))

            else:
                print("primer else")
                flash('Contraseña incorrecta para el administrador.', 'error')
                return render_template('admin/logadmin.html', form=form)
        else:
            print("segundo else")
            flash('Correo electrónico no registrado como administrador.', 'error')

    return render_template('admin/logadmin.html', form=form)





if __name__ == '__main__':
    init_admin()
    app.run(debug=True)
