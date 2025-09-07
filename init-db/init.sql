-- Создание тестовых таблиц
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    category VARCHAR(50),
    stock_quantity INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL
);

-- Вставка тестовых данных
INSERT INTO users (username, email) VALUES
('john_doe', 'john@example.com'),
('jane_smith', 'jane@example.com'),
('bob_wilson', 'bob@example.com'),
('alice_brown', 'alice@example.com');

INSERT INTO products (name, price, category, stock_quantity) VALUES
('Laptop', 999.99, 'Electronics', 10),
('Smartphone', 499.99, 'Electronics', 25),
('Book: SQL Basics', 29.99, 'Books', 100),
('Coffee Mug', 9.99, 'Home', 50),
('Headphones', 79.99, 'Electronics', 30);

INSERT INTO orders (user_id, amount, status) VALUES
(1, 1029.98, 'completed'),
(2, 499.99, 'completed'),
(3, 39.98, 'pending'),
(1, 79.99, 'shipped');

INSERT INTO order_items (order_id, product_id, quantity, price) VALUES
(1, 1, 1, 999.99),
(1, 5, 1, 79.99),
(2, 2, 1, 499.99),
(3, 4, 2, 9.99),
(4, 5, 1, 79.99);

-- Создание индексов для тестирования производительности
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);

-- Создание представлений для сложных запросов
CREATE OR REPLACE VIEW user_order_summary AS
SELECT
    u.id as user_id,
    u.username,
    u.email,
    COUNT(o.id) as total_orders,
    COALESCE(SUM(o.amount), 0) as total_spent
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.username, u.email;

-- Создание функции для генерации тестовых данных
CREATE OR REPLACE FUNCTION generate_test_orders(user_count INT, orders_per_user INT)
RETURNS VOID AS $$
DECLARE
    user_id INT;
    i INT;
    j INT;
BEGIN
    FOR i IN 1..user_count LOOP
        INSERT INTO users (username, email)
        VALUES ('test_user_' || i, 'test' || i || '@example.com')
        RETURNING id INTO user_id;

        FOR j IN 1..orders_per_user LOOP
            INSERT INTO orders (user_id, amount, status)
            VALUES (user_id, (RANDOM() * 1000)::DECIMAL(10,2),
                    CASE WHEN RANDOM() > 0.3 THEN 'completed' ELSE 'pending' END);
        END LOOP;
    END LOOP;
END;
$$ LANGUAGE plpgsql;