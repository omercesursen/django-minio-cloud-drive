import uuid
from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.contrib.auth.models import User

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from .models import CloudFile
from .serializers import RegisterSerializer, CloudFileSerializer
from .utils import minio_client


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer


class FileListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        files = CloudFile.objects.filter(user=request.user)
        serializer = CloudFileSerializer(files, many=True)
        return Response(serializer.data)

    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "Lütfen bir dosya gönderin."}, status=status.HTTP_400_BAD_REQUEST)

        unique_name = f"{request.user.id}_{uuid.uuid4()}_{file_obj.name}"

        minio_client.put_object(
            bucket_name=settings.MINIO_BUCKET_NAME,
            object_name=unique_name,
            data=file_obj,
            length=file_obj.size,
            content_type=file_obj.content_type
        )

        cloud_file = CloudFile.objects.create(
            user=request.user,
            file_name=file_obj.name,
            minio_object_name=unique_name
        )

        serializer = CloudFileSerializer(cloud_file)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        return get_object_or_404(CloudFile, pk=pk, user=user)

    def get(self, request, pk):
        cloud_file = self.get_object(pk, request.user)
        cloud_file.last_download_date = timezone.now()
        cloud_file.save()

        try:
            file_data = minio_client.get_object(
                settings.MINIO_BUCKET_NAME,
                cloud_file.minio_object_name
            )
            response = HttpResponse(file_data.read())
            response['Content-Disposition'] = f'attachment; filename="{cloud_file.file_name}"'
            return response
        finally:
            file_data.close()
            file_data.release_conn()

    def delete(self, request, pk):
        cloud_file = self.get_object(pk, request.user)
        minio_client.remove_object(settings.MINIO_BUCKET_NAME, cloud_file.minio_object_name)
        cloud_file.delete()
        return Response({"mesaj": "Dosya başarıyla silindi."}, status=status.HTTP_204_NO_CONTENT)