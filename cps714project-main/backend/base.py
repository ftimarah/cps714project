import json
from flask import Flask, request, jsonify, render_template
from flask.helpers import send_from_directory
from datetime import datetime, timedelta, timezone

from flask_cors import CORS, cross_origin
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, unset_jwt_cookies, jwt_required, \
    JWTManager

from db__init import db, api, ENV
from models import LanguageCodeName, PhraseCodeName, Phrases, Restaurants, Users, RestaurantReviews, \
    RestaurantReviewsImages
from flask_sqlalchemy import SQLAlchemy
from languages import Language
import googlemaps

CAPITALALPHABETS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
SMALLALPHABETS = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"
cors = CORS(api, resources={r"/*": {"origins": "*"}})

# db.init_app(api)

# please run whole app with api.app_context()
with api.app_context():
    if ENV == "dev":
        # do next 14 lines only once
        # only add languages from l.print_available_languages()
        l = Language()
        l.add_new_language("english")
        l.add_new_language("french")
        l.add_new_language("spanish")
        l.add_new_language("swahili")
        l.add_new_language("japanese")
        l.add_new_language("chinese (simplified)")
        l.add_new_language("yoruba")
        l.add_new_phrase("Do you speak English?")
        l.add_new_phrase("My name is __________.")
        l.add_new_phrase("Can you speak more slowly?")
        l.add_new_phrase("Where can I find a bus/taxi?")
        l.add_new_phrase("Where can I find a train/metro?")
        # l.print_available_languages()

    api.config["JWT_SECRET_KEY"] = "TOURIST_APP"
    api.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)

    jwt = JWTManager(api)


    @api.after_request
    def refresh_expiring_jwts(response):
        try:
            exp_timestamp = get_jwt()["exp"]
            now = datetime.now(timezone.utc)
            target_timestamp = datetime.timestamp(now + timedelta(minutes=30))
            if target_timestamp > exp_timestamp:
                access_token = create_access_token(identity=get_jwt_identity())
                data = response.get_json()
                if type(data) is dict:
                    data["access_token"] = access_token
                    response.data = json.dumps(data)
            return response
        except (RuntimeError, KeyError):
            # Case where there is not a valid JWT. Just return the original respone
            return response


    @api.route('/', methods=["GET", "POST"])
    def create_token():
        email = request.json.get("email", None)
        password = request.json.get("password", None)

        user = db.session.query(Users).filter_by(email=email).first()
        if not user:
            return {"msg": "Email does not exist"}, 401
        else:
            if not user.check_password(password):
                return {"msg": "Wrong password. Please try again."}, 401

        access_token = create_access_token(identity=email)
        response = {"access_token": access_token}
        return response


    @api.route('/', methods=["GET", "POST"])
    def serve():
        return send_from_directory(api.static_folder, 'index.html')


    @api.route("/logout", methods=["GET", "POST"])
    def logout():
        response = jsonify({"msg": "logout successful"})
        unset_jwt_cookies(response)
        return response


    @api.route("/signup", methods=["GET", "POST"])
    def signup():
        l, u, d, plen = 0, 0, 0, 0

        username = request.json.get("username", None)
        email = request.json.get("email", None)
        password = request.json.get("password", None)
        verify_password = request.json.get("verify_password", None)
        first_name = request.json.get("first_name", None)
        last_name = request.json.get("last_name", None)
        if password != verify_password:
            return {"msg": "Password do not match."}, 401


        for i in password:
            # counting lowercase alphabets
            if (i in SMALLALPHABETS):
                l += 1

                # counting uppercase alphabets
            if (i in CAPITALALPHABETS):
                u += 1

                # counting digits
            if (i in DIGITS):
                d += 1
            plen+=1

        if not (l >= 1 and u >= 1 and d >= 1 and plen >= 6):
            return {"msg": "Password must have a minimum length of 6 and contain lowercase, uppercase letters and a number."}, 401

        data = Users(username, email, password, first_name, last_name, location=None)
        db.session.add(data)
        db.session.commit()

        response = jsonify({"msg": "User Successfully Created!"})
        return response


    @api.route("/userprofile", methods=["GET", "POST"])
    def editprofile():
        l, u, d, plen = 0, 0, 0, 0
        username = request.json.get("username", None)
        email = request.json.get("email", None)
        password = request.json.get("password", None)
        verify_password = request.json.get("verify_password", None)
        if password != verify_password:
            return {"msg": "Password do not match."}, 401

        for i in password:
            # counting lowercase alphabets
            if (i in SMALLALPHABETS):
                l += 1

                # counting uppercase alphabets
            if (i in CAPITALALPHABETS):
                u += 1

                # counting digits
            if (i in DIGITS):
                d += 1
            plen+=1

        if not (l >= 1 and u >= 1 and d >= 1 and plen >= 6):
            return {"msg": "Password must have a minimum length of 6 and contain lowercase, uppercase letters and a number."}, 401

        db.session.query(Users).filter_by(email=email).update({'username': username, 'email': email, 'password': password})
        db.session.commit()

        response = jsonify({"msg": "Edit Profile Successful"})
        return response


    @jwt_required()  # new line
    @api.route('/profile', methods=["GET", "POST"])
    def my_profile():
        response_body = {
            "name": "Test",
            "about": "Hello! Testing"
        }

        return response_body

    gmaps = googlemaps.Client(key='AIzaSyAXf5iZ79WWzZ3gf17SVyM9b6i6vOS_QNk', )

    @api.route('/restaurant/recommendation', methods=['GET', 'POST'])
    @cross_origin()
    def restaurant_recommendation():
        args = request.args
        lat = args.get(key='lat', default=0)
        lng = args.get(key='lng', default=0)
        placesResult = gmaps.places(
            location=(lat, lng),
            query='restaurant')
        return placesResult


    @api.route('/entertainment/recommendation', methods=['GET', 'POST'])
    @cross_origin()
    def entertainment_recommendation():
        args = request.args
        lat = args.get(key='lat', default=0)
        lng = args.get(key='lng', default=0)
        placesResult = gmaps.places(
            location=(lat, lng),
            query='attractions')
        return placesResult

    @api.route('/events/recommendation', methods=['GET'])
    @cross_origin()
    def nearby_events():
        args = request.args
        lat = args.get(key='lat', default=0)
        lng = args.get(key='lng', default=0)
        placesResult = gmaps.places(
            location=(lat, lng),
            query='events')
        return placesResult

if __name__ == "__main__":
    api.run(debug=True)