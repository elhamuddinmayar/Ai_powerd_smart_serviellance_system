from django.contrib import admin
from .models import TargetPerson, SecurityProfile

@admin.register(TargetPerson)
class TargetPersonAdmin(admin.ModelAdmin):
    # Displaying biometric and status info for quick scanning
    list_display = ('name', 'last_name', 'tazkira_number', 'is_found', 'created_at')
    list_filter = ('gender', 'is_found', 'marital_status')
    search_fields = ('name', 'last_name', 'tazkira_number')
    readonly_fields = ('created_at',)

@admin.register(SecurityProfile)
class SecurityProfileAdmin(admin.ModelAdmin):
    # display the user, their specific badge, role, and if they are currently active
    list_display = ('badge_number', 'get_full_name', 'role', 'is_on_duty')
    list_filter = ('role', 'is_on_duty')
    search_fields = ('badge_number', 'user__username', 'user__first_name', 'user__last_name')
    list_editable = ('is_on_duty',) # Allows toggling duty status directly from the list view

    # Helper method to show the user's real name in the list
    @admin.display(description='Full Name')
    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"