-- SELECT запросы (будут разрешены)
SELECT * FROM users;
SELECT u.username, o.amount FROM users u JOIN orders o ON u.id = o.user_id;
SELECT COUNT(*) FROM products WHERE category = 'Electronics';

-- INSERT запросы (будут разрешены)
INSERT INTO users (username, email) VALUES ('new_user', 'new@example.com');
INSERT INTO orders (user_id, amount) VALUES (1, 150.00);

-- UPDATE запросы (будут разрешены)
UPDATE products SET price = 89.99 WHERE id = 5;
UPDATE users SET is_active = false WHERE last_login < '2023-01-01';

-- DELETE запросы с WHERE (будут разрешены)
DELETE FROM order_items WHERE order_id = 100;
DELETE FROM users WHERE is_active = false AND created_at < '2022-01-01';

-- Опасные запросы (будут заблокированы)
DELETE FROM users;  -- Без WHERE
DROP TABLE orders;  -- DROP операция
TRUNCATE products;  -- TRUNCATE операция

-- Сложный JOIN запрос
SELECT
    u.username,
    p.name,
    oi.quantity,
    oi.price * oi.quantity as total_price
FROM users u
JOIN orders o ON u.id = o.user_id
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id
WHERE o.status = 'completed'
ORDER BY total_price DESC;

-- Агрегирующий запрос с GROUP BY
SELECT
    p.category,
    COUNT(oi.id) as total_sold,
    SUM(oi.quantity * oi.price) as total_revenue
FROM products p
JOIN order_items oi ON p.id = oi.product_id
GROUP BY p.category
HAVING SUM(oi.quantity * oi.price) > 1000;

-- Запрос с подзапросом
SELECT username, email
FROM users
WHERE id IN (
    SELECT user_id
    FROM orders
    WHERE amount > 500 AND status = 'completed'
);