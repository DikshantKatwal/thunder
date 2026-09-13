from rest_framework.generics import  CreateAPIView, GenericAPIView
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.response import Response
from staff.models import Staff, StaffInvitation
from staff.serializers import CreateStaffSerializer, StaffInvitationSerializer, StaffInvitationSerializer, StaffSerializer, UseStaffInvitationSerializer
from rest_framework.views import  APIView
from rest_framework import viewsets



class InviteStaffViewSet(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StaffInvitationSerializer



class AcceptInviteLink(APIView):
    permission_classes = [AllowAny]
    serializer_class = StaffInvitationSerializer


    def post(self, request, *args, **kwargs):
        invitation = StaffInvitation.objects.filter(token=request.data.get("token",None)).first()
        if not invitation:
            return Response("Invitation not valid.", status=400)
        serializer = self.serializer_class(invitation)
        return Response(serializer.data)


class CreateInvitedUserStaff(CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = UseStaffInvitationSerializer


    def post(self, request, *args, **kwargs):
        invitation = StaffInvitation.objects.filter(token=request.data.get("token",None),accepted_at__isnull=True).first()
        if not invitation:
            return Response("Invitation not valid.", status=400)
        serializer = self.get_serializer(invitation, data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data)



class StaffViewSet(viewsets.ModelViewSet):
    """
    CRUD for Staff
    """

    serializer_class = StaffSerializer
    permission_classes = [IsAuthenticated]
    queryset = Staff.objects.all()
    search_fields = [
        "user__given_name",
    ]


    def get_serializer_class(self):
        if self.action == "create":
            return CreateStaffSerializer
        return super().get_serializer_class()