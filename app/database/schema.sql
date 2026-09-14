CREATE TABLE exposures (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cycle_id INT NOT NULL,
    asset_name VARCHAR(100) NOT NULL,
    vulnerability VARCHAR(255) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    risk_score INT NOT NULL,
    status VARCHAR(30),
    priority VARCHAR(20) DEFAULT 'Pending',
    priority_score INT DEFAULT 0,
    asset_id VARCHAR(50),
    beta_risk_rating INT DEFAULT 0,
    business_criticality VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);


CREATE TABLE validation_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cycle_id INT NOT NULL,
    exposure_id INT NOT NULL,
    validation_type VARCHAR(100),
    validation_status VARCHAR(30) DEFAULT 'Planned',
    assigned_to VARCHAR(100),
    planned_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);




CREATE TABLE remediation_tracking (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cycle_id INT NOT NULL,
    exposure_id INT NOT NULL,
    remediation_status VARCHAR(50) DEFAULT 'Pending',
    assigned_to VARCHAR(100),
    completion_date DATE,
    remediation_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE exceptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cycle_id INT NOT NULL,
    exposure_id INT NOT NULL,
    exception_reason TEXT NOT NULL,
    approved_by VARCHAR(100),
    exception_status VARCHAR(30) DEFAULT 'Pending',
    expiry_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);