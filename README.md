# Categorization and Analytics Dashboard

A Flask dashboard over personal transaction data, with automatic category suggestions that learn from corrections.

The project transforms raw financial transaction data into an interactive PostgreSQL-backed analytics application. It combines transaction categorization, relational database design, analytical SQL, Python, Flask, and HTMX to turn transaction-level data into useful financial insights.

## Overview

This project was built to explore the process of transforming raw financial transaction data into a structured analytical application.

The application:

1. Processes financial transaction data
2. Categorizes transactions into income, expense, and transfer classes
3. Stores the data in a PostgreSQL relational database
4. Uses SQL queries to calculate financial metrics
5. Exposes analytical results through reusable Python functions
6. Provides an interactive dashboard for analyzing spending, budgets, and financial trends
7. Provides a transactions page for viewing, filtering, searching, and managing transaction data
8. Uses transaction corrections to improve future category suggestions

---

## Dashboard

The dashboard provides a high-level overview of personal spending and budget performance.

### Key Performance Indicators

The dashboard includes:

* **Total Spending**
* **Budget Remaining**
* **Budget Used**
* **Projected Month-End Spending**
* **Month-over-Month Spending Change**

The dashboard can be filtered by time period and category, allowing the displayed metrics and visualizations to update based on the selected data.

### Spending Analysis

The dashboard provides:

* Monthly spending trends
* Spending by category
* Category-level spending comparisons
* Budget versus actual spending
* Monthly financial performance

Budget visualizations indicate whether spending is:

* Within the allocated budget
* Approaching the budget limit
* Over budget

---

## Automatic Transaction Categorization

The application includes transaction categorization functionality designed to reduce manual categorization work.

Transactions can be categorized based on transaction descriptions and existing categorization patterns. When a category is corrected, that correction can be used to improve future category suggestions.

This creates a feedback loop:

```text
Transaction
     ↓
Category Suggestion
     ↓
User Correction
     ↓
Stored Categorization Pattern
     ↓
Improved Future Suggestions
```

---

## Analytical Queries

The dashboard is powered by analytical SQL queries that transform transaction-level records into financial metrics.

### Spending by Category

Aggregates expense transactions by category and ranks categories by total spending.

### Spending by Month

Groups expense transactions by month to identify spending trends over time.

### Budget vs. Actual

Compares actual spending against monthly budget targets by category.

This allows the application to identify:

* Categories within budget
* Categories approaching their budget
* Categories exceeding their budget

### Net Cash Flow

Calculates monthly income, expenses, and net cash flow:

```text
Net Cash Flow = Income - Expenses
```

### SQL Techniques Used

The project uses:

* Aggregate functions
* `CASE` expressions
* `COALESCE`
* Common Table Expressions (CTEs)
* Date formatting and monthly aggregation
* Parameterized queries

---

## Database Design

The application uses PostgreSQL as its relational database.

### Categories

Stores category information and the broader transaction classification.

| Column              | Description                  |
| ------------------- | ---------------------------- |
| `category_id`       | Primary key                  |
| `category_name`     | Category name                |
| `transaction_class` | Income, Expense, or Transfer |

### Budgets

Stores monthly budget amounts associated with expense categories.

| Column           | Description        |
| ---------------- | ------------------ |
| `category_id`    | Category reference |
| `category_name`  | Category name      |
| `monthly_budget` | Budget amount      |

### Transactions

Stores individual financial transactions.

| Column             | Description             |
| ------------------ | ----------------------- |
| `transaction_id`   | Primary key             |
| `transaction_date` | Date of transaction     |
| `amount`           | Transaction amount      |
| `description`      | Transaction description |
| `transaction_type` | Type of transaction     |
| `category_id`      | Category reference      |
| `transaction_code` | Transaction identifier  |

The database uses relationships between transactions, categories, and budgets to support the analytical queries powering the dashboard.

---

## Application Architecture

Database logic is separated from the web application layer.

Analytical queries are defined in `queries.py`, while Flask routes retrieve the results and pass them to the templates used to render the dashboard.

HTMX is used for interactive page updates, allowing portions of the page to update without requiring a complete page reload.

The application follows this general architecture:

```text
Database
    ↓
SQL Analytical Queries
    ↓
Python Query Layer
    ↓
Flask Routes
    ↓
Jinja Templates
    ↓
HTMX Interactions
    ↓
Dashboard UI
```

---

## Technology Stack

### Backend

* **Python**
* **Flask**
* **psycopg2**
* **Jinja2**

### Database

* **PostgreSQL**

### Frontend

* **HTML**
* **CSS**
* **HTMX**

### Development Tools

* **Docker**
* **Docker Compose**
* **Git**
* **GitHub**

---

## Project Structure

```text
Categorization-and-Analytics-Dashboard/
│
├── docker-compose.yml
├── requirements.txt
├── README.md
│
└── src/
    │
    ├── main.py
    ├── queries.py
    ├── schema.py
    ├── seed.py
    │
    ├── db/
    │   └── connection.py
    │
    ├── entities/
    │   ├── budgets.py
    │   ├── categories.py
    │   └── transactions.py
    │
    └── web/
        │
        ├── app.py
        ├── sample_data.py
        │
        ├── static/
        │   └── css/
        │       └── styles.css
        │
        └── templates/
            ├── base.html
            ├── dashboard.html
            ├── transactions.html
            │
            └── partials/
```

---

## Running

Requires [Docker](https://www.docker.com/) with Docker Compose.

Start the application and database:

```bash
docker compose up -d --build
```

Then open:

http://localhost:5000/

### Check the Database Connection

```bash
docker compose exec app python main.py check
```

### Shut Down

```bash
docker compose down
```

### Shut Down and Delete the Data Volume

```bash
docker compose down -v
```

> **Warning:** `docker compose down -v` deletes the PostgreSQL data volume.

PostgreSQL is published on `localhost:5432`, so the code can also run outside Docker against the same database. See [`src/README.md`](src/README.md) for the local Python workflow.

---

## Local Development

The application can also be run outside Docker using a Python virtual environment.

From the project root:

```bash
python -m venv .venv
```

Activate the environment on Windows:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start PostgreSQL:

```bash
docker compose up -d
```

Then follow the instructions in [`src/README.md`](src/README.md).

The Flask application can be started from the `src/` directory with:

```bash
flask --app web.app run --debug
```

---

## Future Improvements

Potential future improvements include:

* Dashboard layout
* User authentication and multiple user accounts
* Automated importing of financial data
* Improved transaction categorization using machine learning
* More flexible date-range filtering
* Recurring transaction detection
* More advanced spending forecasts
* Additional financial metrics

---

## Project Status

This project is complete as a functional personal finance analytics dashboard and serves as a portfolio project demonstrating experience with:

```text
Python
SQL
PostgreSQL
Database Design
Data Analysis
Flask
HTMX
HTML/CSS
Dashboard Development
```

The project was built as an end-to-end application to practice turning raw transaction data into a usable analytical product.
