SELECT * FROM Trip;

SELECT t.plane, c.name as company_name, t.town_from, t.town_to
FROM Trip t
JOIN Companies c ON t.company = c.id;

SELECT town_from, COUNT(*) as flight_count
FROM Trip
GROUP BY town_from;

INSERT INTO Passengers (full_name, phone, email)
VALUES ('Иван Иванов', '+79161234567', 'ivan@mail.com');

INSERT INTO Pass_in_trip (trip, passenger, place)
VALUES (1, 1, '12A');

DELETE FROM Pass_in_trip
WHERE trip = 5;

SELECT
p.full_name,
c.name as company_name,
t.plane,
t.town_from,
t.town_to,
pit.place,
t.time_out,
t.time_in
FROM Passengers p
JOIN Pass_in_trip pit ON p.id = pit.passenger
JOIN Trip t ON pit.trip = t.id
JOIN Companies c ON t.company = c.id
WHERE t.town_to = 'Москва'
ORDER BY t.time_out DESC;

SELECT
c.name as company_name,
COUNT(t.id) as total_flights,
COUNT(DISTINCT pit.passenger) as unique_passengers
FROM Companies c
JOIN Trip t ON c.id = t.company
LEFT JOIN Pass_in_trip pit ON t.id = pit.trip
GROUP BY c.name
HAVING COUNT(t.id) > 10;

SELECT full_name, phone
FROM Passengers
WHERE id IN (
SELECT passenger
FROM Pass_in_trip
WHERE trip IN (
SELECT id
FROM Trip
WHERE town_from = 'Париж' AND time_out > '2024-01-01'
)
);