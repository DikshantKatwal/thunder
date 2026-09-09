from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from user.serializers import UserSerializer
# Create your views here.



class MyDetailAPIView(RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


# from dj_rest_auth.registration.views import SocialLoginView
# from social_core.backends.google import GoogleOAuth2

# class GoogleLoginAPIView(SocialLoginView):
#     adapter_class = GoogleOAuth2