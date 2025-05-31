from django.shortcuts import render, redirect, get_object_or_404, HttpResponse, HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.urls import reverse
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from datetime import date
from django.db import transaction # Import transaction for potentially atomic saves
from LibraryManagementSystem import settings
from . import forms, models # Assuming forms.py is in the same app directory
from .forms import StudentForm
# Import necessary models
from .models import Book, Student, IssuedBook, Hold, Genre, User

# Helper function to check if a user is a student (based on having a related Student object)
def is_student(user):
    return hasattr(user, 'student')

def index(request):
    # Display books on the index page
    return render(request, "index2.html")

@login_required(login_url='/student_login/') # Redirect to student login if not logged in
def book_list(request):
    # Display books on the index page
    books = Book.objects.all()
    return render(request, "student/book_list.html", {"books": books})

@login_required(login_url='/admin_login')
def add_book(request):
    if request.method == "POST":
        name = request.POST.get('name')
        author = request.POST.get('author')
        isbn = request.POST.get('isbn')
        category = request.POST.get('category') # Consider using a ForeignKey for category
        description = request.POST.get('description', 'Description')
        publication_date = request.POST.get('publication_date') # Added from model
        publisher = request.POST.get('publisher') # Added from model
        editor = request.POST.get('editor') # Added from model
        edition = request.POST.get('edition') # Added from model
        language = request.POST.get('language') # Added from model
        pages = request.POST.get('pages') # Added from model
        # Genres (Many-to-Many) will need to be handled separately after creating the book

        image = None
        if 'image' in request.FILES:
            image = request.FILES['image']

        # Get or create Genre objects
        # Assuming genres are submitted as a list of names or IDs
        genre_names = request.POST.getlist('genres') # Assuming multiple genres can be selected
        genres = []
        for genre_name in genre_names:
             genre, created = Genre.objects.get_or_create(name=genre_name)
             genres.append(genre)

        try:
            # When adding a book, initialize quantity and available_quantity
            book = Book.objects.create(
                name=name,
                author=author,
                isbn=isbn,
                category=category, # Again, consider ForeignKey
                description=description,
                publication_date=publication_date,
                publisher=publisher,
                editor=editor,
                edition=edition,
                language=language,
                pages=pages,
                image=image,
                quantity=request.POST.get('quantity', 1), # Allow setting quantity from form, default to 1
                available_quantity=request.POST.get('quantity', 1) # Initially available quantity is total quantity
            )
            book.genres.set(genres) # Set the many-to-many relationship
            messages.success(request, "Book added successfully!")
            # Redirect to a new book form or book list
            return redirect('add_book') # Stay on the add book page for another entry
            # Or redirect to view_books: return redirect('view_books')

        except Exception as e:
            messages.error(request, f"Failed to add book: {e}")

    # Fetch existing genres to display in the form
    genres = Genre.objects.all()
    return render(request, "admin_temp/addBook.html", {'genres': genres})


@login_required(login_url='/admin_login/') # Requires admin login - ensure this URL name/path is correct
def edit_book(request, book_id):
    """ Displays the form to edit a specific book's details. """
    user = request.user

    # --- Check to ensure the logged-in user is a superuser (admin) ---
    if not user.is_superuser:
        messages.error(request, "You do not have administrative privileges.")
        return redirect('dash') # Or redirect('admin_login')
    # --- End of check ---

    book = get_object_or_404(Book, id=book_id)
    # Fetch all genres to display in the form for selection
    genres = Genre.objects.all() # This correctly fetches genres
    # Pass 'book' and 'genres' to the template context
    return render(request, "admin_temp/edit_book.html", {'book': book, 'genres': genres})


@login_required(login_url='/admin_login/') # Requires admin login
def edit_book_save(request):
    """ Handles the POST request to save edited book details. """
    user = request.user

    # --- Check to ensure the logged-in user is a superuser (admin) ---
    if not user.is_superuser:
        messages.error(request, "You do not have administrative privileges.")
        return redirect('dash') # Or redirect('admin_login')
    # --- End of check ---

    if request.method != "POST":
        messages.error(request, "Method not allowed for this URL.")
        return redirect('dash') # Redirect if not a POST request

    # Use Django's transaction to ensure changes are atomic
    try:
        with transaction.atomic():
            book_id = request.POST.get('book_id') # Get book_id from the hidden input
            if not book_id:
                 messages.error(request, "Book ID is missing.")
                 return redirect('view_books') # Redirect if book_id is missing

            book = get_object_or_404(Book, id=book_id)

            # Get data from the form
            book.name = request.POST.get('name')
            book.author = request.POST.get('author')
            # Decided to allow ISBN to be editable based on the form structure
            book.isbn = request.POST.get('isbn')
            book.description = request.POST.get('description', '') # Use empty string default
            book.publication_date = request.POST.get('publication_date')
            book.publisher = request.POST.get('publisher')
            book.editor = request.POST.get('editor')
            book.edition = request.POST.get('edition')
            book.language = request.POST.get('language')
            book.pages = request.POST.get('pages')

            # --- Handle Quantity Update and Validation ---
            quantity_str = request.POST.get('quantity')
            available_quantity_str = request.POST.get('available_quantity')

            try:
                quantity = int(quantity_str) if quantity_str else 0
                available_quantity = int(available_quantity_str) if available_quantity_str else 0

                if available_quantity > quantity:
                     messages.error(request, "Available quantity cannot exceed total quantity.")
                     # Re-render the edit form with the book data (before saving)
                     # We need to pass genres here as well for the dropdown/checkboxes
                     genres = Genre.objects.all() # Fetch genres again
                     return render(request, 'admin_temp/edit_book.html', {'book': book, 'genres': genres}) # Pass data and genres

                book.quantity = quantity
                book.available_quantity = available_quantity

            except (ValueError, TypeError):
                 messages.error(request, "Quantity and Available Quantity must be valid numbers.")
                 # Re-render the edit form with the book data (before saving)
                 genres = Genre.objects.all() # Fetch genres again
                 return render(request, 'admin_temp/edit_book.html', {'book': book, 'genres': genres}) # Pass data and genres
            # --- End Quantity Update and Validation ---


            # Handle image update
            if 'image' in request.FILES:
                # Optional: Delete old image before assigning new one if replacing
                # if book.image and hasattr(book.image, 'url'):
                #      try:
                #          from django.core.files.storage import default_storage
                #          if default_storage.exists(book.image.path):
                #              default_storage.delete(book.image.path)
                #      except Exception as delete_error:
                #          print(f"Error deleting old image for book {book.id}: {delete_error}")

                book.image = request.FILES['image']

            # Save the Book object first to ensure it has an ID before setting ManyToMany
            book.save()

            # Update Genres (Many-to-Many)
            genre_names = request.POST.getlist('genres') # Get the list of selected genre names
            genres_to_set = []
            # Find the actual Genre objects based on the submitted names
            for genre_name in genre_names:
                 try:
                     genre = Genre.objects.get(name=genre_name)
                     genres_to_set.append(genre)
                 except Genre.DoesNotExist:
                     # Handle case where a submitted genre name doesn't exist
                     print(f"Warning: Submitted genre name '{genre_name}' does not exist.")
                     pass # Optionally, add a message or log this

            # Set the ManyToMany relationship - This replaces all existing genres with the selected ones
            book.genres.set(genres_to_set)


        # If we reach here, all updates within the transaction were successful
        messages.success(request, f"Book '{book.name}' updated successfully!")
        # Redirect to the book detail page (assuming 'book_detail' is the URL name)
        return redirect('book_detail', book_id=book.id) # Redirect to the detail page

    except Exception as e:
        # If any error occurred during the atomic transaction or before
        messages.error(request, f"Failed to update book: {e}")
        # Redirect back to the edit page with the book ID so they can try again
        # This redirect pattern requires the edit_book URL to accept book_id
        return redirect('edit_book', book_id=book.id) # Redirect back to the edit form



@login_required(login_url='/admin_login')
def view_books(request):
    books = Book.objects.all()
    return render(request, "admin_temp/books.html", {'books': books})

# Added book_detail view
# @login_required(login_url='/login/') # Example if login is required for all
@login_required
def book_detail(request, book_id):
    """ Displays details of a specific book, tailored for admin or student. """
    book = get_object_or_404(Book, id=book_id)

    # --- Check if the logged-in user is an admin (superuser) ---
    if request.user.is_superuser:
        # User is an admin, render the admin book detail template

        # Fetch currently issued copies of this book for the admin view
        issued_copies = IssuedBook.objects.filter(book=book, book_status='Active').select_related('student__user')

        admin_context = {
            'book': book,
            'issued_copies': issued_copies, # Pass issued copies to admin template
            # No need for active_holds or user_has_hold in the admin view context usually
        }
        # Render the admin-specific template
        return render(request, 'admin_temp/admin_book_detail.html', admin_context)

    # --- User is not an admin (must be a logged-in non-superuser) ---
    else:
        # User is a logged-in non-superuser (presumably a student)
        # Add variable to check if the user is a student
        is_student_user = hasattr(request.user, 'student')

        # Fetch active holds for this book if you want to display the queue (for students)
        # Only fetch if the user is actually a student
        active_holds = []
        user_has_hold = False
        if is_student_user:
            active_holds = Hold.objects.filter(book=book, is_active=True).order_by('place_date').select_related('student__user')
            # Determine if the logged-in student has an active hold on this book
            user_has_hold = Hold.objects.filter(book=book, student=request.user.student, is_active=True).exists()


        student_context = {
            'book': book,
            'active_holds': active_holds, # Pass active holds to student template
            'user_has_hold': user_has_hold, # Pass user_has_hold to student template
            'is_student_user': is_student_user, # Pass is_student_user
        }
        # Render the student-specific template
        # Replace 'student/book_detail.html' with the actual path to your student book detail template
        return render(request, 'student/book_detail.html', student_context)

@login_required(login_url='/admin_login')
def view_students(request):
    students = Student.objects.all()
    return render(request, "admin_temp/students.html", {'students': students})

@login_required(login_url='/admin_login')
def Search_student(request):
    q = request.GET.get('q') if request.GET.get('q') is not None else ''
    # Searching by phone, maybe add name, adm_no, etc.
    students = Student.objects.filter(
        Q(phone__icontains=q) |
        Q(user__first_name__icontains=q) |
        Q(user__last_name__icontains=q) |
        Q(adm_no__icontains=q)
        # Add more fields as needed for searching
    ).distinct() # Use distinct to avoid duplicates if a student matches multiple Q conditions
    context = {'students': students}
    return render(request, "admin_temp/students.html", context)


@login_required(login_url='/student_login/')
def Search_book(request):
    q = request.GET.get('q') if request.GET.get('q') is not None else ''
    # Searching by isbn, maybe add name, author, genre, etc.
    books = Book.objects.filter(
        Q(isbn__icontains=q) |
        Q(name__icontains=q) |
        Q(author__icontains=q) |
        Q(genres__name__icontains=q) # Searching by genre name (requires distinct)
    ).distinct() # Use distinct to avoid duplicate books if they have multiple matching genres
    context = {'books': books}
   
   
    return render(request, "student/book_list.html", context)


@login_required(login_url='/admin_login')
def Search_book_admin(request):
    q = request.GET.get('q') if request.GET.get('q') is not None else ''
    # Searching by isbn, maybe add name, author, genre, etc.
    books = Book.objects.filter(
        Q(isbn__icontains=q) |
        Q(name__icontains=q) |
        Q(author__icontains=q) |
        Q(genres__name__icontains=q) # Searching by genre name (requires distinct)
    ).distinct() # Use distinct to avoid duplicate books if they have multiple matching genres
    context = {'books': books}
    return render(request, "admin_temp/books.html", context)



# @login_required(login_url='/admin_login')
def returned(request, pk):
    """ Marks an issued book as returned and notifies the next student on hold if any. """
    issued_book = get_object_or_404(IssuedBook, id=pk)
    book = issued_book.book # Get the related Book object

    # --- Update IssuedBook status to 'Returned' ---
    issued_book.book_status = "Returned"
    # You might want to record the actual return date here if you added a field for it
    # issued_book.return_date = date.today()
    issued_book.save()
    # --- End Update IssuedBook status ---

    # --- Increase the available quantity of the book ---
    book.available_quantity = book.available_quantity + 1
    book.save()
    messages.success(request, f"Book '{book.name}' marked as Returned. Available quantity updated.")
    # --- End Increase available quantity ---


    # --- Check for the next active hold and notify the student ---
    # Find the oldest active hold for this specific book
    next_hold = Hold.objects.filter(book=book, is_active=True).order_by('place_date').first()

    if next_hold:
        student_on_hold = next_hold.student
        student_email = student_on_hold.user.email
        book_title = book.name

        if student_email: # Only send notification if the student has an email
            subject = f"Book Available: '{book_title}' is Ready for Pickup"
            message = (
                f"Hello {student_on_hold.user.first_name},\n\n"
                f"Good news! The book '{book_title}' that you placed on hold is now available for pickup.\n\n"
                "Please visit the library within [Specify Pickup Period, e.g., 3 days] to borrow the book.\n\n" # Add info about pickup period
                "If you do not pick up the book within the specified period, your hold may be cancelled.\n\n"
                "Thank you,\n"
                "Your Library Team" # Replace with your library name
            )
            from_email = settings.DEFAULT_FROM_EMAIL # Use the default sender email from settings
            recipient_list = [student_email]

            try:
                # --- Send the email notification ---
                send_mail(subject, message, from_email, recipient_list)
                messages.info(request, f"Notification email sent to {student_email} (student on hold).")

                # --- Mark the hold as inactive after notification ---
                # You might want to change this logic later to give them a pickup window
                # But for a basic implementation, marking inactive after notification is fine
                next_hold.is_active = False
                next_hold.save()
                messages.info(request, f"Hold for {student_on_hold.user.username} on '{book_title}' has been marked inactive.")

            except Exception as e:
                 messages.error(request, f"Failed to send notification email to {student_email}: {e}")
                 # Consider adding logging here to track failed emails

        else:
            messages.warning(request, f"Book available for {student_on_hold.user.username} on hold, but no email address available to send notification.")
            # You might still want to mark the hold inactive here if you don't have other notification methods

    else:
        messages.info(request, f"No active holds found for '{book.name}'.")
    # --- End Check for hold and notify ---

    # Redirect back to the view issued books page (or wherever appropriate)
    return redirect('view_issued_book') # Or redirect to the book detail page, etc.

@login_required(login_url='/admin_login')
def not_returned(request, id):
    """ Reverts the status of an issued book to Active (if it was marked returned by mistake). """
    # This might need more careful handling to decrement available_quantity if it was incremented
    # when the book was incorrectly marked as returned.
    issued_book = get_object_or_404(IssuedBook, id=id)
    book = issued_book.book

    if issued_book.book_status == "Returned":
         # If it was marked returned, decrement available_quantity as we are reverting the status
         book.available_quantity -= 1
         book.save()

    issued_book.book_status = "Active"
    # issued_book.returned_date = None # Reset returned date if you add that field
    issued_book.save()
    messages.warning(request, f"Book '{book.name}' status set back to Active.")
    return HttpResponseRedirect(reverse("view_issued_book"))


@login_required(login_url='/admin_login')
def issue_book(request):
    # Use the updated IssueBookForm
    form = forms.IssueBookForm()
    if request.method == "POST":
        form = forms.IssueBookForm(request.POST)
        if form.is_valid():
            # Get the selected Book and Student objects directly from the cleaned form data
            selected_book = form.cleaned_data['book']
            selected_student = form.cleaned_data['student']

            try:
                # --- Checks before issuing (uses the book object) ---
                if selected_book.available_quantity <= 0:
                    messages.error(request, f"Book '{selected_book.name}' is not available for issuing.")
                    # Pass the form and relevant context back to the template
                    students = Student.objects.all() # Need this for the student dropdown if not using ModelForm
                    books = Book.objects.filter(available_quantity__gt=0) # Need this for book dropdown if not using ModelForm
                    return render(request, "admin_temp/issueBook.html", {'form': form, 'students': students, 'books': books})

              
                active_hold = Hold.objects.filter(book=selected_book, student=selected_student, is_active=True).order_by('place_date').first()
                if active_hold:
                    # If the student had an active hold, mark it as completed or inactive
                    active_hold.is_active = False # Or add a status like 'Completed'
                    active_hold.save()
                    messages.info(request, f"Hold for '{selected_book.name}' by {selected_student.user.username} has been fulfilled.")

                # If checks pass, create the IssuedBook entry
                issued_book = models.IssuedBook.objects.create(
                    student=selected_student, # Use the student object
                    book=selected_book,     # Use the book object
                    book_status="Active" # Set initial status
                    # expiry_date is handled by the default in the model
                )

                # Decrement the available quantity of the book
                selected_book.available_quantity -= 1
                selected_book.save()

                messages.success(request, f"Book '{selected_book.name}' issued to {selected_student.user.username}.")
                # Redirect to view issued books or stay on the form
                return redirect('issue_book') # Stay on the issue book page for another entry
                # Or redirect to view_issued_book: return redirect('view_issued_book')

            except Exception as e:
                messages.error(request, f"An error occurred: {e}")
                import logging
                logging.exception("Error issuing book")
                # Pass the form and context back to the template on error
                students = Student.objects.all()
                books = Book.objects.filter(available_quantity__gt=0)
                return render(request, "admin_temp/issueBook.html", {'form': form, 'students': students, 'books': books})
        else:
            messages.error(request, "Invalid form data.")
            # Pass the form and context back to the template on invalid form
            students = Student.objects.all()
            books = Book.objects.filter(available_quantity__gt=0)
            return render(request, "admin_temp/issueBook.html", {'form': form, 'students': students, 'books': books})

    # If GET request or form is invalid, render the form
    # You'll need to pass students and books to the template for the form fields
    students = Student.objects.all()
    books = Book.objects.filter(available_quantity__gt=0) # Only show books with available copies
    return render(request, "admin_temp/issueBook.html", {'form': form, 'students': students, 'books': books})

@login_required(login_url='/student_login')
def cancel_hold(request, hold_id):
    """ Allows a student to cancel their active hold. """
    user = request.user

    # Ensure the user is a student
    if not hasattr(user, 'student'):
        messages.error(request, "You do not have a student account.")
        return redirect('index') # Redirect to a safe page

    student = user.student

    # Get the hold object or return 404 if it doesn't exist
    # Also ensure the hold belongs to the logged-in student and is active
    try:
        hold = Hold.objects.get(id=hold_id, student=student, is_active=True)
    except Hold.DoesNotExist:
        messages.error(request, "Hold not found or cannot be cancelled.")
        return redirect('my_holds') # Redirect back to the My Holds page

    # --- Cancel the hold ---
    hold.is_active = False # Mark the hold as inactive instead of deleting
    hold.save()
    # Alternatively, you could delete the hold: hold.delete()
    # Marking as inactive retains a history of holds placed.

    messages.success(request, f"Your hold on '{hold.book.name}' has been cancelled.")

    return redirect('my_holds') # Redirect back to the My Holds page

@login_required(login_url='/admin_login')
def view_issued_book(request):
    """ Displays a list of all issued books for admin. """
    user = request.user

    if not user.is_superuser:
        messages.error(request, "You do not have administrative privileges.")
        return redirect('dash')

    # Fetch all IssuedBook objects, optimizing queries for related data
    issued_books = IssuedBook.objects.all().select_related('student__user', 'book').order_by('-issued_date') # Order by most recently issued

    today = date.today()
    # Calculate days overdue for each issued book in Python
    # Add a boolean flag for 'is_overdue' and the 'days_overdue' count
    for issued_book in issued_books:
        if issued_book.book_status == 'Active' and issued_book.expiry_date < today:
            issued_book.is_overdue = True
            delta = today - issued_book.expiry_date
            issued_book.days_overdue = delta.days
        else:
            issued_book.is_overdue = False
            issued_book.days_overdue = 0 # Or None, but 0 is simpler for display

    context = {'issuedBooks': issued_books}
    return render(request, "admin_temp/issued_books.html", context)

@login_required(login_url='/admin_login') # Requires admin login
def available_books_report(request):
    """ Displays a report of all books that are currently available. """
    user = request.user

    # --- Check to ensure the logged-in user is a superuser (admin) ---
    if not user.is_superuser:
        messages.error(request, "You do not have administrative privileges.")
        return redirect('dash') # Or redirect('admin_login')
    # --- End of check ---

    # Find Book objects where available_quantity is greater than 0
    available_books = Book.objects.filter(
        available_quantity__gt=0
    ).order_by('name') # Order by book title

    context = {
        'available_books': available_books,
        # 'today': date.today(), # Include if you want to display the report date
    }
    return render(request, 'admin_temp/available_books_report.html', context) # We will create this template next


# In your views.py

# ... (your existing imports) ...
from datetime import date # Make sure date is imported


@login_required(login_url='/admin_login') # Requires admin login
def dash(request):
    user_count = User.objects.all().count()
    student_count = Student.objects.all().count()
    books_count = Book.objects.all().count()
    issued_books_count = IssuedBook.objects.filter(book_status='Active').count() # Count active issues
    holds_count = Hold.objects.filter(is_active=True).count() # Count active holds

    # --- Calculate Overdue Count ---
    today = date.today()
    overdue_count = IssuedBook.objects.filter(
        book_status='Active',
        expiry_date__lt=today
    ).count()
    # --- End Calculate Overdue Count ---

    return render(request, "admin_temp/dash.html", {
        "user_count": user_count,
        'books_count': books_count,
        'issued_books_count': issued_books_count,
        "student_count": student_count,
        "holds_count": holds_count,
        'overdue_count': overdue_count, # <-- Pass the new count to the template
    })

# ... (rest of your views) ...


@login_required(login_url='/admin_login') # Requires admin login
def overdue_books_report(request):
    """ Displays a report of all currently overdue issued books. """
    user = request.user

    # --- Check to ensure the logged-in user is a superuser (admin) ---
    if not user.is_superuser:
        messages.error(request, "You do not have administrative privileges.")
        return redirect('dash') # Or redirect('admin_login')
    # --- End of check ---

    today = date.today()

    # Find IssuedBook objects that are Active and whose expiry date is before today
    # Annotate the queryset with the number of days overdue
    overdue_issues = IssuedBook.objects.filter(
        book_status='Active',
        expiry_date__lt=today
    ).annotate(
        # Calculate days overdue: (Today - Expiry Date) in days
        # Use F() expression for database-level calculation
        # Note: This requires Django 2.1+ and database support for date subtraction
        # An alternative is to calculate it in Python after fetching, but that's less efficient for large lists
        # Let's calculate in Python for compatibility
        # days_overdue=Now() - F('expiry_date') # Django 2.1+ example annotation
    ).select_related('student__user', 'book').order_by('expiry_date')

    # Calculate days overdue in Python for compatibility
    for issue in overdue_issues:
        delta = today - issue.expiry_date
        issue.days_overdue = delta.days # Add a new attribute to the issue object

    context = {
        'overdue_issues': overdue_issues,
        'today': today,
    }
    return render(request, 'admin_temp/overdue_books_report.html', context)

@login_required(login_url='/admin_login') # Requires admin login
def admin_view_holds(request):
    """ Displays a list of all holds for administrative viewing. """
    user = request.user

    # --- Check to ensure the logged-in user is a superuser (admin) ---
    if not user.is_superuser:
        messages.error(request, "You do not have administrative privileges.")
        # Redirect to admin dashboard or admin login
        return redirect('dash') # Or redirect('admin_login')
    # --- End of check ---

    # Fetch all Hold objects, ordered by place date (or status, depending on preference)
    all_holds = Hold.objects.all().select_related('book', 'student__user').order_by('-is_active', 'place_date')
    # .select_related() improves performance by fetching related objects in one query
    # .order_by('-is_active', 'place_date') orders active holds first, then by place date

    context = {
        'all_holds': all_holds
    }
    return render(request, 'admin_temp/view_holds.html', context) # We will create this template next

@login_required(login_url='/student_login')
def student_issued_books(request):
    """ View for students to see their issued books. """
    # Get the student object for the logged-in user
    try:
        student = request.user.student
    except Student.DoesNotExist:
        messages.error(request, "User is not a student.")
        return redirect('index') # Redirect to a safe page

    # Get issued books for this student, optimizing queries
    issued_books = IssuedBook.objects.filter(student=student).select_related('book')

    # The complex loop to build 'li1' is removed, you can access related objects directly in the template
    return render(request, 'student/books.html', {'issuedBooks': issued_books})

# Added the my_holds view
@login_required(login_url='/student_login') # Ensure only logged-in students can access
def my_holds(request):
    """ Displays the active holds for the logged-in student. """
    user = request.user

    # Ensure the user is a student
    if not hasattr(user, 'student'):
        messages.error(request, "You do not have a student account.")
        return redirect('index') # Redirect to a safe page

    student = user.student

    # Get all active holds for this student, ordered by the date they were placed
    active_holds = Hold.objects.filter(student=student, is_active=True).order_by('place_date')

    context = {
        'active_holds': active_holds
    }
    return render(request, 'student/my_holds.html', context) # We will create/update this template

# Added the place_hold view
@login_required(login_url='/student_login')
def place_hold(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    user = request.user

    # Ensure the user is a student
    if not hasattr(user, 'student'):
        messages.error(request, "Only students can place holds.")
        # You might want to redirect to student login or the index page if not a student
        return redirect('book_detail', book_id=book.id)
    student = user.student

    # --- Add checks before placing the hold ---

    # Check if the book is available (no need for a hold if available)
    if book.available_quantity > 0:
        messages.info(request, f"Book '{book.name}' is currently available. No need to place a hold.")
        return redirect('book_detail', book_id=book.id)

    # Check if the student already has an active hold on this book
    existing_hold = Hold.objects.filter(book=book, student=student, is_active=True).exists()
    if existing_hold:
        messages.info(request, f"You already have an active hold on '{book.name}'.")
        return redirect('book_detail', book_id=book.id)

    # Optional: Check if the student currently has this book issued
    # You might not want them to place a hold if they already have a copy
    # current_issue = IssuedBook.objects.filter(book=book, student=student, book_status='Active').exists()
    # if current_issue:
    #     messages.info(request, f"You currently have '{book.name}' issued.")
    #     return redirect('book_detail', book_id=book.id)


    # If checks pass, create the hold
    Hold.objects.create(book=book, student=student, is_active=True) # Ensure is_active is True by default
    messages.success(request, f"A hold has been placed on '{book.name}'.")

    return redirect('book_detail', book_id=book.id)


@login_required(login_url='/student_login')
def profile(request):
    # Fetch the student object for the logged-in user
    try:
        student = request.user.student
    except Student.DoesNotExist:
        messages.error(request, "User is not a student.")
        return redirect('index') # Redirect to a safe page

    return render(request, "student/studentHome.html", {'student': student})


@login_required(login_url='/student_login/') # Requires student login - ensure this URL name/path is correct
def edit_student_profile(request): # Renamed function to match template/URL convention
    """ Handles editing the logged-in student's profile. """
    user = request.user

    # --- Check to ensure the logged-in user is a student ---
    # Using hasattr is generally cleaner than try/except for OneToOneFields
    if not hasattr(user, 'student'):
        messages.error(request, "You must be logged in as a student to edit your profile.")
        # Redirect to a safe page, like the student login or index
        return redirect('student_login') # Or redirect('index')
    # --- End of check ---

    student = user.student # Get the related Student object

    if request.method == 'POST':
        # Get data from the form (matching the names in your edit_profile.html template)
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        branch = request.POST.get('branch')
        classroom = request.POST.get('classroom')
        address = request.POST.get('address') # Field from model/template
        guardian_name = request.POST.get('guardian_name') # Field from model/template
        guardian_phone = request.POST.get('guardian_phone') # Field from model/template
        image = request.FILES.get('image') # Get the image file

        # --- Use Django's transaction to ensure both saves succeed or fail together ---
        try:
            with transaction.atomic():
                # --- Update User Model Fields ---
                # Validate email if necessary (Django's User model does some validation on save)
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.save()
                # --- End Update User Model Fields ---

                # --- Update Student Model Fields ---
                student.phone = phone
                student.branch = branch
                student.classroom = classroom
                student.address = address # Update address
                student.guardian_name = guardian_name # Update guardian name
                student.guardian_phone = guardian_phone # Update guardian phone

                # Handle image upload
                if image:
                    # Optional: Delete old image before assigning new one if replacing
                    # if student.image and hasattr(student.image, 'url'): # Check if image exists and has a URL
                    #      try:
                    #          # Ensure the file actually exists before attempting deletion
                    #          from django.core.files.storage import default_storage
                    #          if default_storage.exists(student.image.path):
                    #              default_storage.delete(student.image.path)
                    #      except Exception as delete_error:
                    #          # Log the deletion error but don't stop the save process
                    #          print(f"Error deleting old image for student {student.id}: {delete_error}")

                    student.image = image # Assign the new image file

                # Note: adm_no is not updated here as it's usually not student editable
                # total_fines is also not updated here

                student.save()
                # --- End Update Student Model Fields ---

            # If we reach here, both saves were successful
            messages.success(request, "Your profile has been updated successfully.")
            # Redirect back to the student profile display page (assuming 'student_profile' is the URL name)
            return redirect('profile') # Ensure this URL name is correct

        except Exception as e:
            # If any error occurred during the atomic transaction, changes are rolled back
            messages.error(request, f"Failed to update profile: {e}")
            # Render the edit page again with the data that was attempted to be saved (before rollback)
            # Pass both user and student objects to the template
            return render(request, "student/edit_profile.html", {'user': user, 'student': student}) # Use correct template name and context


    else: # GET request - Display the form with current data
        # Data is automatically available in the template via 'user' and 'student' objects
        pass # No extra data fetching needed for GET

    # Render the edit profile template for GET requests or POST failures
    # Pass both user and student objects to the template
    return render(request, "student/edit_profile.html", {'user': user, 'student': student}) # Use correct template name and context


@login_required(login_url='/admin_login')
def delete_book(request, myid):
    """ Deletes a book. Consider implications for issued books and holds. """
    book = get_object_or_404(Book, id=myid)
    # Before deleting a book, you might want to check if it has active issues or holds
    if IssuedBook.objects.filter(book=book, book_status='Active').exists():
        messages.error(request, f"Cannot delete book '{book.name}' as it has active issues.")
        return redirect("view_books")
    if Hold.objects.filter(book=book, is_active=True).exists():
         messages.error(request, f"Cannot delete book '{book.name}' as it has active holds.")
         return redirect("view_books")

    try:
        book.delete()
        messages.success(request, f"Book '{book.name}' deleted successfully.")
    except Exception as e:
        messages.error(request, f"Failed to delete book '{book.name}': {e}")

    return redirect("view_books")

@login_required(login_url='/admin_login')
def delete_student(request, myid):
    """ Deletes a student. Consider implications for issued books and fines. """
    student = get_object_or_404(Student, id=myid)
    # Before deleting a student, you might want to check if they have active issues or holds
    if IssuedBook.objects.filter(student=student, book_status='Active').exists():
        messages.error(request, f"Cannot delete student '{student.user.username}' as they have active issues.")
        return redirect("view_students")
    if Hold.objects.filter(student=student, is_active=True).exists():
         messages.error(request, f"Cannot delete student '{student.user.username}' as they have active holds.")
         return redirect("view_students")
    # Also consider outstanding fines

    try:
        # Deleting the Student object will also delete the related User object due to CASCADE
        student.delete()
        messages.success(request, f"Student '{student.user.username}' deleted successfully.")
    except Exception as e:
        messages.error(request, f"Failed to delete student '{student.user.username}': {e}")

    return redirect("view_students")

@login_required(login_url='/admin_login')
def delete_issued(request, id):
    """ Deletes an issued book entry. Should increment available quantity. """
    issued_book = get_object_or_404(IssuedBook, id=id)
    book = issued_book.book

    try:
        # If the issued book was active, increment available quantity before deleting
        if issued_book.book_status == 'Active':
             book.available_quantity += 1
             book.save()

        issued_book.delete()
        messages.success(request, "Issued book entry deleted successfully.")
    except Exception as e:
        messages.error(request, f"Failed to delete issued book entry: {e}")

    return redirect("view_issued_book")


def change_password(request):
    # This view seems fine for changing the logged-in user's password
    if request.method == "POST":
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')

        # Basic validation
        if not current_password or not new_password:
             messages.error(request, "Please fill in all fields.")
             return render(request, "student/changepsw.html")

        user = request.user # Use request.user for the currently logged-in user

        if user.check_password(current_password):
            user.set_password(new_password)
            user.save()
            messages.success(request, "Password changed successfully!")
            # Consider logging the user out after password change for security
            # logout(request)
            # return redirect('login_url') # Redirect to login page
            return render(request, "student/changepsw.html") # Or redirect to profile
        else:
            messages.error(request, "Incorrect current password.")
            return render(request, "student/changepsw.html")

    return render(request, "student/changepsw.html")

def student_registration(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        branch = request.POST.get('branch')
        classroom = request.POST.get('classroom')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        image = request.FILES.get('image')

        # Validation
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            Student.objects.create(
                user=user,
                phone=phone,
                branch=branch,
                classroom=classroom,
                image=image
            )

            messages.success(request, "Student registered successfully.")
            return redirect('student_login')

    # Branch and classroom options
    branches = [
        ('CSE', 'Computer Science'),
        ('ECE', 'Electronics'),
        ('ME', 'Mechanical'),
        ('CE', 'Civil'),
    ]
    classrooms = [
        ('A', 'Class A'),
        ('B', 'Class B'),
        ('C', 'Class C'),
    ]

    return render(request, "student/register.html", {
        "branches": branches,
        "classrooms": classrooms
    })

@csrf_exempt
def check_email_exist(request):
    if request.method == "POST":
        email = request.POST.get("email")
        exists = User.objects.filter(email=email).exists()
        return JsonResponse({'exists': exists})
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
def check_username_exist(request):
    if request.method == "POST":
        username = request.POST.get("username")
        exists = User.objects.filter(username=username).exists()
        return JsonResponse({'exists': exists})
    return JsonResponse({'error': 'Invalid request method'}, status=400)


def student_login(request):
    """ Handles student login. """
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)

        if user is not None:
            # Check if the user is associated with a Student profile
            if hasattr(user, 'student'):
                login(request, user)
                messages.success(request, f"Welcome, {user.first_name}!")
                return redirect("profile") # Redirect to the student profile page
            else:
                messages.error(request, "You do not have a student account.")
        else:
            messages.error(request, "Invalid username or password.")

    # If GET request or authentication failed
    return render(request, "student/login.html")

def admin_login(request):
    """ Handles admin/superuser login. """
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password) # Use request in authenticate

        if user is not None:
            # Check if the user is a superuser
            if user.is_superuser:
                login(request, user)
                # --- Modified welcome message logic ---
                if user.first_name and user.last_name:
                    messages.success(request, f"Welcome, {user.first_name} {user.last_name}!") # Use full name
                elif user.first_name:
                    messages.success(request, f"Welcome, {user.first_name}!") # Use first name
                else:
                    messages.success(request, "Welcome, Admin!") # Generic welcome
                # --- End modified welcome message logic ---
                return redirect("dash") # Redirect to the admin dashboard
            else:
                messages.error(request, "You do not have administrator privileges.")
        else:
            messages.error(request, "Invalid username or password.")

    # If GET request or authentication failed
    # Ensure the template name is correct (you used 'admin_temp/login.html')
    return render(request, "admin_temp/login.html")


def Logout(request):
    """ Logs out the current user. """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("index") # Redirect to the homepage"

@login_required(login_url='/student_login/') # Requires student login
def student_dash(request):
    """ Displays the dashboard for a logged-in student. """
    user = request.user

    # --- Check to ensure the logged-in user is a student ---
    if not hasattr(user, 'student'):
        messages.error(request, "You must be logged in as a student to access this page.")
        return redirect('index') # Redirect to index or student login if not a student
    # --- End of check ---

    student = user.student # Get the related Student object

    # Calculate counts specific to this student
    # Count active issued books for this student
    student_issued_books_count = IssuedBook.objects.filter(student=student, book_status='Active').count()

    # Count active holds for this student
    student_holds_count = Hold.objects.filter(student=student, is_active=True).count()

    context = {
        'student_issued_books_count': student_issued_books_count,
        'student_holds_count': student_holds_count,
        'student': student, # Pass the student object to the template
        'user': user, # Pass the user object as well
    }
    # We will create the student_dash.html template next
    return render(request, 'student/student_dashboard.html', context)