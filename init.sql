CREATE TABLE Companies (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE Trip (
    id SERIAL PRIMARY KEY,
    plane TEXT,
    company INT REFERENCES Companies(id),
    town_from TEXT,
    town_to TEXT,
    time_out TIMESTAMP,
    time_in TIMESTAMP
);

CREATE TABLE Passengers (
    id SERIAL PRIMARY KEY,
    full_name TEXT,
    phone TEXT,
    email TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE Pass_in_trip (
    id SERIAL PRIMARY KEY,
    trip INT REFERENCES Trip(id),
    passenger INT REFERENCES Passengers(id),
    place TEXT
);

-- демо-данные
INSERT INTO Companies (name) VALUES ('Aeroflot'), ('AirFrance');
INSERT INTO Trip (plane, company, town_from, town_to, time_out, time_in)
VALUES ('A320', 1, 'Москва', 'Париж', '2024-01-15 09:00:00', '2024-01-15 11:30:00');