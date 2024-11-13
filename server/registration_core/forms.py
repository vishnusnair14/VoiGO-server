from django import forms

from server.models import UploadedImage


class ProfileImageUpload(forms.ModelForm):
    class Meta:
        model = UploadedImage
        fields = ['image']

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.image:
            instance.image.name = instance.image.name
        if commit:
            instance.save()
        return instance
