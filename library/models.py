from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import time

# This function generates an ID string that starts with the prefix "ITCH" followed
# by a timestamp in the format of 10 digits. The timestamp is obtained by multiplying
# the current time (in seconds) by 10,000,000 and converting it to an integer.
# The function then returns the ID string.
def return_timestamped_id():
    prefix="ITCH"
    timestamp = str(int(time.time()*10000000))
    default_value= prefix + timestamp
    return(default_value)

#This function returns a datetime object that represents
# the date and time 14 days in the future.
# The function uses the datetime.today() method to get the current date and time,
# and then adds a timedelta object representing 14 days to it. The timedelta object is created by
# passing the number of days (14) to the timedelta() constructor. The resulting datetime object
# represents the date and time 14 days in the future from the current date and time.
def expiry():
    return datetime.today() + timedelta(days=6)


class Genre(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Book(models.Model):
    name = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    isbn = models.PositiveIntegerField()
    description = models.TextField(default='Description')
    publication_date = models.CharField(max_length=200) # Consider using DateField or IntegerField for year
    publisher = models.CharField(max_length=200)
    editor = models.CharField(max_length=200)
    edition = models.CharField(max_length=200)
    language = models.CharField(max_length=200)
    pages = models.CharField(max_length=200) # Consider using PositiveIntegerField
    image = models.ImageField(upload_to='bookimage/')
    category = models.CharField(max_length=50) # Consider using a ForeignKey to a Category model
    genres = models.ManyToManyField(Genre)

    # Added fields for quantity tracking
    quantity = models.PositiveIntegerField(default=1) # Total number of copies
    available_quantity = models.PositiveIntegerField(default=1) # Copies currently available


    def __str__(self):
        # Updated __str__ to include quantity information
        return f"{self.name} [{self.isbn}] ({self.available_quantity}/{self.quantity} available)"


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    classroom = models.CharField(max_length=10)
    branch = models.CharField(max_length=10)
    adm_no = models.CharField(max_length=3, blank=True, default=return_timestamped_id) # adm_no max_length seems very short (3)
    address = models.CharField(max_length=10) # address max_length seems very short (10)
    email = models.CharField(max_length=10) # email max_length seems very short (10) - Consider using Django's EmailField and linking to User.email
    guardian_name = models.CharField(max_length=10) # guardian_name max_length seems very short (10)
    guardian_phone = models.CharField(max_length=10) # guardian_phone max_length seems very short (10)
    phone = models.CharField(max_length=10, blank=True) # phone max_length seems very short (10)
    image = models.ImageField(upload_to='images/')
   
    # Added field for tracking fines
    total_fines = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)


    def __str__(self):
        return str(self.user.username) + " ["+str(self.branch)+']' + " ["+str(self.classroom)+']' + " ["+str(self.adm_no)+']' # Changed to user.username


class IssuedBook(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    # Changed isbn to a ForeignKey to Book
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    # You might want to use choices for book_status or link to a Status model
    book_status = models.CharField(max_length=14)
    issued_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField(default=expiry)
    # Consider adding a returned_date field
    # returned_date = models.DateField(null=True, blank=True)

    # You might not need a custom manager unless you have specific query requirements later
    # objects = models.Manager()

    def __str__(self):
         # Updated __str__ to show book name and student username
         return f"'{self.book.name}' issued to {self.student.user.username}"


class Hold(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    place_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('book', 'student', 'is_active')
        # Order holds by place date, so the oldest hold is first
        ordering = ['place_date']

    def __str__(self):
        return f"{self.student.user.username} holds {self.book.name} (Active: {self.is_active})"