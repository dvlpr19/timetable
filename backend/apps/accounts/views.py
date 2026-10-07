from rest_framework import generics
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import LoginSerializer, MeSerializer


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class MeView(generics.RetrieveUpdateAPIView):
    """Current user; only the interface language is editable here."""

    serializer_class = MeSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        if "language" in serializer.validated_data:
            serializer.save(language_auto=False)
        else:
            serializer.save()
