# Overview

This is a Korean vacation management system (휴가관리시스템) built for "SS Power Corporation" (에스에스전력). The system allows employees to request vacation time and enables administrators to manage employee vacation requests, holidays, and employment certificates. The application is built using Flask and is designed to be deployed on cloud platforms like Railway or Render.

# System Architecture

The application follows a traditional Flask web application architecture with the following key components:

## Backend Architecture
- **Framework**: Flask 2.2.5 with SQLAlchemy for database operations
- **Authentication**: Flask-Login for session management
- **Forms**: WTForms with Flask-WTF for form handling and validation
- **Templates**: Jinja2 templating engine with responsive design using Tailwind CSS

## Database Architecture
- **Primary Database**: PostgreSQL (with SQLite fallback for development)
- **ORM**: SQLAlchemy with declarative base model
- **Connection Management**: Connection pooling with automatic reconnection

## Frontend Architecture
- **CSS Framework**: Tailwind CSS for responsive design
- **JavaScript**: Vanilla JavaScript with Alpine.js for interactive components
- **UI Components**: Custom components with government-style theming
- **Icons**: Font Awesome 6.0 for iconography

# Key Components

## User Management
- **Role-based Access Control**: Two main roles (Employee and Admin)
- **Authentication System**: Username/password with secure password hashing
- **User Registration**: Self-registration with department/position selection

## Vacation Management
- **Vacation Requests**: Employees can submit vacation requests with date ranges
- **Approval Workflow**: Administrators can approve/reject requests
- **Holiday Management**: System tracks Korean national holidays
- **Vacation Calculation**: Automatic calculation excluding weekends and holidays

## Document Generation
- **Employment Certificates**: PDF generation using ReportLab
- **Word Documents**: Document generation using python-docx
- **Template System**: Customizable document templates

## Data Import/Export
- **Excel Integration**: Bulk employee import via Excel files using pandas/openpyxl
- **CSV Export**: Export vacation data for reporting
- **Template Downloads**: Sample file templates for bulk operations

# Data Flow

## Vacation Request Flow
1. Employee submits vacation request through web form
2. System validates dates and calculates business days
3. Request stored in database with "pending" status
4. Administrator reviews and approves/rejects request
5. System updates vacation balances automatically

## Authentication Flow
1. User submits credentials via login form
2. System validates against stored password hash
3. Flask-Login manages session state
4. Role-based redirects to appropriate dashboard

## Document Generation Flow
1. User/Admin initiates document request
2. System retrieves relevant data from database
3. Template engine generates document (PDF/Word)
4. Document served as download or stored for later access

# External Dependencies

## Core Dependencies
- **Flask 2.2.5**: Web framework
- **SQLAlchemy 2.0.29**: Database ORM
- **psycopg2-binary 2.9.9**: PostgreSQL adapter
- **Werkzeug 2.2.3**: WSGI utilities

## Document Processing
- **python-docx 0.8.11**: Word document generation
- **reportlab 4.1.0**: PDF generation
- **Pillow 10.2.0**: Image processing
- **weasyprint 59.0**: Alternative PDF generation

## Data Processing
- **pandas 2.1.4**: Excel file processing
- **openpyxl 3.1.2**: Excel file handling
- **xlrd 2.0.1**: Excel file reading

## Deployment
- **gunicorn 21.2.0**: WSGI server for production
- **System dependencies**: Font packages for PDF generation (via apt.txt)

# Deployment Strategy

## Cloud Platform Support
- **Railway**: Configured with railway.json for automatic deployment
- **Render**: Separate requirements file for Render-specific dependencies
- **Database**: PostgreSQL with automatic URL conversion from postgres:// to postgresql://

## Production Configuration
- **WSGI Server**: Gunicorn with single worker configuration
- **Static Files**: Served directly by Flask in development
- **Environment Variables**: Database URL and session secrets via environment
- **Health Checks**: Root path health check endpoint

## Database Management
- **Automatic Migration**: Tables created automatically on startup
- **Connection Pooling**: Configured for production reliability
- **Backup Strategy**: Relies on cloud provider database backups

# Changelog

- June 29, 2025. Initial setup

# User Preferences

Preferred communication style: Simple, everyday language.