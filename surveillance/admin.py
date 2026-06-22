from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.db.models import Q
from .models import (SecurityProfile,TargetPerson,DetectionEvent,TargetAssignment,Notification)


# ─────────────────────────────────────────────────────────────────────────────
# SECURITY PROFILE ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(SecurityProfile)
class SecurityProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for SecurityProfile model.
    Manages security personnel profiles, roles, and duty status.
    """
    
    list_display = (
        'badge_number',
        'get_full_name',
        'role_badge',
        'is_on_duty',
        'get_user_link',
    )
    
    list_filter = (
        'role',
        'is_on_duty',
        'user__date_joined',
    )
    
    search_fields = (
        'badge_number',
        'user__username',
        'user__first_name',
        'user__last_name',
        'emergency_contact',
    )
    
    readonly_fields = (
        'user',
        'get_profile_picture_preview',
    )
    
    list_editable = (
        'is_on_duty',
    )
    
    fieldsets = (
        ('User Reference', {
            'fields': ('user',),
        }),
        ('Profile Information', {
            'fields': (
                'badge_number',
                'role',
                'emergency_contact',
                'get_profile_picture_preview',
                'profile_picture',
            ),
        }),
        ('Duty Status', {
            'fields': ('is_on_duty',),
        }),
    )
    
    ordering = ('badge_number',)
    list_per_page = 20
    
    actions = ['mark_on_duty', 'mark_off_duty']
    
    def get_full_name(self, obj):
        """Display user's full name."""
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username
    get_full_name.short_description = 'Full Name'
    
    def get_user_link(self, obj):
        """Link to the user object."""
        url = reverse('admin:auth_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    get_user_link.short_description = 'Username'
    
    def role_badge(self, obj):
        """Display role with color coding."""
        colors = {
            'operator': '#3498db',      # Blue
            'supervisor': '#f39c12',    # Orange
            'admin': '#e74c3c',         # Red
        }
        color = colors.get(obj.role, '#95a5a6')
        role_display = obj.get_role_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            role_display
        )
    role_badge.short_description = 'Role'
    
    def get_profile_picture_preview(self, obj):
        """Display profile picture preview."""
        if obj.profile_picture:
            return format_html(
                '<img src="{}" width="100" height="100" style="border-radius: 5px;" />',
                obj.profile_picture.url
            )
        return format_html('<em>No image</em>')
    get_profile_picture_preview.short_description = 'Profile Picture Preview'
    
    def mark_on_duty(self, request, queryset):
        updated = queryset.update(is_on_duty=True)
        self.message_user(request, f'{updated} personnel marked as on duty.')
    mark_on_duty.short_description = 'Mark selected as on duty'
    
    def mark_off_duty(self, request, queryset):
        updated = queryset.update(is_on_duty=False)
        self.message_user(request, f'{updated} personnel marked as off duty.')
    mark_off_duty.short_description = 'Mark selected as off duty'


# ─────────────────────────────────────────────────────────────────────────────
# TARGET PERSON ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(TargetPerson)
class TargetPersonAdmin(admin.ModelAdmin):
 
    list_display = (
        'id',
        'name',
        'last_name',
        'tazkira_number',
        'is_found',
        'crime',
        'age',
        'gender',
        'expiration_badge',
        'uploaded_by',
        'created_at',
    )
    
    list_filter = (
        'gender',
        'marital_status',
        'is_found',
        'created_at',
        ('expires_at', admin.EmptyFieldListFilter),
        'uploaded_by',
    )
    
    search_fields = (
        'name',
        'last_name',
        'tazkira_number',
        'phone_number',
        'crime',
        'address',
    )
    
    readonly_fields = (
        'created_at',
        'get_image_preview',
        'uploaded_by',
    )
    
    list_editable = (
        'is_found',
    )
    
    fieldsets = (
        ('Personal Information', {
            'fields': (
                'name',
                'last_name',
                'father_name',
                'age',
                'gender',
                'place_of_birth',
                'marital_status',
                'job',
            ),
        }),
        ('Identification', {
            'fields': (
                'tazkira_number',
                'phone_number',
                'address',
            ),
        }),
        ('Crime Information', {
            'fields': (
                'crime',
                'description',
            ),
        }),
        ('Image', {
            'fields': (
                'image',
                'get_image_preview',
            ),
        }),
        ('Status & Timeline', {
            'fields': (
                'is_found',
                'expires_at',
                'created_at',
                'uploaded_by',
            ),
        }),
    )
    
    ordering = ('-created_at',)
    list_per_page = 15
    
    actions = [
        'mark_as_found',
        'mark_as_not_found',
        'set_expire_7_days',
        'set_expire_30_days',
        'clear_expiration',
    ]
    
    def expiration_badge(self, obj):
        """Display expiration status."""
        if not obj.expires_at:
            return format_html('<span style="color: gray;">No expiration</span>')
        
        from django.utils import timezone
        if obj.expires_at > timezone.now():
            return format_html(
                '<span style="color: orange;">⏱ {}</span>',
                obj.expires_at.strftime('%Y-%m-%d %H:%M')
            )
        else:
            return format_html(
                '<span style="color: red; text-decoration: line-through;">Expired</span>'
            )
    expiration_badge.short_description = 'Expires'
    
    def get_image_preview(self, obj):
        """Display image preview in admin."""
        if obj.image:
            return format_html(
                '<img src="{}" width="150" height="150" style="border-radius: 5px; '
                'object-fit: cover;" />',
                obj.image.url
            )
        return format_html('<em>No image</em>')
    get_image_preview.short_description = 'Image Preview'
    
    def mark_as_found(self, request, queryset):
        updated = queryset.update(is_found=True)
        self.message_user(request, f'{updated} target(s) marked as found.')
    mark_as_found.short_description = 'Mark as found'
    
    def mark_as_not_found(self, request, queryset):
        updated = queryset.update(is_found=False)
        self.message_user(request, f'{updated} target(s) marked as not found.')
    mark_as_not_found.short_description = 'Mark as not found'
    
    def set_expire_7_days(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        expires_at = timezone.now() + timedelta(days=7)
        updated = queryset.update(expires_at=expires_at)
        self.message_user(request, f'{updated} target(s) set to expire in 7 days.')
    set_expire_7_days.short_description = 'Set expiration to 7 days'
    
    def set_expire_30_days(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        expires_at = timezone.now() + timedelta(days=30)
        updated = queryset.update(expires_at=expires_at)
        self.message_user(request, f'{updated} target(s) set to expire in 30 days.')
    set_expire_30_days.short_description = 'Set expiration to 30 days'
    
    def clear_expiration(self, request, queryset):
        updated = queryset.update(expires_at=None)
        self.message_user(request, f'{updated} target(s) expiration cleared.')
    clear_expiration.short_description = 'Clear expiration date'


# ─────────────────────────────────────────────────────────────────────────────
# DETECTION EVENT ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(DetectionEvent)
class DetectionEventAdmin(admin.ModelAdmin):
    """
    Admin configuration for DetectionEvent model.
    Tracks and manages all detection events from cameras.
    """
    
    list_display = (
        'id',
        'timestamp',
        'action_badge',
        'matched_target_name',
        'camera_name',
        'person_count',
        'verification_status_badge',
        'verified_by',
    )
    
    list_filter = (
        'action',
        'verification_status',
        'timestamp',
        'camera',
        ('matched_target', admin.RelatedOnlyFieldListFilter),
    )
    
    search_fields = (
        'matched_target_name',
        'camera__name',
        'camera__location',
    )
    
    readonly_fields = (
        'timestamp',
        'get_frame_snapshot_preview',
    )
    
    fieldsets = (
        ('Detection Information', {
            'fields': (
                'timestamp',
                'action',
                'person_count',
                'camera',
            ),
        }),
        ('Target Matching', {
            'fields': (
                'matched_target',
                'matched_target_name',
            ),
        }),
        ('Evidence', {
            'fields': (
                'frame_snapshot',
                'get_frame_snapshot_preview',
            ),
        }),
        ('Verification Workflow', {
            'fields': (
                'verification_status',
                'verified_by',
                'verified_at',
                'verification_note',
            ),
        }),
        ('Assignment Reference', {
            'fields': (
                'related_assignment',
            ),
        }),
    )
    
    ordering = ('-timestamp',)
    list_per_page = 20
    
    actions = [
        'mark_approved',
        'mark_rejected',
        'mark_pending',
        'mark_unreviewed',
    ]
    
    def action_badge(self, obj):
        """Display action type with color."""
        colors = {
            'Normal': '#95a5a6',
            'FALL DETECTED': '#e74c3c',
            'HAND WAVING': '#f39c12',
        }
        color = colors.get(obj.action, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.action
        )
    action_badge.short_description = 'Action'
    
    def camera_name(self, obj):
        """Display camera name with link."""
        if obj.camera:
            return format_html(
                '<strong>{}</strong><br/><small style="color: #666;">{}</small>',
                obj.camera.name,
                obj.camera.location
            )
        return '—'
    camera_name.short_description = 'Camera'
    
    def verification_status_badge(self, obj):
        """Display verification status with color."""
        colors = {
            'unreviewed': '#95a5a6',    # Gray
            'pending': '#f39c12',       # Orange
            'approved': '#27ae60',      # Green
            'rejected': '#e74c3c',      # Red
        }
        color = colors.get(obj.verification_status, '#95a5a6')
        status = obj.get_verification_status_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            status
        )
    verification_status_badge.short_description = 'Verification'
    
    def get_frame_snapshot_preview(self, obj):
        """Display frame snapshot preview."""
        if obj.frame_snapshot:
            return format_html(
                '<img src="{}" width="200" height="150" style="border-radius: 5px; '
                'object-fit: cover;" />',
                obj.frame_snapshot.url
            )
        return format_html('<em>No snapshot</em>')
    get_frame_snapshot_preview.short_description = 'Frame Snapshot Preview'
    
    def mark_approved(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            verification_status='approved',
            verified_at=timezone.now()
        )
        self.message_user(request, f'{updated} event(s) marked as approved.')
    mark_approved.short_description = 'Mark as approved'
    
    def mark_rejected(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            verification_status='rejected',
            verified_at=timezone.now()
        )
        self.message_user(request, f'{updated} event(s) marked as rejected.')
    mark_rejected.short_description = 'Mark as rejected'
    
    def mark_pending(self, request, queryset):
        updated = queryset.update(verification_status='pending')
        self.message_user(request, f'{updated} event(s) marked as pending.')
    mark_pending.short_description = 'Mark as pending'
    
    def mark_unreviewed(self, request, queryset):
        updated = queryset.update(verification_status='unreviewed')
        self.message_user(request, f'{updated} event(s) marked as unreviewed.')
    mark_unreviewed.short_description = 'Mark as unreviewed'


# ─────────────────────────────────────────────────────────────────────────────
# TARGET ASSIGNMENT ADMIN (WITH INLINE)
# ─────────────────────────────────────────────────────────────────────────────

class DetectionEventInline(admin.TabularInline):
    """Inline admin for showing detection events related to an assignment."""
    model = DetectionEvent
    extra = 0
    can_delete = False
    readonly_fields = ('timestamp', 'action', 'person_count', 'verification_status')
    fields = ('timestamp', 'action', 'person_count', 'verification_status')
    ordering = ('-timestamp',)


@admin.register(TargetAssignment)
class TargetAssignmentAdmin(admin.ModelAdmin):
    """
    Admin configuration for TargetAssignment model.
    Manages assignment workflow between supervisors and operators.
    """
    
    list_display = (
        'id',
        'target_name',
        'assigned_to_name',
        'assigned_by_name',
        'status_badge',
        'created_at',
        'updated_at',
    )
    
    list_filter = (
        'status',
        'created_at',
        'updated_at',
        'assigned_by',
        'assigned_to',
    )
    
    search_fields = (
        'target__name',
        'target__last_name',
        'assigned_to__username',
        'assigned_to__first_name',
        'assigned_to__last_name',
        'assigned_by__username',
        'note',
    )
    
    readonly_fields = (
        'created_at',
        'updated_at',
    )
    
    fieldsets = (
        ('Assignment Details', {
            'fields': (
                'target',
                'assigned_to',
                'assigned_by',
                'status',
            ),
        }),
        ('Communication', {
            'fields': ('note',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    inlines = [DetectionEventInline]
    
    ordering = ('-created_at',)
    list_per_page = 20
    
    actions = [
        'mark_pending',
        'mark_acknowledged',
        'mark_passed_back',
        'mark_closed',
    ]
    
    def target_name(self, obj):
        """Display target name."""
        return f"{obj.target.name} {obj.target.last_name}"
    target_name.short_description = 'Target'
    
    def assigned_to_name(self, obj):
        """Display assigned operator."""
        if obj.assigned_to:
            return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip() or obj.assigned_to.username
        return '—'
    assigned_to_name.short_description = 'Assigned To'
    
    def assigned_by_name(self, obj):
        """Display supervisor who made assignment."""
        if obj.assigned_by:
            return f"{obj.assigned_by.first_name} {obj.assigned_by.last_name}".strip() or obj.assigned_by.username
        return '—'
    assigned_by_name.short_description = 'Assigned By'
    
    def status_badge(self, obj):
        """Display status with color."""
        colors = {
            'pending': '#f39c12',
            'acknowledged': '#3498db',
            'passed_back': '#9b59b6',
            'closed': '#27ae60',
        }
        color = colors.get(obj.status, '#95a5a6')
        status = obj.get_status_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            status
        )
    status_badge.short_description = 'Status'
    
    def mark_pending(self, request, queryset):
        updated = queryset.update(status='pending')
        self.message_user(request, f'{updated} assignment(s) marked as pending.')
    mark_pending.short_description = 'Mark as pending'
    
    def mark_acknowledged(self, request, queryset):
        updated = queryset.update(status='acknowledged')
        self.message_user(request, f'{updated} assignment(s) marked as acknowledged.')
    mark_acknowledged.short_description = 'Mark as acknowledged'
    
    def mark_passed_back(self, request, queryset):
        updated = queryset.update(status='passed_back')
        self.message_user(request, f'{updated} assignment(s) marked as passed back.')
    mark_passed_back.short_description = 'Mark as passed back'
    
    def mark_closed(self, request, queryset):
        updated = queryset.update(status='closed')
        self.message_user(request, f'{updated} assignment(s) marked as closed.')
    mark_closed.short_description = 'Mark as closed'


# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICATION ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Admin configuration for Notification model.
    Manages system notifications to security personnel.
    """
    
    list_display = (
        'id',
        'recipient_name',
        'notification_type_badge',
        'title',
        'is_read',
        'created_at',
    )
    
    list_filter = (
        'notification_type',
        'is_read',
        'created_at',
        'recipient',
    )
    
    search_fields = (
        'recipient__username',
        'recipient__first_name',
        'recipient__last_name',
        'title',
        'message',
    )
    
    readonly_fields = (
        'created_at',
        'recipient',
        'notification_type',
    )
    
    fieldsets = (
        ('Recipient', {
            'fields': ('recipient',),
        }),
        ('Notification Content', {
            'fields': (
                'notification_type',
                'title',
                'message',
            ),
        }),
        ('Status', {
            'fields': ('is_read',),
        }),
        ('Related Entities', {
            'fields': (
                'related_assignment',
                'related_event',
            ),
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
    
    ordering = ('-created_at',)
    list_per_page = 20
    list_editable = ('is_read',)
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def recipient_name(self, obj):
        """Display recipient name."""
        return f"{obj.recipient.first_name} {obj.recipient.last_name}".strip() or obj.recipient.username
    recipient_name.short_description = 'Recipient'
    
    def notification_type_badge(self, obj):
        """Display notification type with color."""
        colors = {
            'assignment': '#4ecca3',
            'pass_back': '#f39c12',
            'detection': '#e94560',
            'verification': '#3498db',
            'approved': '#2ecc71',
            'rejected': '#e74c3c',
            'system': '#9b59b6',
        }
        color = colors.get(obj.notification_type, '#95a5a6')
        notif_type = obj.get_notification_type_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            notif_type
        )
    notification_type_badge.short_description = 'Type'
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notification(s) marked as read.')
    mark_as_read.short_description = 'Mark as read'
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'{updated} notification(s) marked as unread.')
    mark_as_unread.short_description = 'Mark as unread'


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN SITE CUSTOMIZATION
# ─────────────────────────────────────────────────────────────────────────────

admin.site.site_header = "Butterfly Surveillance System"
admin.site.site_title = "Butterfly Admin Panel"
admin.site.index_title = "Dashboard"