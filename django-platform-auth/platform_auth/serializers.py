from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Detailed user information serializer.
    """
    full_name = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'role', 'support_level', 'storage_quota', 'phone', 'department',
            'location', 'avatar', 'bio', 'website', 'language', 'timezone',
            'theme', 'is_active', 'email_verified', 'is_two_factor_enabled',
            'is_online', 'last_login', 'last_activity', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_login']

    def get_full_name(self, obj):
        """Get user's full name"""
        return obj.get_full_name()

    def get_is_online(self, obj):
        """Check if user is online"""
        return obj.is_online


class UserListSerializer(serializers.ModelSerializer):
    """
    Minimal user information for list views.
    """
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'full_name', 'role',
            'avatar', 'is_active', 'created_at'
        ]

    def get_full_name(self, obj):
        """Get user's full name"""
        return obj.get_full_name()


class UserProfileSerializer(serializers.ModelSerializer):
    """
    User profile serializer for profile update endpoint.
    """

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'department',
            'location', 'avatar', 'bio', 'website', 'language', 'timezone',
            'theme', 'street', 'postal_code', 'city', 'country'
        ]

    def validate_email(self, value):
        """Validate email is unique"""
        user = self.context['request'].user
        if User.objects.filter(email=value).exclude(id=user.id).exists():
            raise serializers.ValidationError('Email already exists')
        return value


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for user creation (admin).
    """
    password = serializers.CharField(write_only=True, required=True)
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'email', 'username', 'first_name', 'last_name', 'password',
            'password_confirm', 'role', 'support_level', 'is_active'
        ]

    def validate_password(self, value):
        """Validate password strength"""
        validate_password(value)
        return value

    def validate(self, data):
        """Validate password confirmation"""
        if data['password'] != data.pop('password_confirm'):
            raise serializers.ValidationError({'password': 'Passwords do not match'})
        return data

    def create(self, validated_data):
        """Create user with validated data"""
        user = User.objects.create_user(**validated_data)
        return user


class UserEditSerializer(serializers.ModelSerializer):
    """
    Serializer for user editing (admin).
    """

    class Meta:
        model = User
        fields = [
            'email', 'username', 'first_name', 'last_name', 'role',
            'support_level', 'phone', 'department', 'location', 'is_active',
            'email_verified', 'is_two_factor_enabled', 'force_password_change'
        ]

    def validate_email(self, value):
        """Validate email is unique"""
        user = self.instance
        if User.objects.filter(email=value).exclude(id=user.id).exists():
            raise serializers.ValidationError('Email already exists')
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint.
    """
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        """Validate old password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect')
        return value

    def validate_new_password(self, value):
        """Validate new password strength"""
        validate_password(value)
        return value

    def validate(self, data):
        """Validate password confirmation"""
        if data['new_password'] != data.pop('new_password_confirm'):
            raise serializers.ValidationError({'new_password': 'Passwords do not match'})
        return data

    def save(self):
        """Update password"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class PlatformTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extended token serializer with custom claims.
    """

    @classmethod
    def get_token(cls, user):
        """Add custom claims to token"""
        token = super().get_token(user)
        token['email'] = user.email
        token['username'] = user.username
        token['role'] = user.role
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        return token

    def validate(self, attrs):
        """Validate credentials"""
        data = super().validate(attrs)
        data['user'] = UserDetailSerializer(self.user).data
        return data
