import os
from django.conf import settings
import pandas as pd
from django.core.management.base import BaseCommand
from library.models import Book, Genre

class Command(BaseCommand):
    help = 'Import books from Excel file'

    def handle(self, *args, **kwargs):
        # Correct path to Excel file in project root's import_data folder
        file_path = os.path.join(settings.BASE_DIR, 'import_data', 'sample_books.xlsx')
        
        # Read the Excel file
        df = pd.read_excel(file_path)

        for _, row in df.iterrows():
            # Build full path to image
            image_path = os.path.join(settings.MEDIA_ROOT, row['image'])

            # Use default if file doesn't exist
            if not os.path.isfile(image_path):
                row['image'] = 'bookimage/default.jpg'

            # Create Book instance
            book = Book.objects.create(
                name=row['name'],
                author=row['author'],
                isbn=row['isbn'],
                description=row.get('description', 'Description'),
                publication_date=row['publication_date'],
                publisher=row['publisher'],
                editor=row['editor'],
                edition=row['edition'],
                language=row['language'],
                pages=row['pages'],
                image=row['image'],
                category=row['category'],
                quantity=row.get('quantity', 1),
                available_quantity=row.get('available_quantity', 1),
            )

            # Link genres
            genres = [g.strip() for g in row['genres'].split(',') if g.strip()]
            for genre_name in genres:
                genre, _ = Genre.objects.get_or_create(name=genre_name)
                book.genres.add(genre)

        self.stdout.write(self.style.SUCCESS('✅ Books imported successfully!'))
