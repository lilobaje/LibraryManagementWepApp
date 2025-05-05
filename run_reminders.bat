@echo off

REM Change to your project directory
cd C:\Path\to\Your\LibraryManagementWepApp

REM Activate your virtual environment
REM Adjust the path to match your env directory and activation script
call env\Scripts\activate

REM Run the Django management command
REM You can add >> logfile.txt 2>&1 to redirect output to a log file
python manage.py send_expiry_reminders

REM Deactivate virtual environment (optional but good practice)
deactivate

REM Exit the batch file
exit /b %errorlevel%