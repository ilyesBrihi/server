# serializers.py
from rest_framework import serializers
from .models import Address, LawyerProfile, LawyerImage, LawyerDocument , ClientProfile , User , TimeSlot , Appointment , Review , UserProfile
from django.shortcuts import get_object_or_404
from django.db.models import Avg


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'street', 'city', 'state', 'zip_code', 'country']

class TimeSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeSlot
        fields = ['id', 'day', 'start_time', 'end_time']

class LawyerImageSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        lawyer_profile_pk = self.context['lawyer_profile_pk']
        return LawyerImage.objects.create(lawyer_id=lawyer_profile_pk, **validated_data)

    class Meta:
        model = LawyerImage
        fields = ['id', 'image']


class LawyerProfileSerializer(serializers.ModelSerializer):
    address = AddressSerializer(required=False, allow_null=True)
    time_slots = TimeSlotSerializer(required=False, allow_null=True, many=True)
    rating = serializers.SerializerMethodField()
    images= LawyerImageSerializer(many=True , read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)

    def get_rating(self, obj):
        try :
            rating_obj = Review.objects.filter(lawyer=obj).aggregate(rating=Avg('rating'))
            rating_avg = rating_obj['rating']
            if rating_avg:
                   return rating_avg
            else:
                return 0
        except:
            return 0



    class Meta:
        model = LawyerProfile
        fields = ['id', 'first_name', 'last_name', 'specialization', 'phone_number', 'bio', 'language', 'address', 'time_slots' , 'rating' , 'images' , 'image']

    def create(self, validated_data):
        address_data = validated_data.pop('address', None)
        time_slots_data = validated_data.pop('time_slots', None)

        if address_data:
            address = Address.objects.create(**address_data)
            validated_data['address'] = address

        # Save the lawyer profile first
        lawyer = LawyerProfile.objects.create(**validated_data , image = UserProfile.objects.get(user_id = validated_data['user']).image)

        if time_slots_data:
            for slot_data in time_slots_data:
                TimeSlot.objects.create(lawyer=lawyer, **slot_data)

        # Include serialized TimeSlots in the response
        lawyer_time_slots = TimeSlot.objects.filter(lawyer=lawyer)
        time_slots_serializer = TimeSlotSerializer(lawyer_time_slots, many=True)
        validated_data['time_slots'] = time_slots_serializer.data

        return validated_data

    def update(self, instance, validated_data):
        instance.specialization = validated_data.get('specialization', instance.specialization)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.bio = validated_data.get('bio', instance.bio)
        instance.language = validated_data.get('language', instance.language)

        # Update Address
        address_data = validated_data.get('address')
        if address_data:
            instance.address.street = address_data.get('street', instance.address.street)
            instance.address.city = address_data.get('city', instance.address.city)
            instance.address.state = address_data.get('state', instance.address.state)
            instance.address.zip_code = address_data.get('zip_code', instance.address.zip_code)
            instance.address.country = address_data.get('country', instance.address.country)
            instance.address.save()

        # Update TimeSlots
        time_slots_data = validated_data.get('time_slots')
        if time_slots_data:
            instance.time_slots.all().delete()
            for slot_data in time_slots_data:
                TimeSlot.objects.create(lawyer=instance, **slot_data)

        instance.save()
        return instance




class LawyerDocumentSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        lawyer_profile_pk = self.context['lawyer_profile_pk']
        return LawyerDocument.objects.create(lawyer_id=lawyer_profile_pk, **validated_data)

    class Meta:
        model = LawyerDocument
        fields = ['id', 'pdf_file']


class ClientProfileSerializer(serializers.ModelSerializer):
    # user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    address = AddressSerializer(required=False, allow_null=True)

    class Meta:
        model = ClientProfile
        fields = ['id', 'age', 'gender', 'phone_number', 'address']

    def create(self, validated_data):
        address_data = validated_data.pop('address', None)

        if address_data:
            address = Address.objects.create(**address_data)
            validated_data['address'] = address

        client_profile = ClientProfile.objects.create(**validated_data)
        return client_profile
    
    def update(self, instance, validated_data):
        instance.age = validated_data.get('age', instance.age)
        instance.gender = validated_data.get('gender', instance.gender)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)

        # Update Address
        address_data = validated_data.get('address')
        if address_data:
            instance.address.street = address_data.get('street', instance.address.street)
            instance.address.city = address_data.get('city', instance.address.city)
            instance.address.state = address_data.get('state', instance.address.state)
            instance.address.zip_code = address_data.get('zip_code', instance.address.zip_code)
            instance.address.country = address_data.get('country', instance.address.country)
            instance.address.save()

        instance.save()
        return instance
    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class LawyerProfileAdminListSerializer(serializers.ModelSerializer):
    images = LawyerImageSerializer(many=True , read_only=True)
    documents = LawyerDocumentSerializer(many=True , read_only=True)
    first_name = serializers.CharField(source='user.first_name' , read_only=True)
    last_name = serializers.CharField(source='user.last_name' , read_only=True)

    class Meta:
        model = LawyerProfile
        fields = ['id','first_name', 'last_name', 'specialization', 'images', 'documents' , 'approved']


class AppointmentSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    client_name = serializers.CharField(source='client.user.get_full_name', read_only=True)
    client_age = serializers.CharField(source='client.user.age', read_only=True)

    class Meta:
        model = Appointment
        fields = ['id', 'day','client_name','client_age', 'start_time', 'end_time' , 'status']

    def validate(self, data):
        lawyer = self.context.get('lawyer_profile')
        client = self.context.get('client_profile')

        # Appointment.objects.create(
        #     lawyer=lawyer,
        #     client=client,
        #     day=data['day'],
        #     start_time=data['start_time'],
        #     end_time=data['end_time'],
        #     status='pending'
        # )

        data = { 'lawyer': lawyer, 'client': client, 'day': data['day'], 'start_time': data['start_time'], 'end_time': data['end_time'],'status': 'pending'}
        return data

    
class ReviewSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.user.get_full_name', read_only=True)

    class Meta:
        model = Review
        fields = ['id', "lawyer_id","client_id","client_name",'rating', 'comment', 'created_at']

    def create(self, validated_data):
        lawyer = self.context.get('lawyer_id')
        client_id = self.context.get('client_id')
        
        # Get the ClientProfile instance using the provided client_id
        client= get_object_or_404(ClientProfile, id=client_id)
        # client_name = client.user.get_full_name()
        # print(client_name)
        review_instance = Review.objects.create(
            lawyer_id=lawyer,
            # client_name=client_name,
            client = client,
            rating=validated_data['rating'],
            comment=validated_data['comment']
        )
        return review_instance

    
