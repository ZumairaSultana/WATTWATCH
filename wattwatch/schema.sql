-- WATT-WATCH database schema (SQLite).
--
-- Based on the three tables suggested in "Household EB Meter Database":
-- Household, EB_Meter and Electricity_Bill. Two columns are added to
-- EB_Meter so the app can track a billing cycle:
--   Previous_Reading_Date  date of the reading at the start of the period
--                          (the original table only has the end date)
--   Bill_ID                which bill this reading was billed in;
--                          NULL means "not billed yet" = current cycle
--
-- In each EB_Meter row, Previous_Reading -> Current_Reading is one period
-- between two meter readings, and Units_Consumed = Current - Previous.

CREATE TABLE IF NOT EXISTS Household (
    House_ID        VARCHAR(10)  PRIMARY KEY,
    Consumer_Number VARCHAR(20)  NOT NULL UNIQUE,
    Household_Name  VARCHAR(100) NOT NULL,
    Address         VARCHAR(255),
    Connection_Type VARCHAR(20)  NOT NULL
        CHECK (Connection_Type IN ('Single phase', 'Three phase'))
);

CREATE TABLE IF NOT EXISTS Electricity_Bill (
    Bill_ID         INTEGER       PRIMARY KEY AUTOINCREMENT,
    House_ID        VARCHAR(10)   NOT NULL REFERENCES Household(House_ID),
    Billing_Period  VARCHAR(20)   NOT NULL,
    Units_Consumed  DECIMAL(10,2) NOT NULL CHECK (Units_Consumed >= 0),
    Bill_Amount     DECIMAL(10,2) NOT NULL CHECK (Bill_Amount >= 0),
    Payment_Status  VARCHAR(20)   NOT NULL DEFAULT 'Unpaid'
        CHECK (Payment_Status IN ('Paid', 'Unpaid', 'Pending'))
);

CREATE TABLE IF NOT EXISTS EB_Meter (
    Meter_ID              INTEGER       PRIMARY KEY AUTOINCREMENT,
    House_ID              VARCHAR(10)   NOT NULL REFERENCES Household(House_ID),
    Meter_Number          VARCHAR(30)   NOT NULL,
    Previous_Reading      DECIMAL(10,2) NOT NULL,
    Current_Reading       DECIMAL(10,2) NOT NULL,
    Units_Consumed        DECIMAL(10,2) NOT NULL,
    Reading_Date          DATE          NOT NULL,
    Previous_Reading_Date DATE          NOT NULL,
    Bill_ID               INTEGER       REFERENCES Electricity_Bill(Bill_ID),
    CHECK (Current_Reading >= Previous_Reading),
    CHECK (Reading_Date > Previous_Reading_Date)
);

CREATE INDEX IF NOT EXISTS idx_meter_house_date ON EB_Meter (House_ID, Reading_Date);
