# Data Dictionary - Personal Transactions Dataset

This document defines all the tables in the project.

---

## transactions

| Column Name | Data Type | Description | Example |
|-------------|----------|-------------|---------|
| transaction_date | DATE | Date the transaction occurred | 2018 |
| amount | NUMERIC(10, 2) | Cost of purchase | 1247.44 |
| description | TEXT | Description of payment | Thai Restaurant |
| transaction_type | TEXT | Indicates whether the transaction is a credit or debit | debit |
| category_id | INTEGER | Unique id for each category | 21 |
| transaction_code | TEXT | Simulated transaction codes | SHELL OIL #K1CGPZ |


## budgets

| Column Name | Data Type | Description | Example |
|-------------|----------|-------------|---------|
| category_name | TEXT | Name of spending category | Auto Insurance |
| monthly_budget | NUMERIC(10, 2) | Planned monthly spending limit for the category  | 15 |
| category_id | INTEGER | Unique id for each category | 21 |


## categories

| Column Name | Data Type | Description | Example |
|-------------|----------|-------------|---------|
| category_name | TEXT | Name of spending category | Auto Insurance |
| transaction_class | TEXT | Classification of the category: Expense, Income, or Transfer. | Transfer |
| category_id | INTEGER | Unique id for each category | 21 |
