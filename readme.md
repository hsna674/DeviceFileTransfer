# Device File Transfer

A simple Flask web application for secure file uploads, downloads, and management per user. Each user has their own upload directory, and authentication is required for all file operations.

## Features
- User authentication (login/signup)
- Upload files (per user)
- Download files
- Delete files
- Flash messages for user feedback
- Admin and user separation

## Requirements
- Python 3.7+
- Flask
- SQLite3

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/hsna674/DeviceFileTransfer.git
   cd DeviceFileTransfer
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**
   ```bash
   python main.py
   ```
   The app will be available at `http://127.0.0.1:5000/`.

## File Structure
- `main.py` - Main Flask application
- `requirements.txt` - Python dependencies
- `users.db` - SQLite database for user accounts
- `templates/` - HTML templates (login, signup, dashboard)
- `uploads/` - Uploaded files, organized by user

## Usage
- Sign up for a new account or log in with existing credentials.
- Upload, download, or delete your files from the dashboard.
- Admin users have a separate upload directory.
- Access your files from any device using the same account.

## Security Notes
- Each user has a separate upload folder.
- Authentication is required for all file operations.


