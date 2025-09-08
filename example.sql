SELECT * FROM Trip;

SELECT t.plane, c.name as company_name, t.town_from, t.town_to
FROM Trip t
JOIN Companies c ON t.company = c.id;
