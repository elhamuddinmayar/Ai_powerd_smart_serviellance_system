from django.contrib import admin
from .models import (SecurityProfile, TargetPerson, DetectionEvent, TargetAssignment, Notification)


# ─────────────────────────────────────────────────────────────────────────────
# SECURITY PROFILE ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(SecurityProfile)
class SecurityProfileAdmin(admin.ModelAdmin):

    list_display = (
        'badge_number',
        'user',
        'role',
        'is_on_duty',
        'emergency_contact',
    )

    list_filter = (
        'role',
        'is_on_duty',
    )

    search_fields = (
        'badge_number',
        'user__username',
        'user__first_name',
        'user__last_name',
        'emergency_contact',
    )

    list_editable = ('is_on_duty',)

    ordering = ('badge_number',)
    list_per_page = 20

    actions = ['mark_on_duty', 'mark_off_duty']

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
        'expires_at',
        'uploaded_by',
        'created_at',
    )

    list_filter = (
        'gender',
        'marital_status',
        'is_found',
        'created_at',
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

    list_editable = ('is_found',)

    ordering = ('-created_at',)
    list_per_page = 15

    actions = [
        'mark_as_found',
        'mark_as_not_found',
        'set_expire_7_days',
        'set_expire_30_days',
        'clear_expiration',
    ]

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

    list_display = (
        'id',
        'timestamp',
        'action',
        'matched_target_name',
        'camera',
        'person_count',
        'verification_status',
        'verified_by',
    )

    list_filter = (
        'action',
        'verification_status',
        'timestamp',
        'camera',
    )

    search_fields = (
        'matched_target_name',
        'camera__name',
        'camera__location',
    )

    ordering = ('-timestamp',)
    list_per_page = 20

    actions = [
        'mark_approved',
        'mark_rejected',
        'mark_pending',
        'mark_unreviewed',
    ]

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
    model = DetectionEvent
    extra = 0
    can_delete = False
    readonly_fields = ('timestamp', 'action', 'person_count', 'verification_status')
    fields = ('timestamp', 'action', 'person_count', 'verification_status')
    ordering = ('-timestamp',)


@admin.register(TargetAssignment)
class TargetAssignmentAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'target',
        'assigned_to',
        'assigned_by',
        'status',
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

    inlines = [DetectionEventInline]

    ordering = ('-created_at',)
    list_per_page = 20

    actions = [
        'mark_pending',
        'mark_acknowledged',
        'mark_passed_back',
        'mark_closed',
    ]

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

    list_display = (
        'id',
        'recipient',
        'notification_type',
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

    list_editable = ('is_read',)

    ordering = ('-created_at',)
    list_per_page = 20

    actions = ['mark_as_read', 'mark_as_unread']

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