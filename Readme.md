# 🚀 Flask Backend for Stock Trading Application

This README provides instructions for setting up and running the Flask backend for the stock trading application.

## 📋 Prerequisites
- 🐍 **Python** 3.7 or higher
- 📦 **pip** (Python package installer)

## 🛠️ Installation
1. Clone the repository (if you haven't already): 
   ```bash
   git clone <repository-url> 
   cd <project-directory>

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt

## 💾 Prisma Setup
1. Ensure you have the Prisma CLI installed:: 
   ```bash
   pip install prisma

2. Set up your database connection:
- Open the prisma/schema.prisma file.
- Verify that the database connection string is correct in the datasource block:
   ```bash
    datasource db {
    provider = "postgresql"
    url      = env("DATABASE_URL")
    }
3. Create a .env file in the root directory of your project and add your database URL:
   ```bash
    DATABASE_URL="postgresql://username:password@localhost:5432/your_database"
    // Replace username, password, localhost, 5432, and your_database with your actual database credentials.
4. Generate the Prisma client:
   ```bash
    prisma generate
5. Apply the database schema:
   ```bash
    prisma db push

## Running Backend Server
   ```
   python app.py

- The server should start running on http://127.0.0.1:5000/.

## 📡 API Endpoints
- GET /api/portfolio: Fetch the user's portfolio 📈
- POST /api/buy: Buy stocks 🛒
- POST /api/sell: Sell stocks 💼
- GET /api/trade-history: Get trade history 📜

## 🌐 Environment Variables
Ensure the following environment variables are set:
- DATABASE_URL: Your PostgreSQL database connection string 🗄️
- FLASK_ENV: Set to development for development mode 🛠️

## 🛑 Troubleshooting
- If you encounter database connection issues, double-check your DATABASE_URL in the .env file.
- For Prisma-related issues, try running prisma generate again. ⚙️

## 📝 Additional Notes
- This backend uses the yfinance library to fetch real-time stock data. Ensure you have a stable internet connection 🌐.
- The application uses Prisma as an ORM. Refer to the Prisma documentation for advanced database operations 📚.
