from rest_framework import serializers
from django.contrib.auth.models import User
from .models import CloudFile

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        return user

class CloudFileSerializer(serializers.ModelSerializer):
    is_owner = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source='user.username', read_only=True)
    shared_with = serializers.SlugRelatedField(many=True, slug_field='username', read_only=True)

    class Meta:
        model = CloudFile
        fields = ['id', 'file_name', 'upload_date', 'last_download_date', 'is_owner', 'owner_username', 'shared_with']

    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.user == request.user
        return False