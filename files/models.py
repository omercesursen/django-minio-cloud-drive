from django.db import models
from django.contrib.auth.models import User


class CloudFile(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)


    file_name = models.CharField(max_length=255)


    minio_object_name = models.CharField(max_length=255, unique=True)


    upload_date = models.DateTimeField(auto_now_add=True)
    last_download_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.file_name}"