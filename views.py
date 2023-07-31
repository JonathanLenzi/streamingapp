from flask import request, flash, Blueprint
from flask.views import MethodView
from flask_login import login_required, current_user, login_user
from werkzeug.security import generate_password_hash

from admin import app, db
from forms import ProfileForm, LoginForm
from models import Profile, Movie

signup_blueprint = Blueprint('signup', __name__)
estadisticas_admin_blueprint = Blueprint('estadisticas_admin', __name__)

class Home(MethodView):
    def get(self):
        if current_user.is_authenticated:
            return redirect(url_for('signup.profile_list'))
        return render_template('home.html')

from flask import render_template, redirect, url_for
from flask.views import MethodView
from forms import SignupForm
from models import CustomUser

class Signup(MethodView):
    def get(self):
        form = SignupForm()
        return render_template('signup.html', form=form)

    def post(self):
        form = SignupForm()

        if form.validate_on_submit():
            email = form.email.data
            username = form.username.data
            password = form.password.data
            password2 = form.password2.data

            # Verificar si el correo electrónico ya está registrado
            existing_user = db.session.query(CustomUser).filter_by(email=email).first()
            if existing_user:
                flash('El correo electrónico ya está registrado. Por favor, inicia sesión.', 'error')
                return redirect(url_for('login'))

            # Verificar si las contraseñas coinciden
            if password != password2:
                flash('Las contraseñas no coinciden. Por favor, inténtalo de nuevo.', 'error')
                return redirect(url_for('signup'))

            # Crear el nuevo usuario
            user = CustomUser(email=email, username=username, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()

            flash('Registro exitoso. Por favor, inicia sesión.', 'success')
            return redirect(url_for('login'))

        return render_template('signup.html', form=form)




class Login(MethodView):
    def get(self):
        return render_template('login.html')

    def post(self):
        form = LoginForm(request.form)

        if form.validate_on_submit():
            email = form.email.data
            password = form.password.data

            user = db.session.query(CustomUser).filter_by(email=email).first()

            if user:
                if user.check_password(password):
                    login_user(user)
                    flash('Inicio de sesión exitoso.', 'success')
                    return redirect(url_for('profiles'))
                else:
                    flash('Correo electrónico o contraseña incorrectos.', 'error')
            else:
                flash('Correo electrónico no registrado.', 'error')

        return render_template('login.html', form=form)








class ProfileList(MethodView):
    decorators = [login_required]

    def get(self):
        profiles = Profile.query.all()
        current_profile = None

        if current_user.is_authenticated:
            current_profile_id = request.args.get('profile_id')
            if current_profile_id:
                current_profile = Profile.query.get(current_profile_id)
                if current_profile not in current_user.profiles:
                    current_profile = None
            else:
                current_profile = current_user.profiles.first()

        return render_template('profile_list.html', profiles=profiles, current_profile=current_profile, current_user=current_user)




class ProfileCreate(MethodView):
    def get(self):
        form = ProfileForm()
        return render_template('profile_create.html', form=form)

    def post(self):
        form = ProfileForm()

        if form.validate_on_submit():
            # Obtener el usuario actualmente autenticado
            user = current_user

            # Crear el perfil asociado al usuario
            new_profile = Profile(name=form.name.data, age_limit=form.age_limit.data)
            user.profiles.append(new_profile)
            db.session.add(new_profile)
            db.session.commit()

            flash('Perfil creado exitosamente.', 'success')
            return redirect(url_for('profiles'))

        return render_template('profile_create.html', form=form)





class MovieList(MethodView):
    decorators = [login_required]

    def get(self, profile_id):
        profile = Profile.query.filter_by(uuid=profile_id).first()
        if not profile or profile not in current_user.profiles:
            flash('Invalid profile.', 'danger')
            return redirect(url_for('signup.profile_list'))
        movies = Movie.query.all()
        return render_template('movie_list.html', profile=profile, movies=movies)


class MovieDetail(MethodView):
    decorators = [login_required]

    def get(self, movie_id):
        movie = Movie.query.filter_by(uuid=movie_id).first()
        if not movie:
            flash('Invalid movie.', 'danger')
            return redirect(url_for('signup.profile_list'))
        return render_template('movie_detail.html', movie=movie)


class PlayMovie(MethodView):
    decorators = [login_required]

    def get(self, movie_id):
        return redirect(url_for('signup.movie_detail', movie_id=movie_id))


signup_blueprint.add_url_rule('/', view_func=Home.as_view('home'))
signup_blueprint.add_url_rule('/signup/', view_func=Signup.as_view('signup'))
signup_blueprint.add_url_rule('/login/', view_func=Login.as_view('login'))
signup_blueprint.add_url_rule('/profiles/', view_func=ProfileList.as_view('profile_list'))
signup_blueprint.add_url_rule('/profiles/create/', view_func=ProfileCreate.as_view('create_profile'))
signup_blueprint.add_url_rule('/watch/<profile_id>/', view_func=MovieList.as_view('movie_list'))
signup_blueprint.add_url_rule('/watch/detail/<movie_id>/', view_func=MovieDetail.as_view('movie_detail'))
signup_blueprint.add_url_rule('/watch/play/<movie_id>/', view_func=PlayMovie.as_view('play_movie'))

app.register_blueprint(estadisticas_admin_blueprint)
app.register_blueprint(signup_blueprint)



