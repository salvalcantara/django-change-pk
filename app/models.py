from django.db import models

class Author(models.Model):
    id = models.IntegerField(unique=True, null=True)
    name = models.CharField(max_length=30, primary_key=True)

    def __unicode__(self):
        return self.name

class Article(models.Model):
    title = models.CharField(max_length=140)
    authors = models.ManyToManyField(Author, related_name='articles')

    def __unicode__(self):
        return self.title
