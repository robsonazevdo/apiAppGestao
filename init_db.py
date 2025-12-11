import sqlite3

# Conexão e criação do banco
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Drop e criação das tabelas
cursor.executescript('''
DROP TABLE IF EXISTS barbers;
DROP TABLE IF EXISTS photos;
DROP TABLE IF EXISTS services;
DROP TABLE IF EXISTS testimonials;
DROP TABLE IF EXISTS availability;
DROP TABLE IF EXISTS availability_hours;
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS favorites;
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS sale_items;
DROP TABLE IF EXISTS cashflow;
DROP TABLE IF EXISTS clients;
DROP TABLE IF EXISTS barber_services;
DROP TABLE IF EXISTS packages;
DROP TABLE IF EXISTS stock_control;
DROP TABLE IF EXISTS package_services;
DROP TABLE IF EXISTS barber_schedule;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS order_items;


CREATE TABLE favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT NOT NULL,
    barber_id INTEGER NOT NULL,
    FOREIGN KEY(user_email) REFERENCES users(email),
    FOREIGN KEY(barber_id) REFERENCES barbers(id),
    UNIQUE(user_email, barber_id)
);

CREATE TABLE IF NOT EXISTS barber_custom_hours (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barber_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    active INTEGER NOT NULL, -- 0 = disponível / 1 = indisponível
    updated_at TEXT NOT NULL,
    FOREIGN KEY (barber_id) REFERENCES barbers(id)
);


CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    avatar TEXT
);

CREATE TABLE barbers (
    id INTEGER PRIMARY KEY,
    name TEXT,
    avatar TEXT,
    stars REAL,
    lat REAL,
    lng REAL,
    loc TEXT
);

CREATE TABLE photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barber_id INTEGER,
    url TEXT,
    FOREIGN KEY(barber_id) REFERENCES barbers(id)
);

CREATE TABLE services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE barber_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barber_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    price REAL NOT NULL,
    duration INTEGER NOT NULL,
    FOREIGN KEY(barber_id) REFERENCES barbers(id),
    FOREIGN KEY(service_id) REFERENCES services(id),
    UNIQUE(barber_id, service_id)
);

CREATE TABLE barber_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barber_id INTEGER NOT NULL,
    weekday INTEGER NOT NULL, -- 0=Seg, 6=Dom
    start_time TEXT,
    end_time TEXT,
    slot_minutes INTEGER DEFAULT 30
);


CREATE TABLE testimonials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barber_id INTEGER,
    name TEXT,
    rate INTEGER,
    body TEXT,
    FOREIGN KEY(barber_id) REFERENCES barbers(id)
);

CREATE TABLE availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barber_id INTEGER,
    date TEXT,
    FOREIGN KEY(barber_id) REFERENCES barbers(id)
);

CREATE TABLE availability_hours (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    availability_id INTEGER,
    hour TEXT,
    is_booked BOOLEAN DEFAULT 0,
    FOREIGN KEY(availability_id) REFERENCES availability(id)
);

CREATE TABLE appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    barber_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    datetime TEXT NOT NULL,
    user_email TEXT,
    FOREIGN KEY(barber_id) REFERENCES barbers(id),
    FOREIGN KEY(client_id) REFERENCES clients(id),
    FOREIGN KEY(user_email) REFERENCES users(email),
    FOREIGN KEY(service_id) REFERENCES services(id)
);


CREATE TABLE sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barber_id INTEGER,
    client_id INTEGER,
    total REAL,
    datetime TEXT,
    FOREIGN KEY(barber_id) REFERENCES barbers(id),
    FOREIGN KEY(client_id) REFERENCES clients(id)
);

CREATE TABLE sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER,
    service_id INTEGER,
    price REAL,
    FOREIGN KEY(sale_id) REFERENCES sales(id),
    FOREIGN KEY(service_id) REFERENCES services(id)
);

CREATE TABLE cashflow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barber_id INTEGER,
    type TEXT CHECK(type IN ('entrada', 'saida')),
    description TEXT,
    amount REAL,
    datetime TEXT,
    FOREIGN KEY(barber_id) REFERENCES barbers(id)
);

CREATE TABLE clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    phone TEXT,
    email TEXT UNIQUE,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
                     

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    price REAL NOT NULL,
    cost REAL,
    unit TEXT, 
    description TEXT
);


CREATE TABLE stock_control (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    type TEXT CHECK(type IN ('entrada', 'saida')) NOT NULL,
    quantity REAL NOT NULL,
    description TEXT,
    datetime TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(id)
);


CREATE TABLE sale_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    unit_price REAL NOT NULL,
    FOREIGN KEY(sale_id) REFERENCES sales(id),
    FOREIGN KEY(product_id) REFERENCES products(id)
);
                     
CREATE TABLE packages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  price REAL NOT NULL,
  duration INTEGER, -- minutos
  expiration_date TEXT
);
                     

CREATE TABLE package_services (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  package_id INTEGER,
  service_id INTEGER,
  FOREIGN KEY(package_id) REFERENCES packages(id),
  FOREIGN KEY(service_id) REFERENCES services(id)
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    barber_id INTEGER,
    opened_at TEXT DEFAULT CURRENT_TIMESTAMP,
    order_number TEXT ,
    status TEXT DEFAULT 'aberta', -- aberta, finalizada, cancelada
    total REAL,
    discount REAL DEFAULT 0,
    payment_method TEXT,
    total_final REAL,
    FOREIGN KEY(client_id) REFERENCES clients(id),
    FOREIGN KEY(barber_id) REFERENCES barbers(id)
);



CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    qtd INTEGER NOT NULL,
    price REAL NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders(id),
    FOREIGN KEY(service_id) REFERENCES services(id)
);



''')

# Inserir barbeiros
barbers = [
    (1, "Barbeiro 1", "https://i.pravatar.cc/150?img=5", 4.8, -23.5505, -46.6333, "São Paulo"),
    (2, "Barbeiro 2", "https://i.pravatar.cc/150?img=6", 4.6, -23.5595, -46.6350, "São Paulo"),
    (3, "Barbeiro 3", "https://i.pravatar.cc/150?img=7", 3.8, -22.9068, -43.1729, "Rio de Janeiro")
]
cursor.executemany('''
    INSERT INTO barbers (id, name, avatar, stars, lat, lng, loc)
    VALUES (?, ?, ?, ?, ?, ?, ?)
''', barbers)

# Inserir fotos
photos = [
    (1, "https://i.pravatar.cc/300?img=15"),
    (1, "https://i.pravatar.cc/300?img=16"),
    (1, "https://i.pravatar.cc/300?img=9"),
    (2, "https://i.pravatar.cc/300?img=12"),
    (2, "https://i.pravatar.cc/300?img=13"),
    (2, "https://i.pravatar.cc/300?img=14"),
    (3, "https://i.pravatar.cc/300?img=14"),
    (3, "https://i.pravatar.cc/300?img=15"),
    (3, "https://i.pravatar.cc/300?img=17")
]
cursor.executemany('INSERT INTO photos (barber_id, url) VALUES (?, ?)', photos)

# Inserir serviços genéricos
services = [("Corte",), ("Barba",), ("Corte + Barba",), ("Corte Social",)]
cursor.executemany('INSERT INTO services (name) VALUES (?)', services)

# Relacionar barbeiros com serviços (barber_services)
barber_services = [
    (1, 1, 50, 30),  # barbeiro 1 -> Corte
    (1, 2, 30, 20),  # barbeiro 1 -> Barba
    (2, 1, 40, 30),  # barbeiro 2 -> Corte
    (2, 2, 20, 20),  # barbeiro 2 -> Barba
    (2, 3, 60, 45),  # barbeiro 2 -> Corte + Barba
    (3, 4, 35, 30)   # barbeiro 3 -> Corte Social
]
cursor.executemany('''
    INSERT INTO barber_services (barber_id, service_id, price, duration)
    VALUES (?, ?, ?, ?)
''', barber_services)

# Depoimentos
testimonials = [
    (1, "João", 5, "Ótimo corte!"),
    (1, "Rodrigo", 4, "Ótimo corte!"),
    (2, "Lucas", 5, "Trabalho incrível!"),
    (2, "João", 5, "Trabalho incrível!"),
    (3, "Pedro", 4, "Bom atendimento, mas poderia melhorar no tempo.")
]
cursor.executemany('INSERT INTO testimonials (barber_id, name, rate, body) VALUES (?, ?, ?, ?)', testimonials)

# Disponibilidade
availability_raw = [
    (1, "2025-06-02", ["09:00", "10:00", "11:00", "12:00", "15:00", "16:00"]),
    (1, "2025-06-03", ["09:00", "10:00", "11:00", "12:00"]),
    (2, "2025-06-02", ["09:00", "10:00", "11:00", "12:00", "15:00"]),
    (2, "2025-06-03", ["09:00", "10:00", "11:00", "12:00"]),
    (2, "2025-06-04", ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"]),
    (3, "2025-06-02", ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"]),
    (3, "2025-06-03", ["09:00", "10:00", "11:00", "12:00"]),
    (3, "2025-06-04", ["09:00", "10:00", "11:00", "12:00"]),
    (3, "2025-06-05", ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"])
]
for barber_id, date, hours in availability_raw:
    cursor.execute('INSERT INTO availability (barber_id, date) VALUES (?, ?)', (barber_id, date))
    availability_id = cursor.lastrowid
    for hour in hours:
        cursor.execute('INSERT INTO availability_hours (availability_id, hour) VALUES (?, ?)', (availability_id, hour))

# Clientes
clients = [
    (1, "João", "1900112233", 'joao@email.com', '2025-06-04 14:32:10'),
    (2, "Maria", "1900112233", 'maria@email.com', '2025-06-03 14:32:10'),
    (3, "Tati", "1900112233", 'tati@email.com', '2025-06-03 14:32:10')
]
cursor.executemany('''
    INSERT INTO clients (id, name, phone, email, created_at)
    VALUES (?, ?, ?, ?, ?)
''', clients)


# Inserindo produtos
products = [
    ("Pomada Modeladora", 30.0, 12.0, "unidade", "Pomada para cabelo fixação forte"),
    ("Shampoo Anticaspa", 45.0, 20.0, "ml", "Shampoo para tratamento de caspa"),
    ("Creme de Barbear", 25.0, 10.0, "unidade", "Creme para barbear")
]
cursor.executemany('''
    INSERT INTO products (name, price, cost, unit, description)
    VALUES (?, ?, ?, ?, ?)
''', products)

# Entrada de estoque
stock_entries = [
    (1, 'entrada', 10, 'Compra inicial de pomadas'),
    (2, 'entrada', 5, 'Compra de shampoos'),
    (3, 'entrada', 7, 'Compra de cremes de barbear')
]
cursor.executemany('''
    INSERT INTO stock_control (product_id, type, quantity, description)
    VALUES (?, ?, ?, ?)
''', stock_entries)


# Finaliza
conn.commit()
conn.close()

print("Banco de dados com relacionamento barbeiro-serviço normalizado com sucesso.")
