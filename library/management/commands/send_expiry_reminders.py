# your_app_name/management/commands/send_expiry_reminders.py

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from library.models import IssuedBook # Import your IssuedBook model
from django.core.mail import send_mail
from django.conf import settings # Import settings to get email configuration

class Command(BaseCommand):
    help = 'Sends email reminders for books nearing their expiry date.'

    def handle(self, *args, **options):
        # Define how many days before expiry to send the reminder
        REMINDER_DAYS = 3 # Send reminder 3 days before expiry

        # Calculate the date threshold for reminders
        reminder_threshold = timezone.now().date() + timedelta(days=REMINDER_DAYS)

        # Find IssuedBook objects that are Active and expire within the reminder threshold
        # Also exclude books that have already passed the expiry date (they are overdue, not nearing expiry)
        books_nearing_expiry = IssuedBook.objects.filter(
            book_status='Active',
            expiry_date__lte=reminder_threshold, # Expiry date is on or before the threshold
            expiry_date__gte=timezone.now().date() # Expiry date is today or in the future
        ).select_related('student__user', 'book') # Optimize queries

        self.stdout.write(self.style.SUCCESS(f"Found {books_nearing_expiry.count()} books nearing expiry."))

        # --- This is where you would send the actual emails ---
        # For now, we'll just print information to the console
        for issued_book in books_nearing_expiry:
            student_email = issued_book.student.user.email
            book_title = issued_book.book.name
            expiry_date = issued_book.expiry_date

            if student_email: # Only send if the student has an email address
                subject = f"Reminder: Your Library Book '{book_title}' is Due Soon"
                message = (
                    f"Hello {issued_book.student.user.first_name},\n\n"
                    f"This is a reminder that the book '{book_title}' you borrowed is due on {expiry_date}.\n\n"
                    "Please return the book by the due date to avoid fines.\n\n"
                    "Thank you,\n"
                    "Your Library Team" # Replace with your library name
                )
                from_email = settings.DEFAULT_FROM_EMAIL # Use the default sender email from settings
                recipient_list = [student_email]

                # --- For now, print the email details instead of sending ---
                # self.stdout.write(f"--- Email to: {student_email} ---")
                # self.stdout.write(f"Subject: {subject}")
                # self.stdout.write(f"Message:\n{message}")
                # self.stdout.write("-----------------------------")
                # --- End print instead of send ---

                # --- To send actual emails, uncomment the line below and comment out the print block ---
                try:
                    send_mail(subject, message, from_email, recipient_list)
                    self.stdout.write(self.style.SUCCESS(f"Successfully sent reminder email to {student_email}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to send reminder email to {student_email}: {e}"))


        self.stdout.write(self.style.SUCCESS('Expiry reminder command finished.'))