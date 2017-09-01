#!/usr/bin/env python2.7
"""         Flask catalog app
 This is a web app showing different movie genres and items
 Users can log in and then add, remove and update movies
"""
import sqlite3
from oauth2client import client, crypt
from flask_login import (LoginManager, UserMixin, login_required,
                         current_user, login_user, logout_user)
from flask_wtf import Form
from wtforms import StringField, SelectField, HiddenField
from wtforms.validators import DataRequired
from flask import (Flask, render_template, request, redirect, url_for,
                   g, jsonify)


APP = Flask(__name__)
APP.secret_key = 'ahagjgdsjgef354#gjagj'
LOGIN_MANAGER = LoginManager()
LOGIN_MANAGER.init_app(APP)
LOGIN_MANAGER.login_view = "landing_page"


@LOGIN_MANAGER.unauthorized_handler
def unauthorized():
    """ Redirects unauthorized users """
    return redirect(url_for('landing_page'))


class AddMovieForm(Form):
    """ Form used to let users add movies """
    title = StringField(
        'Movie Title',
        validators=[DataRequired()]
    )

    poster = StringField(
        'Movie Poster',
        validators=[DataRequired()]
    )

    description = StringField(
        'Description',
        validators=[DataRequired()]
    )

    category = SelectField(
        'Category',
        choices=[('1', 'Action'), ('2', 'Comedy'), ('3', 'Western'),
                 ('4', 'Sport'), ('5', 'Fantasy'), ('6', 'Adventure'),
                 ('7', 'Drama')]
    )


class UpdateMovieForm(AddMovieForm, Form):
    """ Class used to create a form to update movie entries """
    movieid = HiddenField()


class DeleteMovieForm(Form):
    """ This class helps create a form to delete movies """
    movieid = HiddenField()


class User(UserMixin):
    """ Class used by flask-login to track userstate """
    def __init__(self, userid, name):
        self.id = userid
        self.name = name


@LOGIN_MANAGER.user_loader
def load_user(userid):
    """ Function used to load users by Flask-Login"""
    get_user = db_get('SELECT id, name FROM users WHERE id = ? ', [userid])
    user = User(get_user[0][0], get_user[0][1])

    return user

GET_CATEGORIES = ('SELECT category' +
                  ' FROM categories')


def db_get(query, args=()):
    """ This function gets data from the DB """
    conn = sqlite3.connect('catalogApp.sqlite')
    cur = conn.cursor()
    cur.execute(query, args)
    received_data = cur.fetchall()
    conn.close()
    return received_data


def db_insert(query, args=()):
    """ This function creates a row in the database """
    conn = sqlite3.connect('catalogApp.sqlite')
    cur = conn.cursor()
    cur.executemany(query, args)
    conn.commit()
    conn.close()


@APP.route('/')
def landing_page():
    """ This function returns the landing page """
    return render_template('landing_page.html',
                           categories=db_get(GET_CATEGORIES),
                           recent_movies=db_get('SELECT movie, poster,' +
                                                ' movieid FROM movies ' +
                                                'ORDER BY rowid DESC LIMIT 10'
                                                )
                           )


@APP.route('/category/<category>')
def category_page(category):
    """ This function returns the specific category page """
    return render_template('category_page.html',
                           categories=db_get(GET_CATEGORIES),
                           category=category,
                           movies=db_get('SELECT movie, poster, movieid FROM' +
                                         ' movies JOIN categories ' +
                                         'WHERE categories.category = ?' +
                                         ' AND categories.categoryid = ' +
                                         'movies.categoryid',
                                         [category]
                                         )
                           )


@APP.route('/category/movie/<movie_data>/<movie_title>')
def movie_page(movie_title, movie_data):
    """ This function returns the specific movie page """
    return render_template('movie_page.html',
                           categories=db_get(GET_CATEGORIES),
                           movie_title=movie_title,
                           movie_data=db_get('SELECT * FROM movies ' +
                                             'WHERE movieid = ?', [movie_data]
                                             )
                           )


@APP.route('/signin', methods=['POST'])
def signin():
    """ This function handles the signin process """
    if request.method == 'POST':
        token = request.form['id_token']

        try:
            idinfo = client.verify_id_token(token,
                                            '1072405718300-7kdr08dkvn4hkg' +
                                            'ceimh4c7p679rbsmol.apps.goog' +
                                            'leusercontent.com')

            if idinfo['iss'] not in ['accounts.google.com',
                                     'https://accounts.google.com']:
                raise crypt.AppIdentityError("Wrong issuer.")

        except crypt.AppIdentityError:
            return 'Error AppIdentityError'

        userid = idinfo['sub']
        username = idinfo['name']
        user_exists = db_get('SELECT id, name FROM users WHERE' +
                             ' id = ? ', [userid])

        if not user_exists:
            db_insert('INSERT INTO users VALUES (?, ?)', [(username, userid)])
            user_exists = db_get('SELECT id, name FROM users WHERE' +
                             ' id = ? ', [userid])

        user = User(user_exists[0][0], user_exists[0][1])
        login_user(user)

    return redirect(url_for('landing_page'))


@APP.route("/signout")
@login_required
def signout():
    """ Logs the user out """
    logout_user()
    return redirect(url_for('landing_page'))


@APP.route("/userpage")
@login_required
def user_page():
    """ The users own page showing their personal items """
    user_items = db_get('SELECT movie, movieid FROM movies WHERE ' +
                        'user = ?', [g.user.id])
    return render_template('user_page.html',
                           categories=db_get(GET_CATEGORIES),
                           user_items=user_items)


@APP.route('/add', methods=('GET', 'POST'))
@login_required
def add():
    """ Formpage where users can fill a form to add movies """
    form = AddMovieForm()
    if form.validate_on_submit():
        db_insert('INSERT INTO movies (movie, poster, description,' +
                  ' categoryid, user) VALUES (?, ?, ?, ?, ?)',
                  [(form.title.data, form.poster.data, form.description.data,
                   form.category.data, g.user.id)])
        return redirect(url_for('user_page'))
    return render_template('add_item.html',
                           form=form,
                           categories=db_get(GET_CATEGORIES))


@APP.route('/update/<movieid>', methods=('GET', 'POST'))
@login_required
def update(movieid):
    """ Formpage where users can fill a form to update movies """
    form = UpdateMovieForm()
    if form.validate_on_submit():
        user_auth = db_get('SELECT user FROM movies WHERE user = ?' +
                           ' AND movieid = ?',
                           (g.user.id, form.movieid.data))
        if user_auth[0][0] == g.user.id:
            db_insert('UPDATE movies SET movie = ?, poster = ?, description' +
                      ' = ?, categoryid = ? WHERE  movieid = ? AND user = ?',
                      [(form.title.data, form.poster.data,
                       form.description.data,
                       form.category.data, form.movieid.data, g.user.id)])

        return redirect(url_for('user_page'))

    return render_template('update_item.html',
                           form=form,
                           movieid=movieid,
                           categories=db_get(GET_CATEGORIES))


@APP.route('/delete/<movieid>', methods=('GET', 'POST'))
@login_required
def delete(movieid):
    """ Formpage where users can fill a form to remove movies """
    form = DeleteMovieForm()
    if form.validate_on_submit():
        user_auth = db_get('SELECT user FROM movies WHERE user = ?' +
                           ' AND movieid = ?',
                           (g.user.id, form.movieid.data))
        if user_auth[0][0] == g.user.id:
            db_insert('DELETE FROM movies WHERE movieid = ? AND user = ?',
                      [(form.movieid.data, g.user.id)])
        return redirect(url_for('user_page'))
    return render_template('delete_item.html',
                           form=form,
                           movieid=movieid,
                           categories=db_get(GET_CATEGORIES))


@APP.route('/api')
def api_page():
    """ This page contains the documentation for the api """
    return render_template('api_documentation.html')


@APP.route('/api/movies')
def api_movies():
    """ API call that returns a presentation of the movies for the API """
    movies = db_get('SELECT movie, description, poster FROM movies')
    return jsonify(movies)


@APP.route('/api/<category>')
def api_category(category):
    """ API call that returns movies by a selected category """
    categoryid = {'action': 1, 'comedy': 2, 'western': 3, 'sport': 4,
                  'fantasy': 5, 'adventure': 6, 'drama': 7}
    for key, value in categoryid.items():
        if key == category:
            movies = db_get('SELECT movie, description, poster FROM ' +
                            'movies WHERE categoryid = ?', [value])
            return jsonify(movies)


@APP.before_request
def before_request():
    """ Helps keep track of user """
    g.user = current_user


if __name__ == '__main__':
    APP.debug = False
    APP.run(host='0.0.0.0', port=8080)
