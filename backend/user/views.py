from django.contrib.auth import login
from knox import views as knox_views
from knox.models import AuthToken
from rest_framework import permissions, status
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import CustomHeaderTokenAuthentication
from .serializers import UserRegisterSerializer, UserSettingsSerializer


class LoginView(knox_views.LoginView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, format=None):
        serializer = AuthTokenSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        return super(LoginView, self).post(request, format=None)


class UserRegisterView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        data = {}
        if serializer.is_valid():
            account = serializer.save()
            data["username"] = account.username
            token = AuthToken.objects.create(user=account)[1]
            data["token"] = token
            return Response(data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(knox_views.LogoutView):
    authentication_classes = (CustomHeaderTokenAuthentication,)


class LogoutAllView(knox_views.LogoutAllView):
    authentication_classes = (CustomHeaderTokenAuthentication,)


class UserDetailsView(RetrieveUpdateDestroyAPIView):
    serializer_class = UserSettingsSerializer
    parser_classes = (MultiPartParser, JSONParser)

    def get_object(self):
        return self.request.user

    def delete(self, *args, **kwargs):
        self.skip_actor_from_logging = True
        return super().delete(*args, **kwargs)
