from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from flask_uploads import UploadSet, IMAGES, configure_uploads
import json

from helpers import *
import time
from models import users, groups, posts

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure flask_upload API
photos = UploadSet("photos", IMAGES)
app.config["UPLOADED_PHOTOS_DEST"] = "static/img"
configure_uploads(app, photos)

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    return render_template("index.html")

@app.route("/search")
def search():
    user_id = session["user_id"]
    group = groups.Group(user_id, 0)
    data = group.loadgroups()

    text = request.args['searchText']

    if len(text) >= 2:
        result = []
        for element in data:
            for i in element:
                if i == 'group_name':
                    searchable = element[i]
                    if str(text).lower() in str(searchable).lower():
                        result.append(searchable)
                else:
                    pass

        if not result:
            return json.dumps({"results":["No groups found"]})

        return json.dumps({"results":result})

    else:
        return None

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""

    if request.method == "POST":

        # ensure username input not blank
        if not request.form.get("username"):
            return render_template("register.html")

        # ensure password not blank
        elif not request.form.get("password"):
            return render_template("register.html")

        # ensure same password filled in again
        if request.form.get("password") != request.form.get("passwordcheck"):
            return render_template("register.html")

            # ensure first name not blank
        if not request.form.get("first_name"):
            return render_template("register.html")

        # ensure last name not blank
        elif not request.form.get("last_name"):
            return render_template("register.html")


        # retrieve user after register
        register = users.User.register(request.form.get("username"),
                                       request.form.get("password"),
                                       request.form.get("first_name"),
                                       request.form.get("last_name"))

        # if username already exists
        if register is None:
            return render_template("register.html")

        # if register successful
        else:

            # log user in
            session["user_id"] = register["user_id"]

            # redirect user to homepage
            return redirect(url_for("index"))

    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in. """

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return render_template("login.html", missing_name = "Username missing")

        # ensure password was submitted
        elif not request.form.get("password"):
            return render_template("login.html", missing_pass = "Password missing")

        # retrieve user after login
        login = users.User.login(request.form.get("username"), request.form.get("password"))

        # if login unsuccessful
        if login is None:
            return render_template("login.html", failure = "Login unsuccessful!")

        # if login successful
        else:

            # log user in
            session["user_id"] = login["user_id"]

            # redirect to index
            return redirect(url_for("index"))

    # user reached page via GET
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))


@app.route("/followgroup", methods=["GET", "POST"])
@login_required
def followgroup():

    # instantiate functions
    group = groups.Group(session["user_id"], 0)
    followable = group.loadgroups()

    if request.method == "POST":
        # controls if a button is pressed and which button is pressed
        if request.form["action"]:
            group_id = request.form["action"]

            # the group_id of the pressed button will be transported to the follow function and returns the follow_id
            group = groups.Group(session["user_id"], group_id)
            result = group.follow()
            if result == None:
                return render_template("followgroup.html", followable = followable, error = "You're already member of this group")
            else:
                return render_template("groupfeed.html")

    else:
        return render_template("followgroup.html", followable = followable)

@app.route("/post", methods=["GET", "POST"])
@login_required
def post():

    # instantiate functions
    post = posts.Post(session["user_id"])
    following = post.loadgroups()

    if request.method == "POST" and 'photo' in request.files:
        # request photo
        photo = request.files["photo"]

        # check for correct user input
        if not photo:
            return render_template("post.html", groups = following, error = "no photo uploaded, pick one!")

        # check for allowed extensions
        filename = str(photo.filename)
        if filename.endswith(('.jpg','.png','.jpeg','.gif','.JPG','.PNG','.JPEG','.GIF')):

            # if allowed, save photo in folder
            file = photos.save(photo)

            # check in which group to post
            choice = request.form["group"]
            if not choice:
                return render_template("post.html", groups=following, error = "no group chosen")

            # pull description of photo
            description = request.form["description"]

            # insert into database
            path = file
            post.upload(path, choice, description)

            return redirect(url_for("index"))

        # if extension is not allowed
        else:
            return render_template("post.html", groups = following, error = "extension not allowed")

    else:
        return render_template("post.html", groups = following)

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():

    if request.method == "POST":

        # instantiate user
        user = users.User(session["user_id"])

        # if password button is pressed
        if request.form["action"] == "Change password":

            # if any form blank
            if not request.form.get("current_password"):
                return render_template("settings.html", missingcurrent = "Current password missing")

            if not request.form.get("new_password"):
                return render_template("settings.html", missingnew = "New password missing")

            if not request.form.get("check_password"):
                return render_template("settings.html", missingcheck = "Password check missing")

            # check if new password and password match
            if request.form.get("new_password") != request.form.get("check_password"):
                return render_template("settings.html", nomatch = "Passwords do not match")

            # change password
            change_password = user.change_password(request.form.get("current_password"),
                                          request.form.get("new_password"),
                                          request.form.get("check_password"))

            # if change successful
            if change_password == True:
                return render_template("settings.html", success= "Password changed!")

            else:
                return render_template("settings.html", failure = "Current password is incorrect!")


        # if username button is pressed
        elif request.form["action"] == "Change username":

            # if any form blank
            if not request.form.get("current_username"):
                return render_template("settings.html", missingcurrent = "Current username missing")

            if not request.form.get("new_username"):
                return render_template("settings.html", missingnew2 = "New username missing")

            if not request.form.get("current_password"):
                return render_template("settings.html", missingcheck2 = "Password is missing")

            # change username
            change_username = user.change_username(request.form.get("current_username"),
                                                   request.form.get("new_username"),
                                                   request.form.get("current_password"))

            if change_username is True:
                return render_template("settings.html", success = "Username changed!")

            if change_username is False:
                return render_template("settings.html", failure2 = "Password is incorrect!")

            if change_username is None:
                return render_template("settings.html", failure2 = "Username already exists!")

    else:
        return render_template("settings.html")


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    #TODO
    return render_template("profile.html")

@app.route("/create", methods=["GET", "POST"])
@login_required
def create():

    if request.method == "POST":
        # checks if inputs are correct
        if not request.form.get("title"):
            return render_template("create.html", missingtitle = "The title is missing")

        elif not request.form.get("description"):
            return render_template("create.html", missingdesc = "The description is missing")

        # create function is being called and generates output
        group = groups.Group(session["user_id"], 0)
        create = group.create(request.form.get("title"), request.form.get("description"))

        # responds to the output
        if create == None:
            return render_template("create.html", missingtitle = "The title already exists")

        return render_template("groupfeed.html")
    else:
        return render_template("create.html")

@app.route("/groupfeed", methods=["GET", "POST"])
@login_required
def groupfeed():
    # initiate functions
    group = groups.Group(session["user_id"], group_id)
    feed = group.loadfeed()

    if request.method == "POST":
        return "hello"
    else:
        return render_template("groupfeed.html", feed = feed)