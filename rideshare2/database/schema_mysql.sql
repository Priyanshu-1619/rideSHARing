-- ============================================================
-- NEXTRIDE: College Ride Sharing System
-- MySQL Schema (Normalized - BCNF)
-- ============================================================

CREATE DATABASE IF NOT EXISTS nextride;
USE nextride;

-- Students Table
CREATE TABLE IF NOT EXISTS Students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    email      VARCHAR(150) NOT NULL UNIQUE,
    phone      VARCHAR(15),
    password   VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rides Table
CREATE TABLE IF NOT EXISTS Rides (
    ride_id         INT AUTO_INCREMENT PRIMARY KEY,
    driver_id       INT NOT NULL,
    source          VARCHAR(150) NOT NULL,
    destination     VARCHAR(150) NOT NULL,
    ride_time       DATETIME NOT NULL,
    total_seats     INT NOT NULL CHECK (total_seats > 0),
    available_seats INT NOT NULL,
    price_per_seat  DECIMAL(8,2) NOT NULL CHECK (price_per_seat >= 0),
    status          ENUM('Open','Full','Cancelled','Completed') DEFAULT 'Open',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (driver_id) REFERENCES Students(student_id) ON DELETE CASCADE,
    CONSTRAINT chk_seats CHECK (available_seats <= total_seats AND available_seats >= 0)
);

-- Requests Table
CREATE TABLE IF NOT EXISTS Requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    ride_id    INT NOT NULL,
    rider_id   INT NOT NULL,
    status     ENUM('Pending','Accepted','Rejected','Cancelled','Completed','No-Show','Late') DEFAULT 'Pending',
    actual_arrival_time DATETIME NULL,
    completion_status ENUM('On-Time','Late','Missed','Cancelled') NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ride_id)  REFERENCES Rides(ride_id) ON DELETE CASCADE,
    FOREIGN KEY (rider_id) REFERENCES Students(student_id) ON DELETE CASCADE,
    UNIQUE KEY uq_ride_rider (ride_id, rider_id)   -- no duplicate booking
);

-- Payments Table
CREATE TABLE IF NOT EXISTS Payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL UNIQUE,
    amount     DECIMAL(8,2) NOT NULL,
    status     ENUM('Pending','Paid','Refunded') DEFAULT 'Pending',
    paid_at    TIMESTAMP NULL,
    FOREIGN KEY (request_id) REFERENCES Requests(request_id) ON DELETE CASCADE
);

-- Penalties Table
CREATE TABLE IF NOT EXISTS Penalties (
    penalty_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    request_id INT NOT NULL,
    penalty_type ENUM('Cancellation','Delay','Missed-Ride','Driver-Cancellation') NOT NULL,
    amount DECIMAL(8,2) NOT NULL,
    reason TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (request_id) REFERENCES Requests(request_id) ON DELETE CASCADE
);

-- ============================================================
-- TRIGGER: auto-decrement available_seats on acceptance
-- ============================================================
DELIMITER $$
CREATE TRIGGER trg_accept_request
AFTER UPDATE ON Requests
FOR EACH ROW
BEGIN
    IF NEW.status = 'Accepted' AND OLD.status != 'Accepted' THEN
        UPDATE Rides SET available_seats = available_seats - 1
        WHERE ride_id = NEW.ride_id;
        -- Mark ride as Full if no seats left
        UPDATE Rides SET status = 'Full'
        WHERE ride_id = NEW.ride_id AND available_seats = 0;
    END IF;
    IF NEW.status = 'Cancelled' AND OLD.status = 'Accepted' THEN
        UPDATE Rides SET available_seats = available_seats + 1,
                         status = 'Open'
        WHERE ride_id = NEW.ride_id;
    END IF;
END$$
DELIMITER ;

-- ============================================================
-- SAMPLE DATA
-- ============================================================
INSERT INTO Students (name, email, phone, password) VALUES
('Arjun Sharma',   'arjun@college.edu',   '9876543210', 'pbkdf2:sha256:arjun123'),
('Priya Mehta',    'priya@college.edu',   '9876543211', 'pbkdf2:sha256:priya123'),
('Rohan Gupta',    'rohan@college.edu',   '9876543212', 'pbkdf2:sha256:rohan123'),
('Sneha Verma',    'sneha@college.edu',   '9876543213', 'pbkdf2:sha256:sneha123'),
('Vikram Singh',   'vikram@college.edu',  '9876543214', 'pbkdf2:sha256:vikram123');

INSERT INTO Rides (driver_id, source, destination, ride_time, total_seats, available_seats, price_per_seat, status) VALUES
(1, 'Main Gate', 'Railway Station',  DATE_ADD(NOW(), INTERVAL 2 HOUR),  3, 3, 50.00, 'Open'),
(2, 'Hostel A',  'City Mall',        DATE_ADD(NOW(), INTERVAL 3 HOUR),  2, 2, 30.00, 'Open'),
(3, 'Library',   'Airport',          DATE_ADD(NOW(), INTERVAL 5 HOUR),  4, 4, 120.00,'Open'),
(4, 'Canteen',   'Bus Stand',        DATE_ADD(NOW(), INTERVAL 1 HOUR),  3, 3, 20.00, 'Open'),
(5, 'Gate 2',    'Metro Station',    DATE_ADD(NOW(), INTERVAL 4 HOUR),  2, 2, 40.00, 'Open');
