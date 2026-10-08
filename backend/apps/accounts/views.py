from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import ChangePasswordSerializer, LoginSerializer, MeSerializer


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class MeView(generics.RetrieveUpdateAPIView):
    """Current user; the interface language, e-mail and phone are editable here."""

    serializer_class = MeSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        if "language" in serializer.validated_data:
            serializer.save(language_auto=False)
        else:
            serializer.save()


class ChangePasswordView(generics.GenericAPIView):
    """Any signed-in user changes their own password; the current one is required."""

    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)
