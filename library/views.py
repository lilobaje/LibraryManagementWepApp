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
from datetime import date
from . import forms, models # Assuming forms.py is in the same app directory
from .forms import StudentForm
# Import necessary models
from .models import Book, Student, IssuedBook, Hold, Genre, User

# Helper function to check if a user is a student (based on having a related Student object)
def is_student(user):
    return hasattr(user, 'student')

def index(request):
    # Display books on the index page
    books = Book.objects.all()
    return render(request, "index2.html", {"books": books})

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


@login_required(login_url='/admin_login')
def edit_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    # Fetch all genres to display in the form for selection
    genres = Genre.objects.all()
    return render(request, "admin_temp/edit_book.html", {'book': book, 'genres': genres})


@login_required(login_url='/admin_login')
def edit_book_save(request):
    if request.method != "POST":
        return HttpResponse("Method Not Allowed")
    else:
        book_id = request.POST.get('book_id') # Assume you pass book_id in a hidden input
        book = get_object_or_404(Book, id=book_id)

        book.name = request.POST.get('name')
        book.author = request.POST.get('author')
        # Decide if ISBN should be editable after creation
        # book.isbn = request.POST.get('isbn')
        book.category = request.POST.get('category') # Consider using a ForeignKey
        book.description = request.POST.get('description', 'Description')
        book.publication_date = request.POST.get('publication_date')
        book.publisher = request.POST.get('publisher')
        book.editor = request.POST.get('editor')
        book.edition = request.POST.get('edition')
        book.language = request.POST.get('language')
        book.pages = request.POST.get('pages')

        # Handle image update
        if 'image' in request.FILES:
            book.image = request.FILES['image']

        # Update Genres (Many-to-Many)
        genre_names = request.POST.getlist('genres')
        genres = []
        for genre_name in genre_names:
             genre, created = Genre.objects.get_or_create(name=genre_name)
             genres.append(genre)
        book.genres.set(genres)

        # Decide if quantity should be editable here or only through issue/return
        # book.quantity = request.POST.get('quantity', book.quantity)
        # Recalculate available_quantity if quantity is edited directly (complex)
        # It's often simpler to manage quantity only via issue/return

        try:
            book.save()
            messages.success(request, "Book updated successfully!")
            return redirect('view_books') # Redirect to the book list after saving
        except Exception as e:
            messages.error(request, f"Failed to update book: {e}")
            # Redirect back to the edit page or view books
            return redirect('edit_book', book_id=book.id)


def dash(request):
    user_count = User.objects.all().count()
    student_count = Student.objects.all().count()
    books_count = Book.objects.all().count()
    issued_books_count = IssuedBook.objects.filter(book_status='Active').count() # Count active issues
    holds_count = Hold.objects.filter(is_active=True).count() # Count active holds

    return render(request, "admin_temp/dash.html", {
        "user_count": user_count,
        'books_count': books_count,
        'issued_books_count': issued_books_count,
        "student_count": student_count,
        "holds_count": holds_count,
    })


@login_required(login_url='/admin_login')
def view_books(request):
    books = Book.objects.all()
    return render(request, "admin_temp/books.html", {'books': books})

# Added book_detail view
def book_detail(request, book_id):
    """ Displays the details of a specific book. """
    book = get_object_or_404(Book, id=book_id)

    # --- Add variable to check if the user is a student ---
    is_student_user = False
    if request.user.is_authenticated:
        is_student_user = hasattr(request.user, 'student')
    # --- End added variable ---

    # Fetch active holds for this book if you want to display the queue
    active_holds = Hold.objects.filter(book=book, is_active=True).order_by('place_date')

    # Determine if the logged-in user has an active hold on this book
    user_has_hold = False
    if request.user.is_authenticated and is_student_user: # Use the new variable here too
         user_has_hold = Hold.objects.filter(book=book, student=request.user.student, is_active=True).exists()


    context = {
        'book': book,
        'active_holds': active_holds,
        'user_has_hold': user_has_hold,
        'is_student_user': is_student_user, # <-- Pass the new variable to the template
    }
    return render(request, 'book_detail.html', context)

@login_required(login_url='/admin_login')
def view_students(request):
    students = Student.objects.all()
    return render(request, "admin_temp/students.html", {'students': students})


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
    return render(request, "admin_temp/books.html", context)


def returned(request, id):
    """ Handles the return of an issued book. """
    issued_book = get_object_or_404(IssuedBook, id=id)
    book = issued_book.book # Get the related Book object

    # Update the status of the issued book
    issued_book.book_status = "Returned"
    # Set the returned date (add a returned_date field to IssuedBook model)
    # issued_book.returned_date = date.today() # Requires 'from datetime import date'
    issued_book.save()

    # Increment the available quantity of the book
    book.available_quantity += 1
    book.save()

    # --- Hold System Integration (Check for holds and notify the next person) ---
    # Find the oldest active hold for this book
    next_hold = Hold.objects.filter(book=book, is_active=True).order_by('place_date').first()

    if next_hold:
        # You would implement a notification system here (e.g., sending an email)
        # For now, let's just mark the hold as inactive (or delete it) and maybe add a message
        # Instead of marking inactive here, you might transition the hold status
        # or delete it upon successful notification and subsequent issue.
        messages.info(request, f"Book '{book.name}' returned. {next_hold.student.user.username} was next in the hold queue.")
        # Consider creating a new model/system for managing hold notifications or using a task queue


    messages.success(request, f"Book '{book.name}' marked as returned.")
    return HttpResponseRedirect(reverse("view_issued_book"))


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

                # Optional: Check if the student has too many books issued
                # issued_count = IssuedBook.objects.filter(student=selected_student, book_status='Active').count()
                # if issued_count >= MAX_BOOKS_PER_STUDENT: # Define MAX_BOOKS_PER_STUDENT in settings
                #     messages.error(request, f"{selected_student.user.username} has reached the maximum number of issued books.")
                #     students = Student.objects.all()
                #     books = Book.objects.filter(available_quantity__gt=0)
                #     return render(request, "admin_temp/issueBook.html", {'form': form, 'students': students, 'books': books})

                # Optional: Check if the student has outstanding fines preventing issue
                # if selected_student.total_fines > 0:
                #      messages.error(request, f"{selected_student.user.username} has outstanding fines.")
                #      students = Student.objects.all()
                #      books = Book.objects.filter(available_quantity__gt=0)
                #      return render(request, "admin_temp/issueBook.html", {'form': form, 'students': students, 'books': books})

                # --- Check for active holds and potentially remove the oldest one for this student/book ---
                # If a student is being issued a book they had on hold, you might remove their hold here
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
    """ View for admins/librarians to see all issued books. """
    issued_books = IssuedBook.objects.all().select_related('student__user', 'book') # Optimize queries
    # The complex loop to build 'details' is removed, you can access related objects directly in the template
    return render(request, "admin_temp/issued_books.html", {'issuedBooks': issued_books})


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
@login_required
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


@login_required(login_url='/student_login')
def edit_profile(request):
    """ Allows students to edit their profile information. """
    try:
        student = request.user.student
    except Student.DoesNotExist:
        messages.error(request, "User is not a student.")
        return redirect('index') # Redirect to a safe page

    if request.method == "POST":
        # Be cautious about which fields students can edit.
        # Avoid letting them change core User fields like username or email directly this way.
        # It's better to use Django Forms for validation and cleaner handling.

        # Updating User fields (handle with care or use a User Update Form)
        # request.user.email = request.POST.get('email') # Consider using EmailField in Student or User model
        # request.user.save()

        student.phone = request.POST.get('phone')
        student.branch = request.POST.get('branch')
        student.classroom = request.POST.get('classroom')
        student.adm_no = request.POST.get('roll_no') # Mismatch with model field name 'adm_no' vs 'roll_no'
        # Handle image update
        if 'image' in request.FILES:
             student.image = request.FILES['image']

        try:
            student.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile') # Redirect back to the profile page
        except Exception as e:
            messages.error(request, f"Failed to update profile: {e}")
            # Redirect back to the edit page with current data
            return render(request, "student/edit.html", {'student': student}) # Pass student object

    # If GET request, display the current profile data in the form
    return render(request, "student/edit.html", {'student': student})


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
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            password = data.get('password')
            confirm_password = data.get('confirm_password')

            if password != confirm_password:
                messages.error(request, "Passwords do not match.")
            elif User.objects.filter(username=data['username']).exists():
                messages.error(request, "Username already exists.")
            elif User.objects.filter(email=data['email']).exists():
                messages.error(request, "Email already exists.")
            else:
                user = User.objects.create_user(
                    username=data['username'],
                    email=data['email'],
                    password=password,
                    first_name=data['first_name'],
                    last_name=data['last_name']
                )

                # Create Student profile
                Student.objects.create(
                    user=user,
                    phone=data['phone'],
                    branch=data['branch'],
                    classroom=data['classroom'],
                    image=request.FILES.get('image')
                )

                messages.success(request, "Student registered successfully.")
                return redirect('student_login')  # ✅ Fixed redirect
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = StudentForm()

    icons = {
        form['first_name']: "fa fa-user",
        form['last_name']: "fa fa-user",
        form['username']: "fa fa-user-tag",
        form['email']: "fa fa-envelope",
        form['phone']: "fa fa-phone",
        form['branch']: "fa fa-school",
        form['classroom']: "fa fa-chalkboard-teacher",
        form['image']: "fa fa-image",
        form['password']: "fa fa-lock",
        form['confirm_password']: "fa fa-lock",
    }

    return render(request, "new_student_regform.html", {"form": form, "fields": icons})

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
        user = authenticate(username=username, password=password)

        if user is not None:
            # Check if the user is a superuser
            if user.is_superuser:
                login(request, user)
                messages.success(request, f"Welcome, Admin {user.username}!")
                return redirect("dash") # Redirect to the admin dashboard
            else:
                messages.error(request, "You do not have administrator privileges.")
        else:
            messages.error(request, "Invalid username or password.")

    # If GET request or authentication failed
    return render(request, "admin_temp/login.html")


def Logout(request):
    """ Logs out the current user. """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("index") # Redirect to the homepage"