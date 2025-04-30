from django.db import models
from django.contrib.auth.models import User
from datetime import datetime,timedelta
import time


class Genre(models.Model):
    name = models.CharField(max_length=100 )

    def __str__(self):
        return self.name


class Book(models.Model):
    name = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    isbn = models.PositiveIntegerField()
    description = models.TextField(default='Description')
    publication_date = models.CharField(max_length=200)
    publisher = models.CharField(max_length=200)
    editor = models.CharField(max_length=200)
    edition = models.CharField(max_length=200)
    language = models.CharField(max_length=200)
    pages = models.CharField(max_length=200)
    image = models.ImageField(upload_to='bookimage/')
    category = models.CharField(max_length=50)
    genres = models.ManyToManyField(Genre)

    def __str__(self):
        return str(self.name) + " ["+str(self.isbn)+']'


#This function generates an ID string that starts with the prefix "ITCH" followed 
# by a timestamp in the format of 10 digits. The timestamp is obtained by multiplying 
# the current time (in seconds) by 10,000,000 and converting it to an integer. 
# The function then returns the ID string.
def return_timestamped_id():
    prefix="ITCH"
    timestamp = str(int(time.time()*10000000))
    default_value= prefix + timestamp

    return(default_value)


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    classroom = models.CharField(max_length=10)
    branch = models.CharField(max_length=10)
    adm_no = models.CharField(max_length=3, blank=True ,default=return_timestamped_id)
    address = models.CharField(max_length=10)
    email = models.CharField(max_length=10)
    guardian_name = models.CharField(max_length=10)
    guardian_phone = models.CharField(max_length=10)
    phone = models.CharField(max_length=10, blank=True)
    image=models.ImageField(upload_to='images/')

    def __str__(self):
        return str(self.user) + " ["+str(self.branch)+']' + " ["+str(self.classroom)+']' + " ["+str(self.adm_no)+']'

#This function returns a datetime object that represents 
# the date and time 14 days in the future. 
# The function uses the datetime.today() method to get the current date and time, 
# and then adds a timedelta object representing 14 days to it. The timedelta object is created by 
# passing the number of days (14) to the timedelta() constructor. The resulting datetime object 
# represents the date and time 14 days in the future from the current date and time.
def expiry():
    return datetime.today() + timedelta(days=6)


class IssuedBook(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    isbn = models.CharField(max_length=13)
    book_status = models.CharField(max_length=14)
    issued_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField(default=expiry)
    objects = models.Manager()

