import uuid
from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q

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

        files = CloudFile.objects.filter(
            Q(user=request.user) | Q(shared_with=request.user)
        ).distinct()
        serializer = CloudFileSerializer(files, many=True, context={'request': request})
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

        serializer = CloudFileSerializer(cloud_file, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)



class FileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        cloud_file = get_object_or_404(CloudFile, Q(pk=pk) & (Q(user=request.user) | Q(shared_with=request.user)))

        cloud_file.last_download_date = timezone.now()
        cloud_file.save()

        try:
            file_data = minio_client.get_object(settings.MINIO_BUCKET_NAME, cloud_file.minio_object_name)
            response = HttpResponse(file_data.read())
            response['Content-Disposition'] = f'attachment; filename="{cloud_file.file_name}"'
            return response
        finally:
            file_data.close()
            file_data.release_conn()

    def delete(self, request, pk):
        cloud_file = get_object_or_404(CloudFile, Q(pk=pk) & (Q(user=request.user) | Q(shared_with=request.user)))

        if cloud_file.user == request.user:
            minio_client.remove_object(settings.MINIO_BUCKET_NAME, cloud_file.minio_object_name)
            cloud_file.delete()
            return Response({"mesaj": "Dosya sahibi tarafından kalıcı olarak silindi."},
                            status=status.HTTP_204_NO_CONTENT)
        else:
            cloud_file.shared_with.remove(request.user)
            return Response({"mesaj": "Dosyanın sizinle olan paylaşımı kaldırıldı."}, status=status.HTTP_204_NO_CONTENT)



class FileShareView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        cloud_file = get_object_or_404(CloudFile, pk=pk, user=request.user)
        username_to_share = request.data.get("username")

        if not username_to_share:
            return Response({"error": "Lütfen 'username' belirtin."}, status=status.HTTP_400_BAD_REQUEST)

        if username_to_share == request.user.username:
            return Response({"error": "Dosyayı kendinizle paylaşamazsınız."}, status=status.HTTP_400_BAD_REQUEST)

        user_to_share = get_object_or_404(User, username=username_to_share)
        cloud_file.shared_with.add(user_to_share)

        return Response({"mesaj": f"Dosya '{username_to_share}' kullanıcısıyla başarıyla paylaşıldı."},
                        status=status.HTTP_200_OK)

    def delete(self, request, pk):
        cloud_file = get_object_or_404(CloudFile, pk=pk, user=request.user)
        username_to_unshare = request.data.get("username")

        if not username_to_unshare:
            return Response({"error": "Lütfen paylaşımdan kaldırmak istediğiniz 'username' bilgisini belirtin."},
                            status=status.HTTP_400_BAD_REQUEST)

        user_to_unshare = get_object_or_404(User, username=username_to_unshare)

        if user_to_unshare in cloud_file.shared_with.all():
            cloud_file.shared_with.remove(user_to_unshare)
            return Response({"mesaj": f"'{username_to_unshare}' kullanıcısının bu dosyaya erişim yetkisi kaldırıldı."},
                            status=status.HTTP_200_OK)

        return Response({"error": "Dosya zaten bu kullanıcıyla paylaşılmamış."}, status=status.HTTP_400_BAD_REQUEST)