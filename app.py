from http import client
from flask import Flask
from flask_cors import CORS
from auth import auth
from barbers import barbers
from cliente import clients
from services import service
from barbers import barber
from appointments import appointments
from products import products
from stock import stock
from package import package
from barber_schedule import schedule
from barber_schedule_get import schedule_get
from orders import orders
from database import get_db, close_connection











app = Flask(__name__)

# Libera tudo (para teste). Depois você pode restringir.
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

app.register_blueprint(auth)
app.register_blueprint(barbers)
app.register_blueprint(barber)
app.register_blueprint(clients)
app.register_blueprint(service)
app.register_blueprint(appointments)
app.register_blueprint(products)
app.register_blueprint(stock)
app.register_blueprint(package)
app.register_blueprint(schedule)
app.register_blueprint(schedule_get)
app.register_blueprint(orders)

app.teardown_appcontext(close_connection)
 


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
  