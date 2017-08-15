from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=30, unique=True)

    def __unicode__(self):
        return self.name


class Article(models.Model):
    title = models.CharField(max_length=140)
    authors = models.ManyToManyField(Author, related_name='articles')

    def __unicode__(self):
        return self.title
