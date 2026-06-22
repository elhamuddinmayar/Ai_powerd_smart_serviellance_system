from django.contrib import admin

# Register your models here.
from .models import Camera


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    """
    Admin configuration for Camera model.
    Provides a comprehensive interface for managing surveillance cameras,
    including status monitoring, activation/deactivation, and location tracking.
    """
    
    # Display columns in the list view
    list_display = (
        'id',
        'name',
        'status_badge',
        'is_active',
        'location',
        'last_seen_at',
        'went_offline_at',
        'created_at',
    )
    
    # Filterable fields in the sidebar
    list_filter = (
        'status',
        'is_active',
        'created_at',
        ('last_seen_at', admin.EmptyFieldListFilter),
    )
    
    # Search fields
    search_fields = (
        'name',
        'location',
        'index_or_url',
        'description',
    )
    
    # Read-only fields
    readonly_fields = (
        'created_at',
        'last_seen_at',
        'went_offline_at',
        'status',
    )
    
    # Editable fields in list view
    list_editable = (
        'is_active',
    )
    
    # Fieldsets for organized admin form layout
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'location', 'description'),
            'description': 'Essential camera identification and description.',
        }),
        ('Camera Source', {
            'fields': ('index_or_url',),
            'description': 'Camera index (0, 1, 2...) for local webcams or full URL for IP cameras.',
        }),
        ('Status', {
            'fields': ('status', 'is_active', 'last_seen_at', 'went_offline_at'),
            'description': 'Current operational status of the camera.',
        }),
        ('Location Data (Optional)', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',),
            'description': 'GPS coordinates for map integration.',
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
    
    # Ordering in the admin list
    ordering = ('-created_at', 'id')
    
    # Per-page pagination
    list_per_page = 20
    
    # Actions
    actions = [
        'mark_as_online',
        'mark_as_offline',
        'activate_cameras',
        'deactivate_cameras',
    ]
    
    def status_badge(self, obj):
        """
        Display status with color coding.
        """
        colors = {
            'online': '#28a745',      # Green
            'offline': '#dc3545',     # Red
            'unknown': '#ffc107',     # Yellow
        }
        color = colors.get(obj.status, '#6c757d')
        return f'<span style="color: {color}; font-weight: bold;">● {obj.get_status_display()}</span>'
    status_badge.short_description = 'Status'
    status_badge.allow_tags = True
    
    def mark_as_online(self, request, queryset):
        """
        Admin action to mark cameras as online.
        """
        updated = 0
        for camera in queryset:
            camera.mark_online()
            updated += 1
        self.message_user(request, f'{updated} camera(s) marked as online.')
    mark_as_online.short_description = 'Mark selected cameras as online'
    
    def mark_as_offline(self, request, queryset):
        """
        Admin action to mark cameras as offline.
        """
        updated = 0
        for camera in queryset:
            camera.mark_offline()
            updated += 1
        self.message_user(request, f'{updated} camera(s) marked as offline.')
    mark_as_offline.short_description = 'Mark selected cameras as offline'
    
    def activate_cameras(self, request, queryset):
        """
        Admin action to activate cameras.
        """
        updated = queryset.update(is_active=True, status='unknown')
        self.message_user(request, f'{updated} camera(s) activated.')
    activate_cameras.short_description = 'Activate selected cameras'
    
    def deactivate_cameras(self, request, queryset):
        """
        Admin action to deactivate cameras.
        """
        updated = queryset.update(is_active=False, status='offline')
        self.message_user(request, f'{updated} camera(s) deactivated.')
    deactivate_cameras.short_description = 'Deactivate selected cameras'